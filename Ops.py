# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Ops.py) is part of AXI Visualizer and AXI Combat.
#
# AXI Combat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# AXI Combat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AXI Combat. If not, see <https://www.gnu.org/licenses/>.
# ======== ========

import numpy as np
import time
from Utils import viewMat

import pyopencl as cl

import OpsConv

PATH = OpsConv.PATH

OpsConv.genInfo()
ctx = OpsConv.getContext()

d = ctx.devices[0]
print("Using", d.name)
cq = cl.CommandQueue(ctx)
mf = cl.mem_flags

TILE_BUF = 128
TILE_SIZE = 16

BLOCK_SIZE = TILE_BUF

def makeProgram(f, path="Shaders/"):
    global ctx
    t = open(PATH + path + f).read().replace("BLOCK_SIZE", str(BLOCK_SIZE))
    return cl.Program(ctx, t).build()

from Shaders_src.AVSL import compileAll

compileAll()

vert = makeProgram("vert.c", "Pipe/")
trisetup = makeProgram("trisetup.c", "Pipe/")
trisetupC = makeProgram("trisetup_cull.c", "Pipe/")
trisetupSky = makeProgram("trisetup_sky.c", "Pipe/")
trisetup2d = makeProgram("trisetup_2d.c", "Pipe/")
gather = makeProgram("gather.c", "Pipe/")

coarse = makeProgram("coarse.c", "Pipe/")

draw = makeProgram("drawtexcolsmp.c")
drawSh = makeProgram("drawtexcolsmshp.c")
drawSh2 = makeProgram("drawtexcolsmshp2.c")
drawMip = makeProgram("drawtexmipsh.c")
drawA = makeProgram("drawtexcolsmpalpha.c")
drawEm = makeProgram("drawemissive.c")
drawPh = makeProgram("drawphong.c")

drawFog = makeProgram("drawfog.c")

drawAdd = makeProgram("drawadd.c")
drawSub = makeProgram("drawsub.c")
drawBorder = makeProgram("drawborder.c")

drawSky = makeProgram("drawskylerp.c")

drawSSR = makeProgram("drawtexcolsmshplerp_SSR_water.c")

blur1 = makeProgram("Post/blur.c")
blur2 = makeProgram("Post/blur2.c")

wave = makeProgram("wave2.c", "VertShaders/")
skel = makeProgram("bone1.c", "VertShaders/")

sct = makeProgram("highlight.c", "VertShaders/")

trisetupOrtho = makeProgram("trisetupOrtho.c", "Pipe/")
sh = makeProgram("drawmin.c")
shA = makeProgram("drawminalpha.c")
clearzb = makeProgram("clearzb.c")
clearframe = makeProgram("clearframe.c")

gamma = makeProgram("Post/gamma.c")

particles = makeProgram("ps.c")

def makeRBuf(nbytes):
    return cl.Buffer(ctx, mf.READ_ONLY, size=nbytes)

def align34(a):
    return np.stack((a[:,0], a[:,1], a[:,2], np.zeros_like(a[:,0])), axis=1)

class CLDraw:
    def __init__(self, size_sky, max_uv, w, h, max_particles):
        self.device = d
        self.W = np.int32(w)
        self.H = np.int32(h)
        self.WC = np.int32(w // TILE_SIZE)
        self.HC = np.int32(h // TILE_SIZE)
        self.A = w*h

        i = -np.ones((self.WC, self.HC, TILE_BUF), dtype="int32")
        self.IBUF = cl.Buffer(ctx, mf.READ_WRITE, size=i.nbytes)
        cl.enqueue_copy(cq, self.IBUF, i)
        
        n = np.zeros((self.WC, self.HC), dtype="int32")
        self.NBUF = cl.Buffer(ctx, mf.READ_WRITE, size=n.nbytes)
        cl.enqueue_copy(cq, self.NBUF, n)

        rsi = np.ones((size_sky*size_sky*6,), dtype="uint16")
        
        ro = np.ones((h, w), dtype="uint16")
        db = np.full((h, w), 255, dtype="float32")
        
        self.DB = cl.Buffer(ctx, mf.READ_WRITE, size=db.nbytes)
        
        self.RSI = cl.Buffer(ctx, mf.READ_ONLY, size=rsi.nbytes)
        self.GSI = cl.Buffer(ctx, mf.READ_ONLY, size=rsi.nbytes)
        self.BSI = cl.Buffer(ctx, mf.READ_ONLY, size=rsi.nbytes)
        
        self.RO = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes)
        self.GO = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes)
        self.BO = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes)
        
        self.r2 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)
        self.g2 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)
        self.b2 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)

        self.r3 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)
        self.g3 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)
        self.b3 = cl.Buffer(ctx, mf.WRITE_ONLY, size=ro.nbytes//4)

        self.PC = makeRBuf(np.zeros((max_particles, 4), dtype="float32").nbytes)
        self.PO = makeRBuf(np.zeros((max_particles, 4), dtype="uint16").nbytes)
        self.PT = {}; self.PTsize = {}

        self.XYZ = []
        self.UV = []
        self.VN = []
        self.LI = []
        self.SP = []
        self.ZZ = []
        self.gSize = []

        self.BN = {}
        self.oldBT = {}
        self.BT = {}
        self.oldtt = {}

        self.TIA = [] # small
        self.TIB = [] # large
        self.TNA = []
        self.TNB = []
        self.TOA = []
        self.TOB = []
        
        self.TR = []
        self.TG = []
        self.TB = []
        self.TA = []
        self.texSize = []

        self.SHADOWMAP = {}
        
        self.RRR = {}
        self.GRR = {}
        self.BRR = {}
        self.reflTexSize = {}

        p = np.ones((3,), dtype="float32")
        self.VIEWPOS = cl.Buffer(ctx, mf.READ_ONLY, size=p.nbytes)
        self.VIEWMAT = cl.Buffer(ctx, mf.READ_ONLY, size=4*p.nbytes)

        self.LT = max_uv
        mn = np.ones((self.LT,), dtype="int32")
        self.AL = cl.Buffer(ctx, mf.READ_WRITE, size=mn.nbytes)

        self.hro = np.ones((h, w), dtype="uint16")
        self.hgo = np.ones((h, w), dtype="uint16")
        self.hbo = np.ones((h, w), dtype="uint16")
        self.hdb = np.ones((h, w), dtype="float32")

        self.useCompound = []

    def setScaleCull(self, s, cx, cy):
        self.sScale = np.float32(s)
        self.caX, self.caY = np.float32(cx), np.float32(cy)

    def drawPS(self, xyz, color, opacity, size):
        if xyz.shape[0] == 0: return
        vs = np.int32(xyz.shape[0]//BLOCK_SIZE + 1)
        cl.enqueue_copy(cq, self.PC, align34(xyz.astype("float32")))
        cl.enqueue_copy(cq, self.PO, align34(color.astype("uint16")))
        particles.ps(cq, (vs, 1), (BLOCK_SIZE, 1),
                     self.RO, self.GO, self.BO, self.DB,
                     self.PC, self.PO,
                     np.float32(opacity), np.int32(size),
                     self.VIEWPOS, self.VIEWMAT,
                     self.sScale, self.W, self.H,
                     self.caX, self.caY, np.int32(xyz.shape[0]),
                     g_times_l=True)

    def addBoneWeights(self, tn, bw):
        bb = bw.astype("int8")
        self.BN[tn] = makeRBuf(bb.nbytes)
        cl.enqueue_copy(cq, self.BN[tn], bb)

    def initBoneTransforms(self, name, bn):
        s = np.zeros((4,4),dtype="float32")
        self.BT[name] = makeRBuf(bn*s.nbytes)
        self.oldBT[name] = makeRBuf(bn*s.nbytes)
        self.oldtt[name] = np.tile(np.identity(4), (bn,1)).astype("float32")

    def initBoneOrigin(self, o, bn, tn):
        o = o.astype("float32")
        vs = np.int32(self.gSize[tn]//BLOCK_SIZE + 1)
        skel.offset(cq, (vs, 1), (BLOCK_SIZE, 1),
                       self.XYZ[tn], self.BN[tn],
                       np.int8(bn), o[0], o[1], o[2],
                       self.gSize[tn],
                       g_times_l=True)

    def setBoneTransform(self, name, bt):
        tt = self.invbt(bt, 1).astype("float32")
        cl.enqueue_copy(cq, self.BT[name], tt)
        cl.enqueue_copy(cq, self.oldBT[name], self.oldtt[name])
        self.oldtt[name] = self.invbt(tt)
        
    def boneTransform(self, cStart, cEnd, tn, name, offset=0):
        vs = np.int32((cEnd - cStart)//BLOCK_SIZE + 1)
        skel.transform(cq, (vs, 1), (BLOCK_SIZE, 1),
                       self.XYZ[tn], self.VN[tn],
                       self.BN[tn], self.oldBT[name], self.BT[name],
                       np.int32(cStart), np.int32(cEnd), np.int8(offset),
                       g_times_l=True)

    def invbt(self, b, tt=-1):
        for i in range(b.shape[0]//4):
            b[4*i:4*i+3,:3] = np.transpose(b[4*i:4*i+3,:3])
            b[4*i+3] *= tt
        return b

    def highlight(self, hc, tn):
        hc = np.array(hc, dtype="float32")
        vs = np.int32(self.gSize[tn]*3//BLOCK_SIZE + 1)
        sct.highlight(cq, (vs, 1), (BLOCK_SIZE, 1),
                   self.LI[tn], *hc, self.gSize[tn],
                   g_times_l=True)
        
    def getBoneWeights(self, tn):
        b = np.zeros((self.gSize[tn]//3,3), dtype="int8")
        cl.enqueue_copy(cq, b, self.BN[tn])
        return b
    
    def getVertPoints(self, tn):
        b = np.zeros((self.gSize[tn]//3,3,4), dtype="float32")
        cl.enqueue_copy(cq, b, self.XYZ[tn])
        return b
    def getVertNorms(self, tn):
        b = np.zeros((self.gSize[tn]//3,3,4), dtype="float32")
        cl.enqueue_copy(cq, b, self.VN[tn])
        return b

    def addTexture(self, r, g, b, mip=False):
        rr = r.astype("uint16")
        gg = g.astype("uint16")
        bb = b.astype("uint16")
        
        self.TR.append(makeRBuf(rr.nbytes))
        self.TG.append(makeRBuf(rr.nbytes))
        self.TB.append(makeRBuf(rr.nbytes))
        cl.enqueue_copy(cq, self.TR[-1], rr, is_blocking=False)
        cl.enqueue_copy(cq, self.TG[-1], gg, is_blocking=False)
        cl.enqueue_copy(cq, self.TB[-1], bb, is_blocking=False)
        
        if mip: self.texSize.append(np.int32(np.log2(mip)))
        else: self.texSize.append(np.int32(rr.shape[0]))
        return len(self.TR) - 1

    def addTextureGroup(self, xyz, uv, vn, r, g, b, mip=False):
        rr = r.astype("uint16")
        gg = g.astype("uint16")
        bb = b.astype("uint16")
        
        p = xyz.astype("float32")
        p = align34(p)
        
        n = vn.astype("float32")
        n = align34(n)
        
        uv = uv.astype("float32")
        
        self.XYZ.append(makeRBuf(p.nbytes))
        self.UV.append(makeRBuf(uv.nbytes))
        self.VN.append(makeRBuf(p.nbytes))
        self.LI.append(makeRBuf(uv.nbytes*2))

        self.SP.append(makeRBuf(uv.nbytes))
        self.ZZ.append(makeRBuf(uv.nbytes//2))
        self.TIA.append(makeRBuf(uv.nbytes//6))
        self.TIB.append(makeRBuf(uv.nbytes//6))
        gs = int(p.shape[0] / 3 / BLOCK_SIZE)+1
        ib = np.ones((1,),dtype="int32").nbytes
        self.TNA.append(makeRBuf(gs*ib))
        self.TNB.append(makeRBuf(gs*ib))
        self.TOA.append(makeRBuf(uv.nbytes//6))
        self.TOB.append(makeRBuf(uv.nbytes//6))
        
        self.TR.append(makeRBuf(rr.nbytes))
        self.TG.append(makeRBuf(rr.nbytes))
        self.TB.append(makeRBuf(rr.nbytes))
        
        cl.enqueue_copy(cq, self.XYZ[-1], p, is_blocking=False)
        cl.enqueue_copy(cq, self.UV[-1], uv, is_blocking=False)
        cl.enqueue_copy(cq, self.VN[-1], n, is_blocking=False)
        
        cl.enqueue_copy(cq, self.TR[-1], rr, is_blocking=False)
        cl.enqueue_copy(cq, self.TG[-1], gg, is_blocking=False)
        cl.enqueue_copy(cq, self.TB[-1], bb, is_blocking=False)
        if mip:
            self.texSize.append(np.int32(np.log2(mip)))
        else:
            self.texSize.append(np.int32(rr.shape[0]))
        self.gSize.append(np.int32(p.shape[0]))
        self.useCompound.append(False)
        
        return len(self.TR)-1

    def copyTo(self, tn, vp, vn, cstart=0):
        cl.enqueue_copy(cq, self.XYZ[tn], align34(vp.astype("float32")),
                        device_offset=cstart*3*4*4, is_blocking=False)
        cl.enqueue_copy(cq, self.VN[tn], align34(vn.astype("float32")),
                        device_offset=cstart*3*4*4)

    def addTexAlpha(self, a):
        self.TA.append(cl.Buffer(ctx, mf.READ_ONLY, size=a.nbytes))
        cl.enqueue_copy(cq, self.TA[-1], a, is_blocking=False)

    def setReflTex(self, name, r, g, b, size):
        rr = r.astype("uint16")
        self.RRR[name] = makeRBuf(rr.nbytes)
        self.GRR[name] = makeRBuf(rr.nbytes)
        self.BRR[name] = makeRBuf(rr.nbytes)
        cl.enqueue_copy(cq, self.RRR[name], rr, is_blocking=False)
        cl.enqueue_copy(cq, self.GRR[name], g.astype("uint16"), is_blocking=False)
        cl.enqueue_copy(cq, self.BRR[name], b.astype("uint16"), is_blocking=False)
        self.reflTexSize[name] = np.int32(size/2)
        return len(self.reflTexSize) - 1
    
    def setSkyTex(self, r, g, b, size):
        cl.enqueue_copy(cq, self.RSI, r.T.astype("uint16"), is_blocking=False)
        cl.enqueue_copy(cq, self.GSI, g.T.astype("uint16"), is_blocking=False)
        cl.enqueue_copy(cq, self.BSI, b.T.astype("uint16"), is_blocking=False)
        self.skyTexSize = np.int32(size)

    def setPos(self, vc):
        cl.enqueue_copy(cq, self.VIEWPOS, vc.astype("float32"))
    def setVM(self, vM):
        v = align34(vM)
        cl.enqueue_copy(cq, self.VIEWMAT, v.astype("float32"))

    def rotate(self, oldRM, rotMat, origin, cStart, cEnd, tn):
        if cEnd is None: cEnd = self.gSize[tn]
        oo = origin.astype("float32")
        o = makeRBuf(oo.nbytes)
        cl.enqueue_copy(cq, o, oo)
        rM = align34(rotMat.astype("float32").T)
        oRM = align34(oldRM.astype("float32"))
        r = makeRBuf(rM.nbytes)
        rr = makeRBuf(oRM.nbytes)
        cl.enqueue_copy(cq, r, rM)
        cl.enqueue_copy(cq, rr, oRM)
        vs = np.int32((cEnd - cStart)//BLOCK_SIZE + 1)
        vert.transform(cq, (vs, 1), (BLOCK_SIZE, 1),
                       self.XYZ[tn], self.VN[tn],
                       rr, r, o,
                       np.int32(cStart), np.int32(cEnd),
                       g_times_l=True)

    def translate(self, coords, cStart, cEnd, tn):
        if cEnd is None: cEnd = self.gSize[tn]
        oo = coords.astype("float32")
        o = makeRBuf(oo.nbytes)
        cl.enqueue_copy(cq, o, oo)
        vs = np.int32((cEnd - cStart)//BLOCK_SIZE + 1)
        vert.Ttranslate(cq, (vs, 1), (BLOCK_SIZE, 1),
                       self.XYZ[tn], o,
                       np.int32(cStart), np.int32(cEnd),
                       g_times_l=True)

    def scale(self, origin, scale, cStart, cEnd, tn):
        if cEnd is None: cEnd = self.gSize[tn]
        oo = origin.astype("float32")
        o = makeRBuf(oo.nbytes)
        cl.enqueue_copy(cq, o, oo)
        vs = np.int32((cEnd - cStart)//BLOCK_SIZE + 1)
        vert.Tscale(cq, (vs, 1), (BLOCK_SIZE, 1),
                       self.XYZ[tn], o, np.float32(scale),
                       np.int32(cStart), np.int32(cEnd),
                       g_times_l=True)

    def setupWave(self, origin, wDir, wLen, wAmp, wSpd, numW):
        self.WAVEO = [np.float32(x) for x in origin]
        self.WAVED = [np.float32(x) for x in wDir.reshape((-1,))]
        
        wl = wLen.astype("float32")
        self.WAVELEN = makeRBuf(wl.nbytes)
        cl.enqueue_copy(cq, self.WAVELEN, wl)
        wa = wAmp.astype("float32")
        self.WAVEAMP = makeRBuf(wa.nbytes)
        cl.enqueue_copy(cq, self.WAVEAMP, wa)
        ws = wSpd.astype("float32")
        self.WAVESPD = makeRBuf(ws.nbytes)
        cl.enqueue_copy(cq, self.WAVESPD, ws)
        #self.WNUM = np.int8(ws.shape[0])
        self.WNUM = [np.int8(numW), np.int8(ws.reshape((-1,)).shape[0] - numW)]

    def updateWave(self, pScale, stTime, tn):
        vs = np.int32(self.gSize[tn] // BLOCK_SIZE + 1)
        wave.wave(cq, (vs, 1), (BLOCK_SIZE, 1),
                  self.XYZ[tn], self.VN[tn],
                  *self.WAVEO, *self.WAVED, np.float32(pScale),
                  np.float32(time.time() - stTime),
                  self.WAVELEN, self.WAVEAMP,
                  self.WAVESPD, *self.WNUM, self.gSize[tn],
                  g_times_l=True)
        
    def vertLight(self, mask, dirI, dirD, pointI=None, pointP=None,
                  spotI=None, spotD=None, spotP=None):
        i = dirI.astype("float32")
        i = align34(i)
        d = dirD.astype("float32")
        d = align34(d)
        self.dirInt = makeRBuf(i.nbytes)
        self.dirDir = makeRBuf(d.nbytes)
        cl.enqueue_copy(cq, self.dirInt, i)
        cl.enqueue_copy(cq, self.dirDir, d)
        self.numDirs = np.int8(dirI.shape[0])

        if pointI is None:
            pass
        elif pointI is 1:
            self.pointInt = makeRBuf(4)
            self.pointPos = makeRBuf(4)
            self.numPoints = np.int16(0)
        else:
            i = pointI.astype("float32")
            i = align34(i)
            d = pointP.astype("float32")
            d = align34(d)
            self.pointInt = makeRBuf(i.nbytes)
            self.pointPos = makeRBuf(d.nbytes)
            cl.enqueue_copy(cq, self.pointInt, i)
            cl.enqueue_copy(cq, self.pointPos, d)
            self.numPoints = np.int16(pointI.shape[0])
        if spotI is None:
            pass
        elif spotI is 1:
            self.spotInt = makeRBuf(4)
            self.spotDir = makeRBuf(4)
            self.spotPos = makeRBuf(4)
            self.numSpots = np.int32(0)
        else:
            i = spotI.astype("float32")
            i = align34(i)
            d = spotD.astype("float32")
            d = align34(d)
            p = spotP.astype("float32")
            p = align34(p)
            self.spotInt = makeRBuf(i.nbytes)
            self.spotDir = makeRBuf(d.nbytes)
            self.spotPos = makeRBuf(p.nbytes)
            cl.enqueue_copy(cq, self.spotInt, i)
            cl.enqueue_copy(cq, self.spotDir, d)
            cl.enqueue_copy(cq, self.spotPos, p)
            self.numSpots = np.int32(spotI.shape[0])
        
        for tn in range(len(self.gSize)):
            if mask[tn]:
                vs = np.int32(self.gSize[tn]//BLOCK_SIZE + 1)
                vert.vertL(cq, (vs, 1), (BLOCK_SIZE, 1),
                           self.XYZ[tn], self.VN[tn], self.LI[tn],
                           self.dirInt, self.dirDir,
                           self.pointInt, self.pointPos,
                           self.spotInt, self.spotDir, self.spotPos,
                           self.ambLight,
                           self.numDirs, self.numPoints, self.numSpots,
                           self.gSize[tn], g_times_l=True)

    def setHostSkyTex(self, tex):
        self.hostSTex = tex.astype("uint16")
        self.stSize = tex.shape[0]
    
    def drawAll(self, shaders,
                mask=None, shadowIds=[0,1],
                useOpacitySM=False):
        
        availShaders = "alpha shadow mip refl sky ortho cull"

        if mask is None:
            mask = [False] * len(shaders)
        gsn = []
        
        #a = time.time()
        sm = self.SHADOWMAP[0]
        sm1 = self.SHADOWMAP[1]

        for tn in range(len(self.gSize)):
            if mask[tn]:
                gsn.append(0)
                continue
            gs = np.int32(int(self.gSize[tn] / 3 / BLOCK_SIZE)+1)
            gsn.append(gs)
            if "cull" in shaders[tn]: ts = trisetupC
            elif "sky" in shaders[tn]: ts = trisetupSky
            elif "2d" in shaders[tn]: ts = trisetup2d
            else: ts = trisetup
            ts.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                     self.XYZ[tn], self.VN[tn],
                     self.TIA[tn], self.TIB[tn],
                     self.TNA[tn], self.TNB[tn],
                     self.SP[tn], self.ZZ[tn],
                     self.VIEWPOS, self.VIEWMAT,
                     self.sScale, self.W, self.H,
                     self.caX, self.caY, np.int32(self.gSize[tn]//3),
                     g_times_l=True)

        # Small
        for tn in range(len(self.gSize)):
            if mask[tn]: continue
            gs = gsn[tn]
            gather.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                         self.TIA[tn], self.TNA[tn],
                         self.TOA[tn], self.AL, np.int32(tn),
                         gs, g_times_l=True)

        newSize = np.zeros((self.LT,), dtype="int32")
        cl.enqueue_copy(cq, newSize, self.AL, is_blocking=True)
        nsn = newSize // BLOCK_SIZE + 1

        #print("Small", newSize)
        nAfter = {}
        newSizeAfter = {}

        for tn in range(len(self.gSize)):
            if mask[tn]: continue
            ns = nsn[tn]
            if newSize[tn] > 0:
                if "alpha" in shaders[tn]:
                    drawA.drawSmall(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                               self.TA[shaders[tn]["alpha"]],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H, np.int32(newSize[tn]),
                             g_times_l=True)
                elif "mip" in shaders[tn]:
                    drawMip.drawSmall(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             np.float32(shaders[tn]["mip"]),
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H, np.int32(newSize[tn]),
                             g_times_l=True)
                elif "emissive" in shaders[tn]:
                    drawEm.drawSmall(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["emissive"]),
                             self.UV[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.W, self.H, np.int32(newSize[tn]),
                             g_times_l=True)
                elif any([x in shaders[tn] for x in ["SSR", "add", "sub", "border"]]):
                    nAfter[tn] = ns; newSizeAfter[tn] = newSize[tn]
                elif "phong" in shaders[tn]:
                    drawPh.drawSmall(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.VIEWPOS, self.VIEWMAT,
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             self.W, self.H, np.int32(newSize[tn]),
                             g_times_l=True)
                else:
                    drawSh2.drawSmall(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H, np.int32(newSize[tn]),
                             g_times_l=True)


        # Large
        for tn in range(len(self.gSize)):
            if mask[tn]: continue
            gs = gsn[tn]
            gather.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                         self.TIB[tn], self.TNB[tn],
                         self.TOB[tn], self.AL, np.int32(tn),
                         gs, g_times_l=True)

        newSize = np.zeros((self.LT,), dtype="int32")
        cl.enqueue_copy(cq, newSize, self.AL, is_blocking=True)
        nsn = newSize // BLOCK_SIZE + 1
        
        #print("Large", newSize)
        
        for tn in range(len(self.gSize)):
            if mask[tn]: continue
            ns = nsn[tn]
            if newSize[tn] > 0:
                
                #a = time.perf_counter()
                coarse.draw(cq, (ns, 1), (BLOCK_SIZE, 1),
                            self.TOB[tn],
                            self.IBUF, self.NBUF, self.SP[tn],
                            self.WC, self.HC, np.int32(newSize[tn]),
                            g_times_l=True).wait()

                #print("Coarse:", time.perf_counter()-a)
                #a = time.perf_counter()
                if "alpha" in shaders[tn]:
                    drawA.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.TA[shaders[tn]["alpha"]],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H,
                             g_times_l=True)
                elif "mip" in shaders[tn]:
                    drawMip.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             np.float32(shaders[tn]["mip"]),
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H,
                             g_times_l=True)
                elif "SSR" in shaders[tn]:
                    sr = shaders[tn]["SSR"]
                    drawSSR.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                                self.VIEWPOS, self.VIEWMAT, self.sScale,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.RRR[sr], self.GRR[sr], self.BRR[sr],
                             self.reflTexSize[sr],
                             self.W, self.H,
                             g_times_l=True)
                elif "sky" in shaders[tn]:
                    drawSky.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn],
                             self.RSI, self.GSI, self.BSI, self.skyTexSize,
                             self.W, self.H,
                             g_times_l=True)
                elif "emissive" in shaders[tn]:
                    drawEm.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["emissive"]),
                             self.UV[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.W, self.H,
                             g_times_l=True)
                elif "add" in shaders[tn]:
                    drawAdd.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["add"]),
                             self.UV[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.W, self.H,
                             g_times_l=True)
                elif "sub" in shaders[tn]:
                    drawSub.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["sub"]),                             self.W, self.H,
                             g_times_l=True)
                elif "border" in shaders[tn]:
                    drawBorder.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["border"]),
                             self.VIEWPOS, self.VIEWMAT,
                             self.UV[tn], self.XYZ[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.W, self.H,
                             g_times_l=True)
                
                elif "fog" in shaders[tn]:
                    drawFog.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.VIEWPOS, self.VIEWMAT, self.sScale,
                             self.LInt, self.LDir,
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             self.W, self.H,
                             g_times_l=True)
                elif "phong" in shaders[tn]:
                    drawPh.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.VIEWPOS, self.VIEWMAT,
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             self.W, self.H,
                             g_times_l=True)
                else:
                    drawSh2.draw(cq, (self.WC * self.HC, 1), (BLOCK_SIZE, 1),
                             self.IBUF, self.NBUF,
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                             self.LInt, self.LDir,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             sm["map"], sm["dim2"], sm["scale"],
                             sm["vec"], sm["pos"],
                             sm1["map"], sm1["dim2"], sm1["scale"],
                             sm1["vec"], sm1["pos"],
                             self.W, self.H,
                             g_times_l=True)

                #print("Fine:", time.perf_counter()-a)
        
        
        for tn in range(len(self.gSize)):
            if mask[tn]: continue
            if (tn in newSizeAfter) and (newSizeAfter[tn] > 0):
                if "SSR" in shaders[tn]:
                    sr = shaders[tn]["SSR"]
                    drawSSR.drawSmall(cq, (nAfter[tn], 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.LI[tn], self.VN[tn], self.XYZ[tn],
                                self.VIEWPOS, self.VIEWMAT, self.sScale,
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.RRR[sr], self.GRR[sr], self.BRR[sr],
                             self.reflTexSize[sr],
                             self.W, self.H, np.int32(newSizeAfter[tn]),
                             g_times_l=True)
                elif "add" in shaders[tn]:
                    drawAdd.drawSmall(cq, (nAfter[tn], 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["add"]),
                             self.UV[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.texSize[tn],
                             self.W, self.H, np.int32(newSizeAfter[tn]),
                             g_times_l=True)
                elif "sub" in shaders[tn]:
                    drawSub.drawSmall(cq, (nAfter[tn], 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             self.RO, self.GO, self.BO,
                             self.DB, self.SP[tn], self.ZZ[tn],
                             np.float32(shaders[tn]["sub"]),
                             self.W, self.H, np.int32(newSizeAfter[tn]),
                             g_times_l=True)

        #print("Pixel:", time.time()-a)
        #a = time.time()
        
    def clearZBuffer(self):
        s = 4; t = 4
        clearframe.clearFrame(cq, (s, s), (t, t), self.DB,
                           self.W, self.H,
                           np.int32(t), np.int32(s*t), g_times_l=True)
    def gamma(self, ex):
        s = 4; t = 4
        gamma.g(cq, (s, s), (t, t), self.RO, self.GO, self.BO,
                np.float32(ex),
                self.W, self.H, np.int32(t), np.int32(s*t),
                np.int32(np.ceil(self.H/(s*t))), g_times_l=True)

    def blur(self):
        s = 4; t = 4
        e = blur1.blurH(cq, (s, s), (t, t), self.RO, self.GO, self.BO,
                    self.r2, self.g2, self.b2,
                    self.r3, self.g3, self.b3,
                    self.W, self.H, np.int32(t), np.int32(s*t),
                    np.float32(np.ceil(self.H/(s*t))), g_times_l=True)
        blur2.blurV(cq, (s, s), (t, t), self.r2, self.g2, self.b2,
                    self.r3, self.g3, self.b3,
                    self.RO, self.GO, self.BO,
                    self.W, self.H, np.int32(t), np.int32(s*t),
                    np.float32(np.ceil(self.H/(s*t))), g_times_l=True,
                    wait_for=[e])
    
    def clearShadowMap(self, i):
        sm = self.SHADOWMAP[i]
        s = 4; t = 4
        clearzb.clearFrame(cq, (s, s), (t, t), sm["map"],
                           sm["dim"], sm["dim"],
                           np.int32(t), np.int32(s*t), g_times_l=True)

    def addShadowMap(self, i, size, scale, ambLight=None, useGI=False):
        a = np.full((size, size), 256*256-1, dtype="float32")
        b = np.ones((3, 4), dtype="float32")
        s = {}
        s["map"] = cl.Buffer(ctx, mf.READ_WRITE, size=a.nbytes)
        s["vec"] = cl.Buffer(ctx, mf.READ_ONLY, size=b.nbytes)

        p = np.ones((3,), dtype="float32")
        s["pos"] = cl.Buffer(ctx, mf.READ_ONLY, size=p.nbytes)
        
        s["dim"] = np.int32(size)
        s["dim2"] = np.int32(size/2)
        s["scale"] = np.float32(scale)

        if ambLight is not None:
            self.ambLight = np.float32(ambLight)

        if useGI:
            s["normbuf"] = cl.Buffer(ctx, mf.WRITE_ONLY, size=a.nbytes*4)
            s["Ro"] = cl.Buffer(ctx, mf.WRITE_ONLY, size=a.nbytes//2)
            s["Go"] = cl.Buffer(ctx, mf.WRITE_ONLY, size=a.nbytes//2)
            s["Bo"] = cl.Buffer(ctx, mf.WRITE_ONLY, size=a.nbytes//2)

        self.SHADOWMAP[i] = s

    def placeShadowMap(self, i, pos, facing, ambLight=None):
        sm = self.SHADOWMAP[i]
        p = np.array(pos).astype("float32")
        cl.enqueue_copy(cq, sm["pos"], p)
        f = viewMat(*facing)
        f = align34(f)
        cl.enqueue_copy(cq, sm["vec"], f.astype("float32"))
        sm["vecnp"] = f
        if ambLight is not None:
            self.ambLight = np.float32(ambLight)
    
    def shadowMap(self, i, whichCast, shaders, bias):
        shBias = np.float32(bias)
        tsn = []
        gsn = []
        sm = self.SHADOWMAP[i]
        for tn in range(len(self.gSize)):
            if whichCast[tn]:
                tsn.append(tn)
                gs = np.int32(int(self.gSize[tn] / 3 / BLOCK_SIZE)+1)
                gsn.append(gs)
                trisetupOrtho.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                               self.XYZ[tn], self.TIA[tn], self.TNA[tn],
                               self.SP[tn], self.ZZ[tn],
                               sm["pos"], sm["vec"],
                               shBias,
                               sm["scale"],
                               sm["dim"], sm["dim"],
                               self.caX, self.caY, np.int32(self.gSize[tn]//3),
                               g_times_l=True)

        for i in range(len(tsn)):
            gs = gsn[i]
            tn = tsn[i]
            gather.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                         self.TIA[tn], self.TNA[tn],
                         self.TOA[tn], self.AL, np.int32(tn),
                         gs, g_times_l=True)
        
        newSize = np.zeros((self.LT,), dtype="int32")
        cl.enqueue_copy(cq, newSize, self.AL, is_blocking=True)
        nsn = newSize // BLOCK_SIZE + 1

        #print(nsn, "\n", newSize)
        for i in range(len(tsn)):
            tn = tsn[i]
            ns = nsn[tn]
            #print("ns:", ns, "tn:", tn, "newsize[tn]:", newSize[tn])
            if (newSize[tn] > 0):
                if not "alpha" in shaders[tn]:
                    sh.draw(cq, (ns, 1), (BLOCK_SIZE, 1),
                            self.TOA[tn],
                            sm["map"], self.SP[tn], self.ZZ[tn],
                            sm["dim"], sm["dim"], np.int32(newSize[tn]),
                            g_times_l=True)
                else:
                    aindex = shaders[tn]["alpha"]
                    shA.draw(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TOA[tn],
                             sm["map"], self.SP[tn], self.ZZ[tn],
                             self.UV[tn],
                             self.TA[aindex], self.texSize[tn],
                             sm["dim"], sm["dim"], np.int32(newSize[tn]),
                             g_times_l=True)

            cq.flush()

    def setPrimaryLight(self, dirI, dirD):
        i = dirI.astype("float32")
        i = align34(i)
        d = dirD.astype("float32")
        d = align34(d)
        self.LInt = makeRBuf(i.nbytes)
        self.LDir = makeRBuf(d.nbytes)
        cl.enqueue_copy(cq, self.LInt, i)
        cl.enqueue_copy(cq, self.LDir, d)

    def drawDirectional(self, i, whichCast, useAlpha=[1], shBias=np.float32(0.1)):
        tsn = []
        gsn = []
        sm = self.SHADOWMAP[i]
        for tn in range(len(self.gSize)):
            if whichCast[tn]:
                tsn.append(tn)
                gs = np.int32(int(self.gSize[tn] / 3 / BLOCK_SIZE)+1)
                gsn.append(gs)
                trisetupOrtho.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                               self.XYZ[tn], self.TI[tn], self.TN[tn],
                               self.SP[tn], self.ZZ[tn],
                               sm["pos"], sm["vec"],
                               shBias,
                               sm["scale"],
                               sm["dim"], sm["dim"],
                               self.caX, self.caY, np.int32(self.gSize[tn]//3),
                               g_times_l=True)

        for i in range(len(tsn)):
            gs = gsn[i]
            tn = tsn[i]
            gather.setup(cq, (gs, 1), (BLOCK_SIZE, 1),
                         self.TI[tn], self.TN[tn],
                         self.TO[tn], self.AL, np.int32(tn),
                         gs, g_times_l=True)
        
        newSize = np.zeros((self.LT,), dtype="int32")
        cl.enqueue_copy(cq, newSize, self.AL, is_blocking=True)
        nsn = newSize // BLOCK_SIZE + 1

        for i in range(len(tsn)):
            tn = tsn[i]
            ns = nsn[tn]
            if newSize[tn] > 0:
                if not useAlpha[tn]:
                    drawNorm.draw(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TO[tn],
                             sm["Ro"], sm["Go"], sm["Bo"],
                             sm["normbuf"],
                             sm["map"], self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.VN[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             sm["dim"], sm["dim"], np.int32(newSize[tn]),
                             self.texSize[tn], g_times_l=True)
                else:
                    drawNormA.draw(cq, (ns, 1), (BLOCK_SIZE, 1),
                             self.TO[tn],
                             sm["Ro"], sm["Go"], sm["Bo"],
                             sm["normbuf"],
                             sm["map"], self.SP[tn], self.ZZ[tn],
                             self.UV[tn], self.VN[tn],
                             self.TR[tn], self.TG[tn], self.TB[tn],
                             self.TA[1],#self.TA[useAlpha[tn] - 1],
                             sm["dim"], sm["dim"], np.int32(newSize[tn]),
                             self.texSize[tn], g_times_l=True)

    def getGIM(self, i):
        sm = self.SHADOWMAP[i]
        size = sm["dim"]
        hr = np.zeros((size,size), dtype="uint16")
        hg = np.zeros((size,size), dtype="uint16")
        hb = np.zeros((size,size), dtype="uint16")
        hz = np.zeros((size,size), dtype="float32")
        hn = np.zeros((size,size,4), dtype="float32")
        cq.flush()
        cl.enqueue_copy(cq, hr, sm["Ro"])
        cl.enqueue_copy(cq, hg, sm["Go"])
        cl.enqueue_copy(cq, hb, sm["Bo"])
        cl.enqueue_copy(cq, hz, sm["map"])
        cl.enqueue_copy(cq, hn, sm["normbuf"])
        
        out = [np.stack((hr,hg,hb),axis=2), hz, hn]
        return out
        
    def getSHM(self, i):
        sm = self.SHADOWMAP[i]
        s = np.empty((sm["dim"], sm["dim"]), dtype="float32")
        cl.enqueue_copy(cq, s, sm["map"])
        return s

    def getFrame(self):
        cl.enqueue_copy(cq, self.hro, self.RO, is_blocking=False)
        cl.enqueue_copy(cq, self.hgo, self.GO, is_blocking=False)
        cl.enqueue_copy(cq, self.hbo, self.BO, is_blocking=False)
        cl.enqueue_copy(cq, self.hdb, self.DB)
        
        
        return (self.hro, self.hgo, self.hbo, self.hdb)
