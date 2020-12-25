# ModernGL rasterization

import numpy as np
import time
from Utils import viewMat
import json

import moderngl

import os

ctx = moderngl.create_standalone_context()
print("Using", ctx.info["GL_RENDERER"])

def makeProgram(f, path="Shaders/"):
    t = open(path + f).read()
    return t

vert = makeProgram("vert.c", "Pipe/")

trisetup = makeProgram("trisetup.c", "Pipe/")
trisetupOrtho = makeProgram("trisetupOrtho.c", "Pipe/")
trisetup2d = makeProgram("trisetup_2d.c", "Pipe/")
trisetupAnim = makeProgram("trisetup_anim.c", "Pipe/")

drawBase = makeProgram("drawbase.c")
drawSh = makeProgram("drawsh.c")
drawSky = makeProgram("drawsky.c")
drawSub = makeProgram("drawsub.c")
drawBorder = makeProgram("drawborder.c")
drawEm = makeProgram("drawemissive.c")
drawMin = makeProgram("drawmin.c")

gamma = makeProgram("Post/gamma.c")

ctx.enable(moderngl.DEPTH_TEST)
ctx.enable(moderngl.BLEND)


def makeRBuf(nbytes):
    return cl.Buffer(ctx, mf.READ_ONLY, size=nbytes)

def align34(a):
    return np.stack((a[:,0], a[:,1], a[:,2], np.zeros_like(a[:,0])), axis=1)

class CLDraw:
    def __init__(self, size_sky, max_uv, w, h, max_particles):
        
        # Internal resolution for supersampling
        self.IRES = 1
        
        self.W = np.int32(w)
        self.H = np.int32(h)
        self.A = w*h

        self.FB = ctx.texture((w, h), 3, dtype='f1')
        self.DB = ctx.depth_texture((w, h))
        self.fbo = ctx.framebuffer(self.FB, self.DB)
        self.fbo.use()

        self.fs = ctx.simple_framebuffer((w//self.IRES, h//self.IRES))

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
        self.DRAW = []
        
        self.texSize = []

        self.SHADOWMAP = {}
        self.SVA = []


        x = np.array([-1, -1, 1, 1, -1, 1])
        y = np.array([1, -1, 1, 1, -1, -1])
        z = np.ones(6)*-0.9999
        vertices = np.dstack([x, y, z])
        
        self.post_vbo = ctx.buffer(vertices.astype('float32').tobytes())
        self.post_prog = ctx.program(vertex_shader=trisetup2d, fragment_shader=gamma)
        self.post_vao = ctx.vertex_array(self.post_prog, self.post_vbo, 'in_vert')
        self.post_prog['width'].write(np.float32(self.W))
        self.post_prog['height'].write(np.float32(self.H))
        
        self.oldShaders = {}

    def setSkyTex(self, r, g, b, size):
        pass
    def setHostSkyTex(self, tex):
        pass
    
    def setReflTex(self, name, r, g, b, size):
        pass
    def addTexAlpha(self, tex):
        pass

    def addBoneWeights(self, tn, bw):
        dat = bw.reshape((-1,))        
        bn = ctx.buffer(dat.astype('float32').tobytes())
        self.BN[tn] = bn

    def initBoneTransforms(self, name, bn):
        s = np.zeros((4,4),dtype="float32")
        self.BT[name] = ctx.buffer(reserve=32*s.nbytes)
        self.boneNums[name] = bn

    def initBoneOrigin(self, o, bn, tn):
        if tn not in self.BO:
            self.BO[tn] = np.zeros((32, 3), "float32")

        self.BO[tn][bn] = o

    def setBoneTransform(self, name, bt):
        self.BT[name] = np.zeros((32*4, 4), 'float32')
        self.BT[name][:4*self.boneNums[name]] = bt.astype("float32")
    
    def boneTransform(self, cStart, cEnd, tn, name, offset):
        try:
            self.DRAW[tn]['RR'].write(self.BT[name].tobytes())
            self.DRAW[tn]['off'] = offset
            self.DRAW[tn]['bOrigin'].write(self.BO[tn].tobytes())
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
                self.DRAW[n]['PInt'].write(self.PInt.tobytes())
                self.DRAW[n]['PPos'].write(self.PPos.tobytes())
                self.DRAW[n]['lenP'] = lp
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
        pass

    def setupWave(self, *args, **kwargs):
        pass
    def updateWave(self, *args):
        pass

    def drawPS(self, *args):
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
        self.post_prog['tex1'] = len(self.DRAW) + 2
        self.FB.use(location=len(self.DRAW) + 2)
        self.post_vao.render(moderngl.TRIANGLES)
        
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.enable(moderngl.BLEND)
        

    def setScaleCull(self, s, cx, cy):
        self.sScale = np.float32(s)
        for draw in self.DRAW:
            draw['vscale'].write(np.float32(self.sScale))

    def setPos(self, vc):
        for draw in self.DRAW:
            draw['vpos'].write(vc.astype("float32"))
    
    def setVM(self, vM):
        vmat = np.array([-vM[1], vM[2], vM[0]])
        vmat = np.array(vmat.T, order='C')
        for draw in self.DRAW:
            draw['vmat'].write(vmat.astype("float32"))

    def addTextureGroup(self, xyz, uv, vn, r, g, b, shader, mip=None):
        texNum = len(self.TEX)
        
        rr = np.array(r>>5, order='C', dtype='uint8')
        gg = np.array(g>>5, order='C', dtype='uint8')
        bb = np.array(b>>5, order='C', dtype='uint8')
        
        p = xyz.astype("float32")
        
        n = vn.astype("float32")

        if n.shape[0] == 1:
            n = np.repeat(n, p.shape[0], axis=0)

        uv = uv.astype("float32").reshape((p.shape[0], 2))

        draw = ctx.program(vertex_shader=trisetup, fragment_shader=drawSh)

        draw['vscale'].write(np.float32(self.sScale))
        draw['aspect'].write(np.float32(self.H/self.W))
        
        vertices = np.stack((p[:,0], p[:,1], p[:,2],
                             n[:,0], n[:,1], n[:,2],
                             uv[:,0], uv[:,1]), axis=-1)

        vbo = ctx.buffer(vertices.astype('float32').tobytes())
        vao = ctx.vertex_array(draw, vbo, 'in_vert', 'in_norm', 'in_UV')
        draw['tex1'] = texNum
        draw['SM'] = 0

        tex = ctx.texture(rr.shape[::-1], 3, np.stack((rr,gg,bb), axis=-1))
        
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
        
        self.fbo.use()
        # print(shaders)
        # {0: {'refl': '1a'}, 1: {'shadow': 'R', 'alpha': 0}, 2: {'shadow': 'R'},
        # 3: {'shadow': 'R'}, 4: 'sky', 5: {'emissive': 2}, 6: {'emissive': 2.5},
        # 7: {'add': 0.4}, 8: {'emissive': 1.4}, 9: {'emissive': 0.0},
        # 10: {'SSR': '0'}, 11: {'add': 2.0}, 12: {'border': 0.1}}
        
        for i in range(len(self.VBO)):
            if shaders[i] != self.oldShaders[i]:
                #print(shaders[i])

                if i in self.BO:
                    ts = trisetupAnim
                else:
                    ts = trisetup
                
                p = self.VBO[i]

                if 'sky' in shaders[i]:
                    draw = ctx.program(vertex_shader=ts, fragment_shader=drawSky)
                    
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

                draw['vscale'].write(np.float32(self.sScale))
                draw['aspect'].write(np.float32(self.H/self.W))
                draw['tex1'] = i
                
                self.DRAW[i] = draw

                if i in self.BO:
                    vao = ctx.vertex_array(draw,
                        [(p, '3f 3f 2f /v', 'in_vert', 'in_norm', 'in_UV'),
                         (self.BN[i], '1f /v', 'boneNum')])
                else:
                    vao = ctx.vertex_array(draw, p, 'in_vert', 'in_norm', 'in_UV')
                
                self.oldShaders[i] = dict(shaders[i])
##                for arg in args:
##                    p[arg].write(arg)

                self.VAO[i] = vao

                ctx.finish()
                
##            if shaders[i]['shadow'] == 'R':
##                vao = ctx.vertex_array(drawSh, vbo,
##                                       'in_vert', 'in_norm', 'in_UV')
##                drawSh['LInt'].write(i)
##                drawSh['LDir'].write(d)
##            else:
##                vao = self.VAO[i]


        ctx.blend_func = moderngl.ONE, moderngl.ZERO
        ctx.blend_equation = moderngl.FUNC_ADD
        self.fbo.depth_mask = True

        # Opaque
        for i in range(len(self.VBO)):
            vao = self.VAO[i]

            trans = {'add', 'border', 'SSR', 'sub'}
            if all(t not in shaders[i] for t in trans):
                vao.render(moderngl.TRIANGLES)

        
        self.fbo.depth_mask = False
        
        # Transparent
        for i in range(len(self.VBO)):
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

            vao.render(moderngl.TRIANGLES)

##        self.oldShaders = shaders
        self.fbo.depth_mask = True

    def clearZBuffer(self):
        self.fbo.clear(0.0, 0.0, 0.0, 1.0)

    def addShadowMap(self, i, size, scale, ambLight=None, gi=None):
        if i > 0: return
        d = ctx.depth_texture((size,size))
        a = ctx.framebuffer(depth_attachment=d)
        s = {}
        s['map'] = a
        s['tex'] = d
        s['scale'] = np.float32(scale * 2 / size)
        s['dim'] = np.int32(size)
        self.SHADOWMAP[i] = s
        
        self.drawS = ctx.program(vertex_shader=trisetupOrtho,
                                 fragment_shader=drawMin)

        self.drawS['vscale'].write(s['scale'])
        
        for n in range(len(self.VBO)):
            vbo = self.VBO[n]
            vao = ctx.vertex_array(self.drawS,
                                   [(vbo, '3f4 5x4', 'in_vert')])
            self.SVA.append(vao)
        
        L=len(self.DRAW)

        for n in range(len(self.DRAW)):
            self.DRAW[n]['SM'] = L
            self.DRAW[n]['wS'] = np.int32(s['dim'])
            self.DRAW[n]['sScale'].write(s['scale'])
            
        d.use(location=L)

    def placeShadowMap(self, i, pos, facing, ambLight=None):
        if i > 0: return
        sm = self.SHADOWMAP[i]
        sm['pos'] = pos.astype('float32')
        f = viewMat(*facing)
        f = np.array([-f[1], f[2], f[0]])
        f = np.array(f.T, order='C')
        sm['vec'] = f.astype('float32')

        for i in range(len(self.DRAW)):
            try:
                self.DRAW[i]['SPos'].write(sm['pos'])
                self.DRAW[i]['SV'].write(sm['vec'])
            except KeyError:
                pass

        self.drawS['vpos'].write(sm['pos'])
        self.drawS['vmat'].write(sm['vec'])

    def clearShadowMap(self, i):
        if i > 0: return
        a = self.SHADOWMAP[i]['map']
        a.clear()
        
    def shadowMap(self, i, whichCast, shaders, bias):
        if i > 0: return
        sm = self.SHADOWMAP[i]
        sm['map'].use()

        for n in range(len(self.SVA)):
            if n < len(whichCast) and whichCast[n]:
                sva = self.SVA[n]
                sva.render(moderngl.TRIANGLES)

        self.fbo.use()

        try:
            self.STEX.release()
        except AttributeError:
            pass
        tex = ctx.texture((sm['dim'], sm['dim']), 1,
                              np.frombuffer(sm['tex'].read(), 'float32'),
                              dtype='f4')
        self.STEX = tex
        
        L=len(self.DRAW)
        for i in range(len(self.DRAW)):
            try:
                self.DRAW[i]['SM'] = L
            except KeyError: pass
            tex.use(location=L)
        
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
        h = np.frombuffer(self.fs.read(), "uint8").reshape((self.H, self.W, 3))
        return h
