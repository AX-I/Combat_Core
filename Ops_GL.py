# ModernGL rasterization

import numpy as np
import time
from Utils import viewMat
import json

import moderngl

import os

import OpsConv
PATH = OpsConv.PATH

ctx = moderngl.create_standalone_context()
print("Using", ctx.info["GL_RENDERER"])

def makeProgram(f, path="ShadersGL/"):
    t = open(PATH + path + f).read()
    return t

trisetup = makeProgram("trisetup.c", "PipeGL/")
trisetupAnim = makeProgram("trisetup_anim.c", "PipeGL/")
trisetupOrtho = makeProgram("trisetupOrtho.c", "PipeGL/")
trisetupOrthoAnim = makeProgram("trisetupOrtho_anim.c", "PipeGL/")
trisetup2d = makeProgram("trisetup_2d.c", "PipeGL/")

drawBase = makeProgram("drawbase.c")
drawSh = makeProgram("drawsh.c")
drawAlpha = makeProgram("drawshalpha.c")
drawSky = makeProgram("drawsky.c")
drawSub = makeProgram("drawsub.c")
drawBorder = makeProgram("drawborder.c")
drawEm = makeProgram("drawemissive.c")
drawMin = makeProgram("drawmin.c")
drawZ = makeProgram("drawZ.c")

gamma = makeProgram("Post/gamma.c")

ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.BLEND)
ctx.front_face = 'cw'

def align34(a):
    return np.stack((a[:,0], a[:,1], a[:,2], np.zeros_like(a[:,0])), axis=1)

class CLDraw:
    def __init__(self, size_sky, max_uv, w, h, max_particles):

        # Internal resolution for supersampling
        self.IRES = 1

        self.W = np.int32(w * self.IRES)
        self.H = np.int32(h * self.IRES)
        self.A = w*h

        self.FB = ctx.texture((self.W, self.H), 3, dtype='f2')
        self.DB = ctx.depth_texture((self.W, self.H))
        self.fbo = ctx.framebuffer(self.FB, self.DB)
        self.fbo.use()

        self.fs = ctx.simple_framebuffer((w, h))

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
        self.TA = []
        self.DRAW = []
        self.DRAWZ = {}

        self.texSize = []

        self.SHADOWMAP = {}
        self.SVA = []
        self.drawSB = {}


        x = np.array([-1, -1, 1, 1, -1, 1])
        y = np.array([1, -1, 1, 1, -1, -1])
        z = np.ones(6)*-0.9999
        vertices = np.dstack([x, y, z])

        self.post_vbo = ctx.buffer(vertices.astype('float32').tobytes())
        self.post_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=gamma)
        self.post_vao = ctx.vertex_array(self.post_prog, self.post_vbo, 'in_vert')
        self.post_prog['width'].write(np.float32(w))
        self.post_prog['height'].write(np.float32(h))

        self.oldShaders = {}

    def setSkyTex(self, r, g, b, size):
        pass
    def setHostSkyTex(self, tex):
        pass

    def setReflTex(self, name, r, g, b, size):
        pass
    def addTexAlpha(self, tex):
        ta = tex.astype('uint8') * 255
        a = ctx.texture(tex.shape[::-1], 1, ta)
        self.TA.append(a)

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
        self.DInt = np.zeros((4, 3), 'float32')
        self.DDir = np.zeros((4, 3), 'float32')
        self.DInt[:ld] = dirI
        self.DDir[:ld] = dirD

        if pointI is 1:
            pointI = np.zeros(3)
            pointP = np.zeros(3)

        lp = pointI.shape[0]

        self.PInt = np.zeros((16, 3), 'float32')
        self.PPos = np.zeros((16, 3), 'float32')
        self.PInt[:lp] = pointI
        self.PPos[:lp] = pointP


        for n in range(len(self.DRAW)):
            try:
                self.DRAW[n]['DInt'].write(self.DInt.tobytes())
                self.DRAW[n]['DDir'].write(self.DDir.tobytes())
                self.DRAW[n]['lenD'] = ld
                self.DRAW[n]['PInt'].write(self.PInt.tobytes())
                self.DRAW[n]['PPos'].write(self.PPos.tobytes())
                self.DRAW[n]['lenP'] = lp
                self.DRAW[n]['highColor'].write(np.zeros(3, 'float32'))
            except KeyError:
                pass

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

    def highlight(self, color, tn):
        try:
            self.DRAW[tn]['highColor'].write(np.array(color, 'float32'))
        except KeyError: pass

    def setupWave(self, *args, **kwargs):
        pass
    def updateWave(self, *args):
        pass

    def drawPS(self, *args):
        pass

    def distort(self, x=0.5, y=0.5, z=4, p=20, st=20):
        pass
    def motionBlur(self, oldPos, oldVMat):
        pass
    def ssao(self):
        pass
    def dof(self, d):
        pass
    def blur(self):
        pass
    def gamma(self, ex):
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        self.fs.clear(0.0, 0.0, 0.0, 0.0)
        self.fs.use()
        self.post_prog['tex1'] = 0
        self.post_prog['exposure'] = ex
        self.FB.use(location=0)

        self.post_prog['db'] = 1
        self.DBT.use(location=1)

        self.post_vao.render(moderngl.TRIANGLES)

        ctx.enable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)


    def setScaleCull(self, s, cx, cy):
        self.sScale = np.float32(s)
        for draw in self.DRAW:
            draw['vscale'].write(self.sScale)

    def setPos(self, vc):
        self.vc = vc.astype('float32')
        for draw in self.DRAW:
            draw['vpos'].write(self.vc)

    def setVM(self, vM):
        vmat = np.array([-vM[1], vM[2], vM[0]])
        vmat = np.array(vmat.T, order='C')
        self.vmat = vmat.astype('float32')
        for draw in self.DRAW:
            draw['vmat'].write(self.vmat)

    def addTextureGroup(self, xyz, uv, vn, r, g, b, shader=None, mip=None):
        texNum = len(self.TEX)

        rr = np.array(r/65536, order='C', dtype='float16')
        gg = np.array(g/65536, order='C', dtype='float16')
        bb = np.array(b/65536, order='C', dtype='float16')

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

        tex = ctx.texture(rr.shape[::-1], 3, np.stack((rr,gg,bb), axis=-1),
                          dtype='f2')

        if mip is not None:
            tex.build_mipmaps()

        tex.use(location=texNum)

        self.TEX.append(tex)

        self.DRAW.append(draw)

        self.VBO.append(vbo)
        self.VAO.append(vao)

        self.texSize.append(np.int32(rr.shape[0]))
        self.gSize.append(np.int32(p.shape[0]))

        self.oldShaders[texNum] = ""

        return len(self.TEX)-1


    def drawAll(self, shaders, mask=None, shadowIds=[0,1], **kwargs):

        if mask is None:
            mask = [False] * len(shaders)

        self.fbo.use()

        for i in range(len(self.VBO)):
            if shaders[i] != self.oldShaders[i]:

                if i in self.BO:
                    ts = trisetupAnim
                else:
                    ts = trisetup

                p = self.VBO[i]

                if 'sky' in shaders[i]:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawSky)
                elif 'alpha' in shaders[i]:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawAlpha)
                    sa = shaders[i]['alpha']
                    draw['TA'] = sa + 2
                    self.TA[sa].use(location=sa + 2)

                elif 'emissive' in shaders[i]:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawEm)
                    draw['vPow'].write(np.float32(shaders[i]['emissive']))

                elif 'add' in shaders[i]:
                    if 'add' in self.oldShaders[i]:
                        draw = self.DRAW[i]
                    else:
                        draw = ctx.program(vertex_shader=ts, fragment_shader=drawEm)
                    draw['vPow'].write(np.float32(shaders[i]['add']))

                elif 'sub' in shaders[i]:
                    if 'sub' in self.oldShaders[i]:
                        draw = self.DRAW[i]
                    else:
                        draw = ctx.program(vertex_shader=ts, fragment_shader=drawSub)
                    draw['emPow'].write(np.float32(shaders[i]['sub']))

                elif 'border' in shaders[i]:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawBorder)
                    draw['width'].write(np.float32(self.W))
                    draw['height'].write(np.float32(self.H))

                else:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawSh)
                    draw['SM'] = 0

                draw['vscale'].write(self.sScale)
                draw['aspect'].write(np.float32(self.H/self.W))

                self.DRAW[i] = draw

                self.writeShArgs(i)

                if i in self.BO:
                    vao = ctx.vertex_array(draw,
                        [(p, '3f 3f 2f /v', 'in_vert', 'in_norm', 'in_UV'),
                         (self.BN[i], '1f /v', 'boneNum')])
                else:
                    vao = ctx.vertex_array(draw, p, 'in_vert', 'in_norm', 'in_UV')

                self.oldShaders[i] = dict(shaders[i])

                self.VAO[i] = vao

        ctx.blend_func = moderngl.ONE, moderngl.ZERO
        ctx.blend_equation = moderngl.FUNC_ADD
        self.fbo.depth_mask = True

        # Opaque
        for i in range(len(self.VBO)):
            if mask[i]: continue
            vao = self.VAO[i]

            if 'cull' in shaders[i]:
                ctx.enable(moderngl.CULL_FACE)
            else:
                ctx.disable(moderngl.CULL_FACE)

            trans = {'add', 'border', 'SSR', 'sub'}
            if all(t not in shaders[i] for t in trans):
                self.DRAW[i]['tex1'] = 0
                self.TEX[i].use(location=0)

                vao.render(moderngl.TRIANGLES)


        self.fbo.depth_mask = False

        # Transparent
        for i in range(len(self.VBO)):
            if mask[i]: continue
            vao = self.VAO[i]

            if 'add' in shaders[i] or 'border' in shaders[i]:
                ctx.blend_func = moderngl.ONE, moderngl.ONE
                ctx.blend_equation = moderngl.FUNC_ADD
            elif 'SSR' in shaders[i]:
                ctx.blend_func = moderngl.ONE, moderngl.ONE
                ctx.blend_equation = moderngl.FUNC_ADD
            elif 'sub' in shaders[i]:
                ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
                ctx.blend_equation = moderngl.FUNC_ADD
            else:
                continue

            self.DRAW[i]['tex1'] = 0
            self.TEX[i].use(location=0)

            vao.render(moderngl.TRIANGLES)

            if 'add' in shaders[i]:
                vao.render(moderngl.LINES)

        self.fbo.depth_mask = True

        # Write to readable depth buffer
        self.fboZ.use()
        self.fboZ.clear(red=1.0, depth=1.0)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        for i in range(len(self.VBO)):
            if mask[i]: continue
            trans = {'add', 'border', 'SSR', 'sub'}
            if any(t in shaders[i] for t in trans): continue

            try: _ = self.DRAWZ[i]
            except KeyError:
                p = self.VBO[i]
                if i in self.BO:
                    draw = ctx.program(vertex_shader=trisetupAnim, fragment_shader=drawZ)
                    vao = ctx.vertex_array(draw,
                        [(p, '3f4 5x4 /v', 'in_vert'),
                         (self.BN[i], '1f /v', 'boneNum')])
                else:
                    draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawZ)
                    vao = ctx.vertex_array(draw, [(p, '3f4 5x4 /v', 'in_vert')])
                draw['aspect'].write(np.float32(self.H/self.W))
                self.DRAWZ[i] = (vao, draw)
            if 'cull' in shaders[i]:
                ctx.enable(moderngl.CULL_FACE)
            else:
                ctx.disable(moderngl.CULL_FACE)

            self.DRAWZ[i][1]['vscale'].write(self.sScale)
            self.DRAWZ[i][1]['vpos'].write(self.vc.astype("float32"))
            self.DRAWZ[i][1]['vmat'].write(self.vmat.astype("float32"))

            self.DRAWZ[i][0].render(moderngl.TRIANGLES)

        ctx.enable(moderngl.BLEND)

    def clearZBuffer(self):
        self.fbo.clear(0.0, 0.0, 0.0, 1.0)

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

            for n in range(len(self.VBO)):
                vbo = self.VBO[n]
                vao = ctx.vertex_array(self.drawS,
                                       [(vbo, '3f4 5x4', 'in_vert')])
                self.SVA.append(vao)

    def placeShadowMap(self, i, pos, facing, ambLight=None):
        sm = self.SHADOWMAP[i]
        sm['pos'] = pos.astype('float32')
        f = viewMat(*facing)
        f = np.array([-f[1], f[2], f[0]])
        f = np.array(f.T, order='C')
        sm['vec'] = f.astype('float32')

        for n in range(len(self.VBO)):
            if n in self.BN:
                if n in self.drawSB: continue
                self.drawSB[n] = ctx.program(vertex_shader=trisetupOrthoAnim,
                                             fragment_shader=drawMin)
                vbo = self.VBO[n]
                vao = ctx.vertex_array(self.drawSB[n],
                                       [(vbo, '3f 5x4 /v', 'in_vert'),
                                        (self.BN[n], '1f /v', 'boneNum')])
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
        for n in self.drawSB:
            self.drawSB[n]['vscale'].write(sm['scale'])
            self.drawSB[n]['vpos'].write(sm['pos'])
            self.drawSB[n]['vmat'].write(sm['vec'])
            self.drawSB[n]['sbias'] = bias/2

        ctx.enable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)

        for n in range(len(self.SVA)):
            if n < len(whichCast) and whichCast[n]:
                sva = self.SVA[n]
                sva.render(moderngl.TRIANGLES)

        sm['tex'].use(location=4+i)

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
        except KeyError: return
        sm = self.SHADOWMAP[1]
        try:
            draw[i]['SM2'] = 5
            draw[i]['SPos2'].write(sm['pos'])
            draw[i]['SV2'].write(sm['vec'])
            draw[i]['wS2'] = np.int32(sm['dim'])
            draw[i]['sScale2'].write(sm['scale'])
        except KeyError: pass

    def setPrimaryLight(self, dirI, dirD):
        i = dirI.astype("float32")
        d = dirD.astype("float32")

        for draw in self.DRAW:
            draw['LInt'].write(i)
            draw['LDir'].write(d)

    def getSHM(self, i):
        sm = self.SHADOWMAP[i]
        s = np.frombuffer(sm['tex'].read(), 'float32')
        return s.reshape((sm['dim'], sm['dim']))

    def getFrame(self):
        shape = (int(self.H//self.IRES), int(self.W//self.IRES), 3)
        h = np.frombuffer(self.fs.read(), "uint8").reshape(shape)
        return h
