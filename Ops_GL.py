# ModernGL rasterization

import numpy as np
import time
from Utils import viewMat
import json
import time

import moderngl

from OpenGL.GL import glGenTextures

import sys, os

import OpsConv
PATH = OpsConv.PATH

ctx = OpsConv.getContext_GL()
print("Using", ctx.info["GL_RENDERER"])

def makeProgram(f, path="ShadersGL/"):
    t = open(PATH + path + f).read()
    return t

trisetup = makeProgram("trisetup.c", "PipeGL/")
trisetupAnim = makeProgram("trisetup_anim.c", "PipeGL/")
trisetupOrtho = makeProgram("trisetupOrtho.c", "PipeGL/")
trisetupOrthoAnim = makeProgram("trisetupOrtho_anim.c", "PipeGL/")
trisetup2d = makeProgram("trisetup_2d.c", "PipeGL/")

trisetupNorm = makeProgram('trisetup_norm.c', 'PipeGL/')

trisetupWave = makeProgram('trisetupWave.c', 'PipeGL/')

if True: #if sys.platform == 'darwin':
    trisetup = trisetup.replace('[128]', '[12]')
    trisetupAnim = trisetupAnim.replace('[128]', '[12]')


DRAW_SHADERS = 'Base Sh ShAlpha Sky Sub Border Emissive Min MinAlpha Z ZAlpha'
DRAW_SHADERS += ' Dissolve ZDissolve Fog SSR SSRglass SSRopaque Metallic Special'

TRANSPARENT_SHADERS = set(
    'add border special SSR SSRopaque SSRglass sub fog lens'.split(' '))

POST_SHADERS = 'gamma lens FXAA dof ssao'

def loadShaders():
    for f in DRAW_SHADERS.split(' '):
        globals()[f'draw{f}'] = makeProgram('draw{}.c'.format(f.lower()))
    for f in POST_SHADERS.split(' '):
        globals()[f.lower()] = makeProgram(f'Post/{f}.c')


loadShaders()

FSR_SUPPORTED = 1
fsr_frag = makeProgram('Post/fsr.c')
fsr_frag = fsr_frag.replace('#include "ffx_a.h"', makeProgram('Post/ffx_a.h'))
fsr_frag = fsr_frag.replace('#include "ffx_fsr1.h"', makeProgram('Post/ffx_fsr1.h'))
try:
    ctx.program(vertex_shader=trisetup2d, fragment_shader=fsr_frag)
except moderngl.Error:
    FSR_SUPPORTED = 0
    print('FSR not supported')

fsr_rcas_frag = makeProgram('Post/fsr_rcas.c')
fsr_rcas_frag = fsr_rcas_frag.replace('#include "ffx_a.h"', makeProgram('Post/ffx_a.h'))
fsr_rcas_frag = fsr_rcas_frag.replace('#include "ffx_fsr1.h"', makeProgram('Post/ffx_fsr1.h'))
if FSR_SUPPORTED:
    ctx.program(vertex_shader=trisetup2d, fragment_shader=fsr_rcas_frag)

ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.BLEND)
ctx.front_face = 'cw'

def align34(a):
    return np.stack((a[:,0], a[:,1], a[:,2], np.zeros_like(a[:,0])), axis=1)

class CLDraw:
    def __init__(self, w, h, ires=1, use_fsr=0):

        # Internal resolution for supersampling
        self.IRES = ires

        self.USE_FSR = use_fsr * FSR_SUPPORTED
        self.ENABLE_FXAA = 1

        self.W = np.int32(w * self.IRES)
        self.H = np.int32(h * self.IRES)
        self.A = w*h

        self.outW = w
        self.outH = h

        self.FB = ctx.texture((self.W, self.H), 3, dtype='f2')
        self.FB.repeat_x = False
        self.FB.repeat_y = False

        self.DB = ctx.depth_texture((self.W, self.H))
        self.fbo = ctx.framebuffer(self.FB, self.DB)
        self.fbo.use()

        # Final output
        try:
            self.FB_GL = glGenTextures(1) + 1
        except:
            print('Unable to get GL buffer id')
        self.FS_GL = ctx.texture((w, h), 3, dtype='f1')
        self.DS_GL = ctx.depth_texture((w, h))
        self.fs = ctx.framebuffer(self.FS_GL, self.DS_GL)

        self.FS2_GL = ctx.texture((w, h), 3, dtype='f1')
        self.DS2_GL = ctx.depth_texture((w, h))
        self.fs2 = ctx.framebuffer(self.FS2_GL, self.DS2_GL)

        if self.USE_FSR or self.ENABLE_FXAA:
            self.F_FSR = ctx.texture((self.W, self.H), 3, dtype='f1')
            self.D_FSR = ctx.depth_texture((self.W, self.H))
            self.fs_fsr = ctx.framebuffer(self.F_FSR, self.D_FSR)

        # Readable depth buffer
        self.DBT = ctx.texture((self.W, self.H), 1, dtype='f4')
        temp = ctx.depth_texture((self.W, self.H))
        self.fboZ = ctx.framebuffer((self.DBT,), temp)

        self.XYZ = []
        self.UV = []
        self.VN = []
        self.LI = []

        self.BN = {}
        self.BT = {}
        self.BO = {}
        self.boneNums = {}

        self.VBO = []
        self.VAO = []

        self.gSize = []

        self.TEX = []
        self.TA = {}
        self.DRAW = []
        self.DRAWZ = {}

        self.texSize = []

        self.SHADOWMAP = {}
        self.SVA = []
        self.drawSB = {}

        self.NM = {}

        self.PSTEX = {}

        x = np.array([-1, -1, 1, 1, -1, 1])
        y = np.array([1, -1, 1, 1, -1, -1])
        z = np.ones(6)*-0.9999
        vertices = np.dstack([x, y, z])
        self.post_vbo = ctx.buffer(vertices.astype('float32').tobytes())

        self.setupPost()
        self.setupFSR()

        self.oldShaders = {}

        self.dofFocus = 3
        self.dofAperture = 12
        self.doSSAO = False

        self.setupBlur()
        self.setupNoise()
        self.noiseDist = 0

        self.stTime = time.time()

        self.shaderParams = {'{REFL_LENGTH}':str(self.H)}

        self.batchCache = {}

    def reloadShaders(self, **kwargs):
        while True:
            try:
                loadShaders()
                tmpOldShaders = dict(self.oldShaders)
                for i in range(len(self.VBO)):
                    self.changeShader(i, {'shader':'', 'args':{}}, **kwargs)
                    self.changeShader(i, tmpOldShaders[i], **kwargs)

                for s in 'psProg dProg moProg ssaoProg'.split(' '):
                    try: self.__delattr__(s)
                    except: pass

                self.setupPost()
                self.setupBlur()
                self.setupSSAO()
                self.setupDoF()
            except moderngl.Error as e:
                print(e)
                input('Try again: ')
            else:
                break

    def setupPost(self):
        w, h = self.outW, self.outH

        self.post_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=gamma)
        self.post_vao = ctx.vertex_array(self.post_prog, self.post_vbo, 'in_vert')
        self.post_prog['tex1'] = 0

        self.post_prog['width'].write(np.float32(self.W))
        self.post_prog['height'].write(np.float32(self.H))

    def setupFSR(self):
        w, h = self.outW, self.outH

        if self.USE_FSR:
            self.fsr_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=fsr_frag)
            self.fsr_vao = ctx.vertex_array(self.fsr_prog, self.post_vbo, 'in_vert')
            self.fsr_prog['Source'] = 0
            self.fsr_prog['width_in'].write(np.float32(self.W))
            self.fsr_prog['height_in'].write(np.float32(self.H))
            self.fsr_prog['width_out'].write(np.float32(w))
            self.fsr_prog['height_out'].write(np.float32(h))

            self.fsr_rcas_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=fsr_rcas_frag)
            self.fsr_rcas_vao = ctx.vertex_array(self.fsr_rcas_prog, self.post_vbo, 'in_vert')

        self.fxaa_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=fxaa)
        self.fxaa_vao = ctx.vertex_array(self.fxaa_prog, self.post_vbo, 'in_vert')
        self.fxaa_prog['tex1'] = 0
        if self.USE_FSR:
            self.fxaa_prog['width'].write(np.float32(self.W))
            self.fxaa_prog['height'].write(np.float32(self.H))
        else:
            self.fxaa_prog['width'].write(np.float32(w))
            self.fxaa_prog['height'].write(np.float32(h))

    def setupNoise(self):
        from PIL import Image
        n = Image.open('../Assets/Noise/NoiseTest.png').convert('RGB')
        n = (np.array(n)[:,:,0] / 256.).astype('float16')
        tex = ctx.texture3d((16,16,16), 1, n, dtype='f2')
        self.noiseTex = tex

    def setSkyTex(self, r, g, b, size):
        pass
    def setHostSkyTex(self, tex):
        pass

    def setReflTex(self, name, r, g, b, size):
        pass
    def addTexAlpha(self, tex, name=None, mipLvl=8):
        ta = tex.astype('uint8') * 255
        a = ctx.texture(tex.shape[::-1], 1, ta)
        a.build_mipmaps(0, mipLvl)
        if name is None: name = len(self.TA)
        self.TA[name] = a

    def addNrmMap(self, nrm, name, mip=True, mipLvl=2):
        t = ctx.texture((nrm.shape[1],nrm.shape[0]), 3, nrm)
        if mip:
            t.build_mipmaps(0, mipLvl)
        self.NM[name] = t

    def addPSTex(self, tex, name):
        t = ctx.texture((tex.shape[1],tex.shape[0]), 1, tex)
        t.build_mipmaps(0, 2)
        self.PSTEX[name] = t

    def addBoneWeights(self, tn, bw):
        dat = bw.reshape((-1,))
        bn = ctx.buffer(dat.astype('float32').tobytes())
        self.BN[tn] = bn

    def initBoneTransforms(self, name, bn):
        self.boneNums[name] = bn

    def initBoneOrigin(self, o, bn, tn):
        if tn not in self.BO:
            self.BO[tn] = np.zeros((32, 3), "float32")

        self.BO[tn][bn] = o

    def setBoneTransform(self, name, bt):
        self.BT[name] = np.zeros((32*4, 4), 'float32')
        self.BT[name][:4*self.boneNums[name]] = bt.astype("float32")
        self.BT[name] = self.BT[name].tobytes()

    def boneTransform(self, cStart, cEnd, tn, name, offset):
        try:
            self.DRAW[tn]['RR'].write(self.BT[name])
            self.DRAW[tn]['off'] = offset
            self.DRAW[tn]['bOrigin'].write(self.BO[tn].tobytes())
        except KeyError:
            pass
        try:
            self.drawSB[tn]['RR'].write(self.BT[name])
            self.drawSB[tn]['off'] = offset
            self.drawSB[tn]['bOrigin'].write(self.BO[tn].tobytes())
        except KeyError:
            pass
        try:
            self.DRAWZ[tn][1]['RR'].write(self.BT[name])
            self.DRAWZ[tn][1]['off'] = offset
            self.DRAWZ[tn][1]['bOrigin'].write(self.BO[tn].tobytes())
        except KeyError:
            pass

    def invbt(self, b, tt=-1):
        for i in range(b.shape[0]//4):
            b[4*i:4*i+3,:3] = np.transpose(b[4*i:4*i+3,:3])
            b[4*i+3] *= tt
        return b

    def vertLight(self, mask, dirI, dirD,
                  pointI=None, pointP=None,
                  spotI=None, spotD=None, spotP=None):

        ld = dirI.shape[0]
        self.DInt = np.zeros((8, 3), 'float32')
        self.DDir = np.zeros((8, 3), 'float32')
        self.DInt[:ld] = dirI
        self.DDir[:ld] = dirD


        if pointI is 1:
            pointI = np.zeros((1,3))
            pointP = np.zeros((1,3))
        lp = min(16, pointI.shape[0])

        self.PInt = np.zeros((16, 3), 'float32')
        self.PPos = np.zeros((16, 3), 'float32')
        self.PInt[:lp] = pointI[:lp]
        self.PPos[:lp] = pointP[:lp]


        if spotI is 1 or spotI is None:
            spotI = np.zeros((1,3))
            spotP = np.zeros((1,3))
            spotD = np.zeros((1,3))

        ssize = 12 # if sys.platform == 'darwin' else 128

        ls = min(ssize, spotP.shape[0])

        self.SInt = np.zeros((ssize, 3), 'float32')
        self.SPos = np.zeros((ssize, 3), 'float32')
        self.SDir = np.zeros((ssize, 3), 'float32')
        self.SInt[:ls] = spotI[:ls]
        self.SPos[:ls] = spotP[:ls]
        self.SDir[:ls] = spotD[:ls]


        for n in range(len(self.DRAW)):
            try:
                self.DRAW[n]['DInt'].write(self.DInt.tobytes())
                self.DRAW[n]['DDir'].write(self.DDir.tobytes())
                self.DRAW[n]['lenD'] = ld
            except KeyError:
                pass

            try:
                self.DRAW[n]['PInt'].write(self.PInt.tobytes())
                self.DRAW[n]['PPos'].write(self.PPos.tobytes())
                self.DRAW[n]['lenP'] = lp
                self.DRAW[n]['highColor'].write(np.zeros(3, 'float32'))
            except KeyError:
                pass

            try:
                self.DRAW[n]['SLInt'].write(self.SInt.tobytes())
                self.DRAW[n]['SLPos'].write(self.SPos.tobytes())
                self.DRAW[n]['SLDir'].write(self.SDir.tobytes())
                self.DRAW[n]['lenSL'] = ls
            except KeyError:
                pass

    def translateBatch(self, batch: dict):
        """batch = {tn: [(diff, cStart, cEnd), ..], ..}"""
        for tn in batch:
            tb = batch[tn]
            if len(tb) == 0: continue
            size = 8*4
            mEnd = max(a[2] for a in tb)
            mStart = min(a[1] for a in tb)
            try:
                dat = self.batchCache[tn]
            except KeyError:
                raw = self.VBO[tn].read()
                dat = np.array(np.frombuffer(raw, 'float32')).reshape((-1, 8))
                self.batchCache[tn] = dat

            for i in range(len(tb)):
                dat[tb[i][1]:tb[i][2],:3] += np.expand_dims(tb[i][0], 0)
            self.VBO[tn].write(dat[mStart:mEnd], offset=mStart*size)

    def translate(self, diff, cStart, cEnd, tn):
        size = 8*4
        raw = self.VBO[tn].read(size=(cEnd-cStart)*size, offset=cStart*size)
        dat = np.array(np.frombuffer(raw, 'float32')).reshape((cEnd-cStart, 8))
        dat[:,:3] += np.expand_dims(diff, 0)
        self.VBO[tn].write(dat, offset=cStart*size)

    def scale(self, origin, diff, cStart, cEnd, tn):
        o = np.expand_dims(origin, 0)
        size = 8*4
        raw = self.VBO[tn].read(size=(cEnd-cStart)*size, offset=cStart*size)
        dat = np.array(np.frombuffer(raw, 'float32')).reshape((cEnd-cStart, 8))
        dat[:,:3] = (dat[:,:3] - o) * diff + o
        self.VBO[tn].write(dat, offset=cStart*size)

    def rotateBatch(self, batch: dict):
        """batch = {tn: [(diff, cStart, cEnd), ..], ..}"""
        for tn in batch:
            tb = batch[tn]
            if len(tb) == 0: continue
            size = 8*4
            mEnd = max(a[2] for a in tb)
            mStart = min(a[1] for a in tb)
            try:
                dat = self.batchCache[tn]
            except KeyError:
                raw = self.VBO[tn].read()
                dat = np.array(np.frombuffer(raw, 'float32')).reshape((-1, 8))
                self.batchCache[tn] = dat

            for i in range(len(tb)):
                dat[tb[i][1]:tb[i][2],:3] = dat[tb[i][1]:tb[i][2],:3] @ tb[i][0]
            self.VBO[tn].write(dat[mStart:mEnd], offset=mStart*size)

    def rotate(self, rotMat, cStart, cEnd, tn):
        size = 8*4
        raw = self.VBO[tn].read(size=(cEnd-cStart)*size, offset=cStart*size)
        dat = np.array(np.frombuffer(raw, 'float32')).reshape((cEnd-cStart, 8))
        dat[:,:3] = dat[:,:3] @ rotMat
        self.VBO[tn].write(dat, offset=cStart*size)


    def highlight(self, color, tn, mult=False):
        if mult:
            try:
                self.DRAW[tn]['highMult'].write(np.array(color, 'float32') - 1)
            except KeyError: pass
            return
        try:
            self.DRAW[tn]['highColor'].write(np.array(color, 'float32'))
        except KeyError: pass

    def setupWave(self, origin, wDir, wLen, wAmp, wSpd, numW):
        self.WAVEO = np.array(origin, 'float32').tobytes()
        self.WAVED = np.array(wDir.reshape((2,-1)), 'float32')

        self.WAVELEN = np.array(wLen, 'float32').tobytes()
        self.WAVEAMP = np.array(wAmp, 'float32').tobytes()
        self.WAVESPD = np.array(wSpd, 'float32').tobytes()
        self.WNUM = (np.int32(numW), np.int32(wSpd.reshape((-1,)).shape[0] - numW))

    def updateWave(self, pScale, stTime, tn):
        d = self.DRAW[tn]
        try:
            d['pScale'].write(np.float32(pScale))
            d['pTime'].write(self.currTime)
        except KeyError:
            draw = ctx.program(vertex_shader=trisetupWave,
                               fragment_shader=drawSSR.replace(
                                   '{REFL_LENGTH}', self.shaderParams['{REFL_LENGTH}']))
            try:
                draw['width'].write(np.float32(self.W))
                draw['height'].write(np.float32(self.H))
            except: pass

            draw['vscale'].write(self.sScale)
            draw['aspect'].write(np.float32(self.H/self.W))
            self.DRAW[tn] = draw
            self.writeShArgs(tn)
            self.VAO[tn] = ctx.vertex_array(draw, self.VBO[tn],
                                            'in_vert', 'in_norm', 'in_UV')
            draw['origin'].write(self.WAVEO)
            draw['wDir1'].write(self.WAVED[0].tobytes())
            draw['wDir2'].write(self.WAVED[1].tobytes())
            draw['wLen'].write(self.WAVELEN)
            draw['wAmp'].write(self.WAVEAMP)
            draw['wSpd'].write(self.WAVESPD)
            draw['lenW'].write(self.WNUM[0])
            draw['lenW2'].write(self.WNUM[1])


    def drawPS(self, xyz, color, opacity, size, tex=None, shader=1):
        try: _ = self.psProg
        except:
            ctx.point_size = 4
            draw = ctx.program(vertex_shader=trisetup,
                               fragment_shader=drawSub,
                               geometry_shader=makeProgram('ps.c'))

            draw['aspect'].write(np.float32(self.H/self.W))

            self.psProg = draw

        self.psProg['vscale'].write(self.sScale)
        self.psProg['size'] = size
        self.psProg['emPow'].write(np.float32(1-opacity))
        self.psProg['tColor'].write(np.array(color[0], 'float32').tobytes())

        if tex in self.PSTEX:
            self.psProg['fadeUV'] = 0
            self.psProg['useTex'] = 1
            self.psProg['tex1'] = 0
            self.PSTEX[tex].use(location=0)
        else:
            self.psProg['useTex'] = 0
            self.psProg['fadeUV'] = shader

        self.psProg['vmat'].write(self.vmat)
        self.psProg['vpos'].write(self.vc)

        p = xyz
        vertices = np.stack((p[:,0], p[:,1], p[:,2]), axis=-1)

        try:
            PSvbo = ctx.buffer(vertices.astype('float32').tobytes())
        except moderngl.Error:
            return False

        self.PSvao = ctx.vertex_array(self.psProg, PSvbo, 'in_vert')

        self.fbo.use()
        self.fbo.depth_mask = True
        ctx.enable(moderngl.DEPTH_TEST)

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.PSvao.render(moderngl.POINTS)


    def blit(self, dest, src, destW, destH):
        dest.use()
        src.use(location=0)
        self.blurProg1['width'].write(np.float32(destW))
        self.blurProg1['height'].write(np.float32(destH))
        self.blurProg1['useLum'].write(np.int32(0))
        self.blurVao1.render(moderngl.TRIANGLES)

    def distort(self, x=0.5, y=0.5, z=4, p=20, st=20):
        try: _ = self.dProg
        except:
            self.dProg = ctx.program(vertex_shader=trisetup2d,
                fragment_shader=makeProgram('Post/distort.c'))
            self.dProg['width'].write(np.float32(self.W))
            self.dProg['height'].write(np.float32(self.H))
            self.dVao = ctx.vertex_array(self.dProg, self.post_vbo, 'in_vert')

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        self.POSTFBO.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO.use()

        self.dProg['x'].write(np.float32(x))
        self.dProg['y'].write(np.float32(y))
        self.dProg['z'].write(np.float32(z))
        self.dProg['portal'].write(np.float32(p))
        self.dProg['strength'].write(np.float32(st))
        self.dProg['tex1'] = 0
        self.dProg['texd'] = 1
        self.FB.use(location=0)
        self.DBT.use(location=1)

        self.dVao.render(moderngl.TRIANGLES)

        # Copy to frame
        self.blit(self.fbo, self.POSTBUF, self.W, self.H)

    def motionBlur(self, oldPos, oldVMat):
        try: _ = self.moProg
        except:
            self.moTime = time.perf_counter()
            self.moProg = ctx.program(vertex_shader=trisetup2d,
                fragment_shader=makeProgram('Post/motion.c'))
            self.moProg['width'].write(np.float32(self.W))
            self.moProg['height'].write(np.float32(self.H))
            self.moProg['vscale'].write(self.sScale)
            self.moVao = ctx.vertex_array(self.moProg, self.post_vbo, 'in_vert')

            self.OLDBUF = ctx.texture((self.W, self.H), 3, dtype='f2')
            self.OLDDB = ctx.depth_texture((self.W, self.H))
            self.OLDFBO = ctx.framebuffer(self.OLDBUF, self.OLDDB)

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        self.POSTFBO.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO.use()

        exp = time.perf_counter() - self.moTime
        self.moTime += exp
        self.moProg['EXPOSURE'].write(np.float32(min(0.8, 1/60 / exp)))
        self.moProg['vscale'].write(self.sScale)
        self.moProg['tex1'] = 0
        self.moProg['texd'] = 1
        self.OLDBUF.use(location=0)
        self.DBT.use(location=1)

        self.moProg['Vpos'].write(self.vc)
        self.moProg['VV'].write(self.rawVM)

        self.moProg['oldPos'].write(oldPos.astype('float32'))

        oldVm = oldVMat.astype('float32')
        self.moProg['oldVV'].write(oldVm[0])
        self.moProg['oldVX'].write(oldVm[1])
        self.moProg['oldVY'].write(oldVm[2])

        self.moVao.render(moderngl.TRIANGLES)

        # Copy to oldbuf
        self.blit(self.OLDFBO, self.FB, self.W, self.H)

        # Copy to frame
        self.blit(self.fbo, self.POSTBUF, self.W, self.H)

    def setupSSAO(self):
        self.ssaoProg = ctx.program(vertex_shader=trisetup2d,
            fragment_shader=ssao)
        self.ssaoProg['width'].write(np.float32(self.W))
        self.ssaoProg['height'].write(np.float32(self.H))
        self.ssaoProg['vscale'].write(np.float32(self.sScale))
        self.ssaoVao = ctx.vertex_array(self.ssaoProg, self.post_vbo, 'in_vert')

        ra = np.random.rand(64)
        self.ssaoProg['R'].write(ra.astype('float32'))

    def ssao(self):
        try: _ = self.ssaoProg
        except: self.setupSSAO()
        self.doSSAO = True

    def setupDoF(self):
        self.dofProg = ctx.program(vertex_shader=trisetup2d,
                                   fragment_shader=dof)
        self.dofProg['width'] = self.W
        self.dofProg['height'] = self.H
        self.dofProg['tex1'] = 0
        self.dofProg['db'] = 1
        self.dofVao = ctx.vertex_array(self.dofProg, self.post_vbo, 'in_vert')

    def dof(self, focus, aperture=None):
        self.dofFocus = np.float32(focus)
        if aperture is not None:
            self.dofAperture = np.float32(aperture)

    def applyDoF(self):
        try: _ = self.dofProg
        except: self.setupDoF()

        ctx.disable(moderngl.BLEND)
        ctx.disable(moderngl.DEPTH_TEST)

        self.POSTFBO.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO.use()
        self.dofProg['focus'] = self.dofFocus
        self.dofProg['aperture'] = self.dofAperture * self.IRES
        self.FB.use(location=0)
        self.DBT.use(location=1)

        self.dofVao.render(moderngl.TRIANGLES)

        # Copy to frame
        self.blit(self.fbo, self.POSTBUF, self.W, self.H)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)


    def setupLens(self):
        pass
    def applyLens(self, i):
        try: _ = self.lensProg
        except: self.setupLens()
        self.fbo.use()
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.DRAW[i]['SM'] = 4
        self.DRAW[i]['SM2'] = 5
        self.DRAW[i]['db'] = 1
        self.DRAW[i]['vmat'].write(self.rawVM)
        self.DRAW[i]['tex1'] = 0
        self.TEX[i].use(location=0)

        self.VAO[i].render(moderngl.TRIANGLES)

    def setupBlur(self):
        # Temp
        self.POSTBUF = ctx.texture((self.W, self.H), 3, dtype='f2')
        self.POSTDB = ctx.depth_texture((self.W, self.H))
        self.POSTFBO = ctx.framebuffer(self.POSTBUF, self.POSTDB)

        # 1st pass
        self.POSTBUF1 = ctx.texture((self.W//2, self.H//2), 3, dtype='f2')
        self.POSTBUF1.repeat_x = False
        self.POSTBUF1.repeat_y = False
        self.POSTDB1 = ctx.depth_texture((self.W//2, self.H//2))
        self.POSTFBO1 = ctx.framebuffer(self.POSTBUF1, self.POSTDB1)
        # 2nd pass
        self.POSTBUF2 = ctx.texture((self.W//2, self.H//2), 3, dtype='f2')
        self.POSTBUF2.repeat_x = False
        self.POSTBUF2.repeat_y = False
        self.POSTDB2 = ctx.depth_texture((self.W//2, self.H//2))
        self.POSTFBO2 = ctx.framebuffer(self.POSTBUF2, self.POSTDB2)

        self.blurProg1 = ctx.program(vertex_shader=trisetup2d,
            fragment_shader=makeProgram('Post/bloom1.c'))
        self.blurVao1 = ctx.vertex_array(self.blurProg1, self.post_vbo, 'in_vert')

        self.blurProg2 = ctx.program(vertex_shader=trisetup2d,
            fragment_shader=makeProgram('Post/bloom2.c'))
        self.blurVao2 = ctx.vertex_array(self.blurProg2, self.post_vbo, 'in_vert')

        self.blurProg1['tex1'] = 0
        self.blurProg2['tex1'] = 0
        self.blurProg2['width'].write(np.float32(self.W//2))
        self.blurProg2['height'].write(np.float32(self.H//2))

    def blur(self, ex):

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        # Downsample once
        self.POSTFBO1.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO1.use()

        self.blurProg1['width'].write(np.float32(self.W//2))
        self.blurProg1['height'].write(np.float32(self.H//2))
        self.blurProg1['useLum'].write(np.int32(1))
        self.blurProg1['exposure'] = ex
        self.FB.use(location=0)

        self.blurVao1.render(moderngl.TRIANGLES)

        # Vertical blur
        self.POSTFBO2.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO2.use()

        self.POSTBUF1.use(location=0)

        self.blurProg2['axis'].write(np.int32(0))
        self.blurVao2.render(moderngl.TRIANGLES)

        # Horizontal blur
        self.POSTFBO1.clear(0.0, 0.0, 0.0, 0.0)
        self.POSTFBO1.use()

        self.POSTBUF2.use(location=0)

        self.blurProg2['axis'].write(np.int32(1))
        self.blurVao2.render(moderngl.TRIANGLES)

        # Blend with frame
        self.fbo.use()
        self.POSTBUF1.use(location=0)

        self.blurProg1['width'].write(np.float32(self.W))
        self.blurProg1['height'].write(np.float32(self.H))
        self.blurProg1['useLum'].write(np.int32(0))

        ctx.enable(moderngl.BLEND)
        ctx.blend_func = moderngl.ONE, moderngl.ONE

        self.blurVao1.render(moderngl.TRIANGLES)

    def gamma(self, ex, tonemap='gamma', blackPoint=0, useFxaa=0):
        tm = {'gamma':0, 'reinhard':1, 'reinhard2':2, 'aces':3}

        useFxaa &= self.ENABLE_FXAA

        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        if self.USE_FSR or useFxaa:
            self.fs_fsr.clear(0.0, 0.0, 0.0, 0.0)
            self.fs_fsr.use()
        else:
            self.fs.clear(0.0, 0.0, 0.0, 0.0)
            self.fs.use()
        self.post_prog['exposure'] = ex
        self.post_prog['tonemap'] = np.int32(tm[tonemap])
        self.post_prog['blackPoint'] = np.float32(blackPoint)

        self.FB.use(location=0)
        self.DBT.use(location=1)

        self.post_vao.render(moderngl.TRIANGLES)

        if self.USE_FSR and useFxaa:
            self.fbo.use()
            self.F_FSR.use(location=0)
            self.fxaa_vao.render(moderngl.TRIANGLES)

            self.fs2.use()
            self.FB.use(location=0)
            self.fsr_vao.render(moderngl.TRIANGLES)

            self.fs.use()
            self.FS2_GL.use(location=0)
            self.fsr_rcas_vao.render(moderngl.TRIANGLES)

        elif self.USE_FSR or useFxaa:
            self.fs.use()
            self.F_FSR.use(location=0)

        if self.USE_FSR and not useFxaa:
            self.fsr_vao.render(moderngl.TRIANGLES)
        if not self.USE_FSR and useFxaa:
            self.fxaa_vao.render(moderngl.TRIANGLES)

        ctx.enable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)


    def setScaleCull(self, s, cx, cy):
        self.sScale = np.float32(s)
        for draw in self.DRAW:
            try: draw['vscale'].write(self.sScale)
            except: pass

    def setPos(self, vc):
        self.vc = vc.astype('float32')
        for draw in self.DRAW:
            try: draw['vpos'].write(self.vc)
            except: pass

    def setVM(self, vM):
        self.rawVM = vM.astype('float32')
        vmat = np.array([-vM[1], vM[2], vM[0]])
        vmat = np.array(vmat.T, order='C')
        self.vmat = vmat.astype('float32')
        for draw in self.DRAW:
            try: draw['vmat'].write(self.vmat)
            except: pass

    def setAnisotropy(self, a):
        for tex in self.TEX:
            if max(tex.size) > 128:
                tex.anisotropy = a

    def addTextureGroup(self, xyz, uv, vn, rgb, shader=None, mip=None):
        texNum = len(self.TEX)

        rr = np.array(rgb/65535, order='C', dtype='float16')

        p = xyz.astype("float32")

        n = vn.astype("float32")

        if n.shape[0] == 1:
            n = np.repeat(n, p.shape[0], axis=0)

        uv = uv.astype("float32").reshape((p.shape[0], 2))

        draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawSh)

        draw['vscale'].write(self.sScale)
        draw['aspect'].write(np.float32(self.H/self.W))

        vertices = np.stack((p[:,0], p[:,1], p[:,2],
                             n[:,0], n[:,1], n[:,2],
                             uv[:,0], uv[:,1]), axis=-1)

        vbo = ctx.buffer(vertices.astype('float32').tobytes())
        vao = ctx.vertex_array(draw, vbo, 'in_vert', 'in_norm', 'in_UV')
        draw['tex1'] = texNum
        draw['SM'] = 0

        tex = ctx.texture(rr.shape[1::-1], 3, rr,
                          dtype='f2')

        if max(rr.shape) > 128:
            tex.anisotropy = 2

        if mip is not None or 'mip' in shader:
            tex.build_mipmaps()

        if 'texMode' in shader:
            if shader['texMode'] == 'clamp':
                tex.repeat_x = False
                tex.repeat_y = False

        self.TEX.append(tex)

        self.DRAW.append(draw)

        self.VBO.append(vbo)
        self.VAO.append(vao)

        self.texSize.append(np.int32(rr.shape[0]))
        self.gSize.append(np.int32(p.shape[0]))

        self.oldShaders[texNum] = {'shader':'', 'args':{}}

        return len(self.TEX)-1

    def setUVOff(self, tn, lo, hi, offset):
        """tn: texNum    lo, hi, offset: float2(u, v)"""
        self.DRAW[tn]['uv_lo'].write(np.array(lo, 'float32'))
        self.DRAW[tn]['uv_hi'].write(np.array(hi, 'float32'))
        self.DRAW[tn]['uv_offset'].write(np.array(offset, 'float32'))

    def changeShader(self, tn: int, mtl: dict, **kwargs):
        i = tn
        if i in self.BO:
            ts = trisetupAnim
        elif '2d' in mtl:
            ts = trisetup2d
        else:
            ts = trisetup

        p = self.VBO[i]

        shader = mtl['shader'] or 'base'


        if self.oldShaders[i]['shader'] == shader:
            draw = self.DRAW[i]
        else:
            shaderT = 'emissive' if shader == 'add' else shader

            shaderName = 'draw{}'.format(shaderT[0].upper() + shaderT[1:])

            if shader == 'lens': shaderName = 'lens'

            prog = globals()[shaderName]
            for sp in self.shaderParams:
                prog = prog.replace(sp, self.shaderParams[sp])

            progKwargs = {}
            if 'calcNorm' in mtl:
                progKwargs['geometry_shader'] = makeProgram('calcNormal.c', 'PipeGL/')
                ts = trisetupNorm
                prog = prog.replace('vec3 norm = normalize(v_norm)',
                                    'vec3 norm = normalize(v_gs_norm)')
                prog = prog.replace('in vec3 v_norm',
                                    'in vec3 v_gs_norm')

            draw = ctx.program(
                vertex_shader=ts,
                fragment_shader=prog,
                **progKwargs
            )

            if shader == 'fog':
                ra = np.random.rand(64) - 0.5
                draw['R'].write(ra.astype('float32'))

            if 'envFallback' in mtl:
                draw['useEquiEnv'] = 1
                draw['equiEnv'] = 6

            if 'roughness' in mtl['args']:
                try:
                    ra = np.random.rand(64)
                    draw['R'].write(ra.astype('float32'))
                except KeyError: pass

        for arg in mtl['args']:
            try: draw[arg] = mtl['args'][arg]
            except KeyError: print(f'Unused {arg} in shader {tn}: {mtl}')

        if 'alpha' in mtl:
            sa = mtl['alpha']
            draw['TA'] = 2
            self.TA[sa].use(location=2)
            if 'highlight' in mtl:
                draw['highMult'].write(np.array(mtl['highlight'], 'float32'))

        elif shader == 'metallic':
            draw['isMetal'] = 1

        try:
            draw['SM'] = 0
            draw['RAND'] = 2
        except KeyError: pass

        if 'normal' in mtl:
            try:
                draw['useNM'] = 1
                draw['NM'] = 7
            except KeyError: print(f'Unused normal in shader {tn}')

        try:
            if 'stage' in kwargs:
                draw['stage'] = kwargs['stage']
        except: pass

        try:
            draw['width'].write(np.float32(self.W))
            draw['height'].write(np.float32(self.H))
        except: pass
        try:
            draw['vscale'].write(self.sScale)
            draw['aspect'].write(np.float32(self.H/self.W))
        except: pass

        self.DRAW[i] = draw

        self.writeShArgs(i)

        if i in self.BO:
            vao = ctx.vertex_array(draw,
                [(p, '3f 3f 2f /v', 'in_vert', 'in_norm', 'in_UV'),
                 (self.BN[i], '1f /v', 'boneNum')])
        else:
            vao = ctx.vertex_array(draw, p, 'in_vert', 'in_norm', 'in_UV')

        self.oldShaders[i] = dict(mtl)

        self.VAO[i] = vao

    def changeShaderZ(self, tn, shader):
        i = tn
        p = self.VBO[i]
        if 'alpha' in shader:
            draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawZAlpha)
            draw['TA'] = 2
            vao = ctx.vertex_array(draw, [(p, '3f4 3x4 2f4 /v', 'in_vert', 'in_UV')])
        elif 'dissolve' in shader:
            if 'dissolve' in self.oldShaders[i]:
                draw = self.DRAWZ[i][1]
                vao = self.DRAWZ[i][0]
            else:
                draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawZDissolve)
                vao = ctx.vertex_array(draw, [(p, '3f4 3x4 2f4 /v', 'in_vert', 'in_UV')])
            draw['fadeOrigin'].write(np.array(shader['dissolve']['origin'], 'float32'))
            draw['fadeFact'].write(shader['dissolve']['fact'])
        else:
            draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawZ)
            vao = ctx.vertex_array(draw, [(p, '3f4 5x4 /v', 'in_vert')])
        draw['aspect'].write(np.float32(self.H/self.W))
        self.DRAWZ[i] = (vao, draw)


    def drawAll(self, shaders, mask=None, shadowIds=[0,1], **kwargs):

        if mask is None:
            mask = [False] * len(shaders)

        for i in range(len(self.VBO)):
            if shaders[i] != self.oldShaders[i]:
                self.changeShader(i, shaders[i], **kwargs)

        self.currTime = np.float32(time.time() - self.stTime)

        # Write to readable depth buffer
        self.fboZ.use()
        self.fboZ.clear(red=2048.0, depth=1.0)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        for i in range(len(self.VBO)):
            if mask[i]: continue
            if shaders[i]['shader'] in TRANSPARENT_SHADERS: continue

            try: _ = self.DRAWZ[i]
            except KeyError:
                p = self.VBO[i]

                dZ = drawZAlpha if 'alpha' in shaders[i] else drawZ
                va1 = (p, '3f4 5x4 /v', 'in_vert')
                if 'alpha' in shaders[i]:
                    va1 = (p, '3f4 3x4 2f4 /v', 'in_vert', 'in_UV')

                if i in self.BO:
                    draw = ctx.program(vertex_shader=trisetupAnim, fragment_shader=dZ)
                    vao = ctx.vertex_array(draw,
                        [va1, (self.BN[i], '1f /v', 'boneNum')])
                else:
                    draw = ctx.program(vertex_shader=trisetup, fragment_shader=dZ)
                    vao = ctx.vertex_array(draw, [va1])

                if 'alpha' in shaders[i]:
                    draw['TA'] = 2
                draw['aspect'].write(np.float32(self.H/self.W))
                self.DRAWZ[i] = (vao, draw)
            if 'cull' in shaders[i]:
                ctx.enable(moderngl.CULL_FACE)
            else:
                ctx.disable(moderngl.CULL_FACE)

            self.DRAWZ[i][1]['vscale'].write(self.sScale)
            self.DRAWZ[i][1]['vpos'].write(self.vc)
            self.DRAWZ[i][1]['vmat'].write(self.vmat)

            if 'alpha' in shaders[i]:
                sa = shaders[i]['alpha']
                self.TA[sa].use(location=2)

            self.DRAWZ[i][0].render(moderngl.TRIANGLES)


        self.fbo.use()
        self.fbo.depth_mask = True

        # Opaque
        for i in range(len(self.VBO)):
            if mask[i]: continue
            vao = self.VAO[i]

            if 'cull' in shaders[i]:
                ctx.enable(moderngl.CULL_FACE)
            else:
                ctx.disable(moderngl.CULL_FACE)

            if not shaders[i]['shader'] in TRANSPARENT_SHADERS:
                self.DRAW[i]['tex1'] = 0
                self.TEX[i].use(location=0)

                if 'alpha' in shaders[i]:
                    sa = shaders[i]['alpha']
                    self.TA[sa].use(location=2)
                elif 'noise' in shaders[i]:
                    self.noiseTex.use(location=2)
                    self.DRAW[i]['RAND'] = 2
                    self.DRAW[i]['useNoise'] = 1
                    self.DRAW[i]['noiseDist'] = self.noiseDist
                    self.DRAW[i]['noisePos'].write(self.noisePos.astype('float32'))
                if 'normal' in shaders[i]:
                    try:
                        self.NM[shaders[i]['normal']].use(location=7)
                    except KeyError:
                        print('Normal map {} not found'.format(shaders[i]['normal']))
                if 'ignoreShadow' in shaders[i]:
                    self.DRAW[i]['ignoreShadow'] = shaders[i]['ignoreShadow']

                vao.render(moderngl.TRIANGLES)


        self.fbo.depth_mask = False

        if self.doSSAO:
            ctx.disable(moderngl.DEPTH_TEST)

            self.POSTFBO.clear(0.0, 0.0, 0.0, 0.0)
            self.POSTFBO.use()
            self.ssaoProg['vscale'].write(np.float32(self.sScale))
            self.ssaoProg['tex1'] = 0
            self.ssaoProg['texd'] = 1
            self.FB.use(location=0)
            self.DBT.use(location=1)

            self.ssaoVao.render(moderngl.TRIANGLES)

            # Copy to frame
            self.blit(self.fbo, self.POSTBUF, self.W, self.H)
            ctx.enable(moderngl.DEPTH_TEST)
            self.doSSAO = False

        ctx.enable(moderngl.BLEND)

        # Transparent
        for i in range(len(self.VBO)):
            if mask[i]: continue
            vao = self.VAO[i]

            shader = shaders[i]['shader']

            if shader in ('add', 'border', 'special'):
                ctx.blend_func = moderngl.ONE, moderngl.ONE
                if shader == 'special':
                    self.DRAW[i]['VV'].write(self.rawVM[0])

                try: self.DRAW[i]['iTime'].write(self.currTime)
                except KeyError: pass

            elif 'SSR' in shader:
                ctx.disable(moderngl.CULL_FACE)
                ctx.disable(moderngl.DEPTH_TEST)
                ctx.disable(moderngl.BLEND)
                self.POSTFBO.clear(0.0, 0.0, 0.0, 0.0)
                self.blit(self.POSTFBO, self.FB, self.W, self.H)
                ctx.enable(moderngl.DEPTH_TEST)
                ctx.enable(moderngl.BLEND)

                self.fbo.use()
                if shader == 'SSRopaque':
                    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
                    ctx.depth_func = '<='
                else:
                    ctx.blend_func = moderngl.ONE, moderngl.SRC_ALPHA
                self.POSTBUF.use(location=3)
                self.DRAW[i]['currFrame'] = 3
                self.DRAW[i]['db'] = 1
                self.DRAW[i]['rawVM'].write(self.rawVM)
                if 'envFallback' in shaders[i]:
                    self.TEX[shaders[i]['envFallback']].use(location=6)
                if 'normal' in shaders[i]:
                    try:
                        self.NM[shaders[i]['normal']].use(location=7)
                    except KeyError:
                        print('Normal map {} not found'.format(shaders[i]['normal']))

            elif shader == 'sub':
                ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            elif shader == 'fog':
                ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
                self.DBT.use(location=1)
                self.DRAW[i]['SM'] = 4
                self.DRAW[i]['db'] = 1
                self.DRAW[i]['vmat'].write(self.rawVM)
            elif shader == 'lens':
                self.lensTn = i
                continue
            else:
                continue
            if 'cull' in shaders[i]:
                ctx.enable(moderngl.CULL_FACE)
            else:
                ctx.disable(moderngl.CULL_FACE)

            self.DRAW[i]['tex1'] = 0
            self.TEX[i].use(location=0)

            vao.render(moderngl.TRIANGLES)

            if shader == 'SSRopaque':
                ctx.depth_func = '<'
            if shader == 'add' or shader == 'sub':
                if 'noline' not in shaders[i]:
                    vao.render(moderngl.LINES)

        self.fbo.depth_mask = True


    def clearZBuffer(self):
        self.fbo.clear(0.0, 0.0, 0.0, 1.0)

    def addBakedShadow(self, i, tex):
        assert i == 0
        t = ctx.texture(tex.shape, 1, tex)
        s = self.SHADOWMAP[i]
        s['sm_baked'] = t
        s['sm_baked_size'] = tex.shape[0]

    def addShadowMap(self, i, size, scale, ambLight=None, gi=None):
        c = ctx.texture((size,size), 1, dtype='f4')
        d = ctx.depth_texture((size,size))
        s = {}
        s['map'] = ctx.framebuffer((c,), d)
        s['tex'] = c
        s['scale'] = np.float32(scale * 2 / size)
        s['dim'] = np.int32(size)
        self.SHADOWMAP[i] = s

        s['tex'].filter = moderngl.NEAREST, moderngl.NEAREST

        try: _ = self.drawS
        except AttributeError:
            self.drawS = ctx.program(vertex_shader=trisetupOrtho,
                                     fragment_shader=drawMin)
            self.drawSA = ctx.program(vertex_shader=trisetupOrtho,
                                      fragment_shader=drawMinAlpha)

            for n in range(len(self.VBO)):
                vbo = self.VBO[n]
                vao = ctx.vertex_array(self.drawS,
                                       [(vbo, '3f4 5x4', 'in_vert')])
                self.SVA.append(vao)

    def placeShadowMap(self, i, pos, facing, ambLight=None, updateShaders=False):
        sm = self.SHADOWMAP[i]
        sm['pos'] = pos.astype('float32')
        f = viewMat(*facing)
        f = np.array([-f[1], f[2], f[0]])
        f = np.array(f.T, order='C')
        sm['vec'] = f.astype('float32')

        if not updateShaders: return

        for n in range(len(self.VBO)):
            if n in self.BN:
                vbo = self.VBO[n]
                if 'alpha' in self.oldShaders[n]:
                    dm = drawMinAlpha
                    vbosetup = (vbo, '3f 3x4 2f4 /v', 'in_vert', 'in_UV')
                else:
                    dm = drawMin
                    vbosetup = (vbo, '3f 5x4 /v', 'in_vert')
                self.drawSB[n] = ctx.program(vertex_shader=trisetupOrthoAnim,
                                             fragment_shader=dm)
                if 'alpha' in self.oldShaders[n]:
                    self.drawSB[n]['TA'] = 2

                vao = ctx.vertex_array(self.drawSB[n],
                                       [vbosetup, (self.BN[n], '1f /v', 'boneNum')])
                self.SVA[n].release()
                self.SVA[n] = vao

            elif 'alpha' in self.oldShaders[n]:
                vbo = self.VBO[n]
                vao = ctx.vertex_array(self.drawSA,
                                       [(vbo, '3f4 3x4 2f4 /v', 'in_vert', 'in_UV')])
                self.SVA[n].release()
                self.SVA[n] = vao

    def clearShadowMap(self, i):
        self.SHADOWMAP[i]['map'].clear(red=1.0, depth=1.0)

    def shadowMap(self, i, whichCast, shaders, bias):
        sm = self.SHADOWMAP[i]
        sm['map'].use()

        self.drawS['vscale'].write(sm['scale'])
        self.drawS['vpos'].write(sm['pos'])
        self.drawS['vmat'].write(sm['vec'])
        self.drawS['sbias'] = bias/2
        self.drawSA['vscale'].write(sm['scale'])
        self.drawSA['vpos'].write(sm['pos'])
        self.drawSA['vmat'].write(sm['vec'])
        self.drawSA['sbias'] = bias/2
        for n in self.drawSB:
            self.drawSB[n]['vscale'].write(sm['scale'])
            self.drawSB[n]['vpos'].write(sm['pos'])
            self.drawSB[n]['vmat'].write(sm['vec'])
            self.drawSB[n]['sbias'] = bias/2

        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        for n in range(min(len(whichCast), len(self.SVA))):
            if whichCast[n]:
                if 'alpha' in shaders[n]:
                    ta = shaders[n]['alpha']
                    self.drawSA['TA'] = 2
                    self.TA[ta].use(location=2)

                sva = self.SVA[n]
                sva.render(moderngl.TRIANGLES)

        sm['tex'].use(location=4+i)
        if 'sm_baked' in sm:
            sm['sm_baked'].use(location=6)

        self.fbo.use()
        ctx.enable(moderngl.BLEND)

        for n in range(len(self.DRAW)):
            self.writeShArgs(n)

    def writeShArgs(self, i):
        sm = self.SHADOWMAP[0]
        draw = self.DRAW[i]
        try:
            draw['SM'] = 4
            draw['SPos'].write(sm['pos'])
            draw['SV'].write(sm['vec'])
            draw['wS'] = np.int32(sm['dim'])
            draw['sScale'].write(sm['scale'])
        except KeyError: pass
        try:
            draw['SM_im'] = 6
            sm['sm_baked'].use(location=6)
            draw['wS_im'] = np.int32(sm['sm_baked_size'])
        except KeyError: pass

        sm = self.SHADOWMAP[1]
        try:
            draw['SM2'] = 5
            draw['SPos2'].write(sm['pos'])
            draw['SV2'].write(sm['vec'])
            draw['wS2'] = np.int32(sm['dim'])
            draw['sScale2'].write(sm['scale'])
        except KeyError: pass

    def setPrimaryLight(self, dirI, dirD):
        i = dirI.astype("float32")
        d = dirD.astype("float32")

        for draw in self.DRAW:
          try:
            draw['LInt'].write(i)
            draw['LDir'].write(d)
          except KeyError: pass

    def getSHM(self, i):
        sm = self.SHADOWMAP[i]
        s = np.frombuffer(sm['tex'].read(), 'float32')
        return s.reshape((sm['dim'], sm['dim']))

    def getFrame(self):
        shape = (self.outH, self.outW, 3)
        h = np.frombuffer(self.fs.read(), "uint8").reshape(shape)
        return h

    def getDB(self):
        shape = (self.H, self.W)
        return np.frombuffer(self.DBT.read(), 'float32').reshape(shape)
