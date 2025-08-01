# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Compute.py) is part of AXI Visualizer and AXI Combat.
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

import multiprocessing as mp
from queue import Empty, Full
thisprocess = mp.current_process().name

from math import sin, cos, pi, ceil, atan2
import numpy as np
import time
from Utils import *

import Visualizer as VS

from TexObjects import TexSkyBox
from Cubemap import CubeMap
from VertObjects import VertSphere, VertModel, VertTerrain, VertTerrain0, VertPlane, VertWater

from ParticleSystem import ContinuousParticleSystem
import sys, os
from PIL import Image
import json

import ctypes

os.system('color')

DO_PROFILE = False

if DO_PROFILE and (thisprocess == 'MainProcess'):
    print('\033[46m Profiling! \033[0m')
    from profilehooks import profile
else:
    def profile(**kwargs):
        return lambda f: f

if getattr(sys, "frozen", False): PATH = os.path.dirname(sys.executable) + "/"
else: PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

def getTexture(fn, cgamma=True, texMul=1):
    ti = Image.open(fn).convert("RGB")
    if ti.size[0] != ti.size[1]:
        print("Texture is not square")
        n = max(ti.size)
        ti = ti.resize((n,n))
    if (ti.size[0] & (ti.size[0] - 1)) != 0:
        print("Texture is not a power of 2, resizing up.")
        n = 2**ceil(log2(ti.size[0]))
        ti = ti.resize((n,n))
    ta = np.array(ti.rotate(-90)).astype('float32')
    if cgamma:  ta *= ta; ta /= 8.
    else:       ta *= 64
    ta *= texMul

    return np.array(ta/65535, order='C', dtype='float16')


class ThreeDBackend:
    def __init__(self, width, height,
                 scale=600, fovx=None,
                 downSample=1, record=None):

        pipe = rec = mp.Queue(1)

        self.evtQ = mp.Queue(64)
        self.infQ = mp.Queue(16)

        self.P = pipe
        self.recP = rec
        self.handles = {}
        self.full = 0
        self.empty = 0

        self.W = width
        self.H = height
        self.downSample = downSample

        self.α = 0
        self.β = 0

        self.estWedges = 0
        self.actWedges = 0
        self.vertObjects = []

        self.vtNames = {}
        self.vertpoints = []
        self.vertnorms = []
        self.vertu = []
        self.vertv = []
        self.vtextures = []

        self.instanceData = {}

        self.renderMask = None

        self.vertBones = []

        self.texAlphas = []
        self.vaNames = {}

        self.matShaders = {}

        self.skyTex = None
        self.skyHemiLight = [0.1,0.2,0.4]

        self.useOpSM = False

        self.uInfo = None
        self.recVideo = False

        self.particleSystems = []

        self.W2 = int(self.W/2)
        self.H2 = int(self.H/2)

        self.pos = np.array([0., 0., 0.])
        self.vc = self.viewCoords()

        self.camSpeed = 0.3
        self.speed = np.array([0., 0., 0.])
        self.svert = 0
        self.shorz = 0
        self.mouseSensitivity = 20

        self.setFOV(fovx, scale)

        self.directionalLights = []

        self.pointLights = []
        self.spotLights = []
        self.shadowCams = []
        self.ambLight = 0.2

        self.drawAxes = True
        self.axPoints = np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],
                                 dtype="float")*0.25
        self.baseAxPoints = np.array(self.axPoints)

        self.maxFPS = 66

        self.VRMode = False

        self.selecting = False
        self.genNewBones = False

        if not os.path.isdir(PATH + "Screenshots"):
            os.mkdir(PATH + "Screenshots")

        self.record = record
        self.batchKB = None

        bargs = (self.recP, self.evtQ, self.infQ,
                 self.W, self.H, self.mouseSensitivity,
                 self.downSample, self.recVideo)
        self.frontend = mp.Process(target=VS.runGUI, args=bargs, name="UI")

        self.frontend.start()


    def loadTexture(self, tex: str, cgamma: bool, texMul: float):
        if self.texLoadManager:
            return self.texLoadManager.loadTex(len(self.vtextures),
                                               tex, cgamma, texMul)
        return getTexture(tex, cgamma, texMul)

    def enableDOF(self, dofR=24, rad=0.2, di=4):
        pass

    def dofScreenshot(self):
        pass

    def setFOV(self, fovx, scale=None):
        if fovx is not None:
            self.scale = self.W/self.H / np.tan(fovx*pi/360)
        else:
            self.scale = scale
        self.fovX = np.arctan(self.W2 / (self.scale*self.H/2)) * 360/pi
        self.cullAngle = self.scale / np.sqrt(self.scale**2 + self.W2**2 + self.H2**2) * 0.85
        self.cullAngleX = self.W2 / self.scale + 2
        self.cullAngleY = self.H2 / self.scale + 2
        try:
            self.draw.setScaleCull(self.scale, self.cullAngleX, self.cullAngleY)
        except AttributeError: pass

    def setWH(self, w, h):
        self.W = w
        self.H = h
        self.W2 = w//2
        self.H2 = h//2
        self.setFOV(self.fovX, self.scale)

    @profile(stdout=open('profile/start.txt', 'w'), filename='profile/start.pstats')
    def start(self):
        self.loadStart = time.time()

        if mp.cpu_count() >= 4:
            self.texLoadManager = TexLoadManager(getTexture, 2)
        else:
            self.texLoadManager = None

        self.createObjects()

        self.vertPoints = []
        self.vertNorms = []
        self.vertU = []
        self.vertV = []
        for _ in range(len(self.vertpoints)):
            self.vertPoints.append(np.concatenate(self.vertpoints[0]))
            self.vertNorms.append(np.concatenate(self.vertnorms[0]))
            self.vertU.append(np.concatenate(self.vertu[0]))
            self.vertV.append(np.concatenate(self.vertv[0]))
            del self.vertpoints[0], self.vertnorms[0], self.vertu[0], self.vertv[0]
        self.vertLight = [np.ones((i.shape[0], 3)) for i in self.vertPoints]


        import OpsConv
        settings = OpsConv.getSettings(False)

        GL = settings["Render"] == "GL"
        self.GL = GL

        if GL:
            import Ops_GL as Ops
        else:
            import Ops_CL as Ops

        self.draw = Ops.CLDraw(self.W, self.H, ires=settings['IRES'], use_fsr=1)

        self.draw.setScaleCull(self.scale, self.cullAngleX, self.cullAngleY)

        if self.texLoadManager is not None:
            self.texLoadManager.collectTex(self.vtextures)
            self.texLoadManager.cleanup()

        for i in range(len(self.vtextures)):
            inst = None
            if i in self.instanceData:
                inst = self.instanceData[i]

            tex = self.vtextures[i]
            self.draw.addTextureGroup(
                self.vertPoints[i].reshape((-1,3)),
                np.stack((self.vertU[i], self.vertV[i]), axis=2).reshape((-1,3,2)),
                self.vertNorms[i].reshape((-1,3)),
                tex, shader=self.matShaders[i],
                instances=inst)
            self.vtextures[i] = np.array([1])

        for f in self.matShaders:
            mat = self.matShaders[f]
            if 'alpha' not in mat: continue
            tex = self.texAlphas[mat['alpha']]
            self.draw.addTexAlpha(tex, name=mat['alpha'],
                                  mipLvl=mat['alphaMip'] if 'alphaMip' in mat else 8)

        del self.texAlphas

        if self.genNewBones:
            self.vertBones = []
            for i in self.vertLight:
                self.vertBones.append(np.zeros((i.shape[0], 3), dtype="int"))

        for i in range(len(self.vertBones)):
            if 'genBone' in self.matShaders[i]:
                self.vertBones[i] = np.ones((self.vertLight[i].shape[0], 3),
                                            dtype="int") * self.matShaders[i]['genBone']
            if len(self.vertBones[i]) > 0:
                self.draw.addBoneWeights(i, self.vertBones[i])

        d = self.directionalLights[0]
        self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

        self.startBatchKB()
        self.customizeFrontend()
        self.endBatchKB()

        self.vMat = np.stack((self.viewVec(),self.vVhorz(),self.vVvert()))

        print('GL loaded in', time.time() - self.loadStart)

    def updateRig(self, rig, ct, name, vobj, offset=0):
        bt = rig.b0.getTransform()
        self.draw.setBoneTransform(name, bt)
        for i in ct:
            self.draw.boneTransform(vobj.cStart*3, vobj.cEnd*3, i, name, offset)
            vobj = vobj.nextMtl

    def stepParticles(self):
        for ps in self.particleSystems: ps.step()
    def resetParticles(self):
        for ps in self.particleSystems: ps.reset()

    def createObjects(self):
        pass

    def makeObjects(self, v=0):
        print("Loading objects...")
        self.actWedges = 0
        for o in self.vertObjects:
            o.created()
            self.actWedges += o.numWedges
            try:
                self.evtQ.put_nowait(int(100 * self.actWedges / self.estWedges))
            except Full:
                pass

        self.evtQ.put("Ready")

        print("\nComplete")

    def addVertObject(self, objClass, *args, **kwargs):
        thing = objClass(self, *args, **kwargs)
        self.estWedges += thing.estWedges
        self.vertObjects.append(thing)
        return True
    def makeSkybox(self, objClass, *args, **kwargs):
        thing = objClass(self, *args, **kwargs)
        thing.created()
        return thing
    def addParticleSystem(self, ps, isCloud=False):
        ps.setup()
        self.particleSystems.append(ps)

    def addNrmMap(self, tex, name, **kwargs):
        nrm = np.array(Image.open(tex).rotate(-90))
        if nrm.shape[2] == 4:
            nrm = np.array(nrm[:,:,:3])

        self.draw.addNrmMap(nrm, name, **kwargs)

    def startRender(self):

        self.vc = self.viewCoords()
        if not self.VRMode:
            self.vMat = np.stack((self.vv,self.vVhorz(),self.vVvert()))

        if self.frameNum > 0:
            self.draw.setPos(self.vc)
            self.draw.setVM(self.vMat)

        self.draw.clearZBuffer()

        s = [0,1]
        self.draw.drawAll(self.matShaders,
                          mask=self.renderMask,
                          shadowIds=s,
                          useOpacitySM=self.useOpSM,
                          stage=self.stage)

        cc = []
        for ps in self.particleSystems:
            if not ps.started: continue
            dist = np.linalg.norm(ps.pos - self.pos)
            cc.append((ps, dist))

        cc = sorted(cc, key=lambda a: a[1], reverse=True)

        for i in range(len(cc)):
            ps = cc[i][0]
            try: shader = ps.shader
            except AttributeError: shader=1
            self.draw.drawPS(ps.pc, ps.color, ps.opacity, ps.size, ps.tex,
                             shader)


    def finishRender(self):
        self.postProcess()

        result = self.draw.getFrame()
        if self.VRMode and self.GL:
            self.rgb = np.array(result)[::-1]
        else:
            self.rgb = result

        self.debugOverlay()

        if self.VRMode:
            if self.GL:
                try: _ = self.VRtex
                except:
                    print('Setup VR')
                    import openvr
                    self.VRtex = openvr.Texture_t()
                    self.VRtex.handle = int(self.draw.FB_GL)
                    self.VRtex.eType = openvr.TextureType_OpenGL
                    self.VRtex.eColorSpace = openvr.ColorSpace_Gamma

                self.cmp.submit(openvr.Eye_Left, self.VRtex)
                self.cmp.submit(openvr.Eye_Right, self.VRtex)
            else:
                rgba = np.array(Image.fromarray(self.rgb.astype("uint8")).convert("RGBA"))
                ibuf = ctypes.create_string_buffer(rgba.tobytes())

                b = (self.vrBuf1, self.vrBuf2)[self.frameNum % 2]
                self.ov.showOverlay(b)
                b2 = (self.vrBuf1, self.vrBuf2)[(self.frameNum+1) % 2]
                self.ov.hideOverlay(b2)
                self.ov.setOverlayRaw(b2, ibuf, self.W, self.H, 4)


        return [self.rgb, None, self.selecting, (self.pos, self.vv), self.uInfo]

    def simpleShaderVert(self, mask=None, updateLights=True):
        if mask is None:
            mask = [True] * len(self.vertU)
        dirI = np.array([d["i"] for d in self.directionalLights])
        dirD = np.array([viewVec(*d["dir"]) for d in self.directionalLights])

        if updateLights:
            if len(self.pointLights) == 0:
                pointI = 1
            else:
                pointI = np.array([p["i"] for p in self.pointLights])
            pointP = np.array([p["pos"] for p in self.pointLights])

            if len(self.spotLights) == 0:
                spotI = 1
            else:
                spotI = np.array([p["i"] for p in self.spotLights])
            spotD = np.array([p["vec"] for p in self.spotLights])
            spotP = np.array([p["pos"] for p in self.spotLights])

            self.draw.vertLight(mask, dirI, dirD, pointI, pointP,
                                spotI, spotD, spotP)
        else:
            self.draw.vertLight(mask, dirI, dirD)

    def shadowObjects(self):
        sobj = np.full((len(self.vertU),), False)
        for o in self.vertObjects:
            if o.castShadow:
                sobj[o.texNum] = True

        self.castObjs = sobj

    def setupShadowCams(self):
        for i in range(len(self.shadowCams)):
            s = self.shadowCams[i]
            g = "gi" in s
            self.draw.addShadowMap(i, s["size"], s["scale"],
                                   self.ambLight, g)

    def updateShadowCam(self, i, **kwargs):
        s = self.shadowCams[i]
        self.draw.placeShadowMap(i, s["pos"], s["dir"], self.ambLight, **kwargs)

    def shadowMap(self, i, castObjs=None, bias=0.2):
        if castObjs is None:
            castObjs = self.castObjs

        sc = self.shadowCams[i]

        self.draw.clearShadowMap(i)
        self.draw.shadowMap(i, castObjs, self.matShaders, bias)

    def viewCoords(self):
        return self.pos

    def viewVec(self):
        v = np.array([sin(self.α) * cos(self.β),
                      -sin(self.β),
                      cos(self.α) * cos(self.β)])
        return v
    def vVvert(self):
        b2 = self.β - pi/2
        v = np.array([sin(self.α) * cos(b2),
                      -sin(b2),
                      cos(self.α) * cos(b2)])
        return -v
    def vVhorz(self):
        a2 = self.α + pi/2
        v = np.array([sin(a2), 0, cos(a2)])
        return -v

    def doEvent(self, action):
        self.α += action[1]
        self.β += action[2]

    def moveKey(self, key):
        if key == "u":   self.svert = 1
        elif key == "d": self.svert = -1
        elif key == "r": self.shorz = 1
        elif key == "l": self.shorz = -1
        elif key == "ZV": self.svert = 0
        elif key == "ZH": self.shorz = 0

    def pan(self, d):
        dx = d[0]
        dy = d[1]
        self.pos += np.array([
            -(dx * cos(self.α) - dy * sin(self.β) * sin(self.α)),
            dy * cos(self.β),
            dx * sin(self.α) + dy * sin(self.β) * cos(self.α)])

    @profile(stdout=open('profile/render.txt', 'w'), filename='profile/render.pstats')
    def renderMethod(self):
        self.startRender()

        while not self.evtQ.empty():
            self.processEvent()

        self.vv = self.viewVec()

        self.frameUpdate()

        r = self.finishRender()
        data = ("render", np.array(r, dtype="object"))
        try:
            self.P.put_nowait(data)
        except Full:
            self.full += 1

    def runBackend(self):
        self.doQuit = False
        self.pendingShader = True
        frontReady = False

        print("waiting for frontend", end="")
        while (not frontReady):
            try:
                if self.evtQ.get(True, 1) == ["ready"]:
                    frontReady = True
            except Empty:
                print(".", end="")
        print("\nstarting render")

        self.startTime = time.perf_counter()
        self.frameNum = 0
        self.totTime = 0

        self.onStart()
        self.vv = self.viewVec()

        while (not self.doQuit):
            self.renderMethod()

            if DO_PROFILE and (self.frameNum > 100):
                self.doQuit = True
                self.proceed = False

            self.frameNum += 1
            dt = time.perf_counter() - self.startTime
            if dt < (1/self.maxFPS):
                time.sleep((1/self.maxFPS) - dt)
            dt = time.perf_counter() - self.startTime
            self.totTime += dt
            self.startTime = time.perf_counter()

        try:
            self.P.put(None, True, 1)
        except (Full, BrokenPipeError):
            pass

    def lookAt(self, target):
        d = target - self.pos
        self.α = pi/2-atan2(*(d[2::-2]))
        self.β = -atan2(d[1], sqrt(d[0]**2 + d[2]**2))

    def processEvent(self):
        try:
            action = self.evtQ.get_nowait()
        except Empty:
            self.empty += 1
        else:
            if action is None:
                self.doQuit = True
            elif action[0] == "event":
                self.doEvent(action)
            elif action[0] == "eventk":
                self.moveKey(action[1])
            elif action in self.handles:
                self.handles[action]()

    def finish(self):
        try:
            for x in self.draw.VBO:
                x.release()
            for x in self.draw.VAO:
                x.release()
            for x in self.draw.TEX:
                x.release()
            for x in self.draw.DRAW:
                x.release()
            self.draw.FB.release()
            self.draw.DB.release()
            self.draw.fs.release()
            self.draw.fbo.release()
            del self.draw
        except AttributeError: pass

        try:
            self.P.put(None, True, 0.5)
        except: pass
        try:
            while not self.evtQ.empty():
                self.evtQ.get(True, 0.2)
        except: pass

        print("Closing processes", end="")
        self.P.close()
        self.evtQ.close()
        time.sleep(0.2)
        self.P.join_thread()
        self.evtQ.join_thread()
        while mp.active_children():
            print(mp.active_children())
            print(".", end=""); time.sleep(0.5)
        self.frontend.join()
        print("\nClosed frontend")

    def changeTitle(self, t):
        self.P.put(("title", str(t)))

    def startBatchKB(self):
        self.batchKB = []
    def endBatchKB(self):
        self.P.put(('keyBatch', self.batchKB))
        self.batchKB = None

    def bindKey(self, k, f):
        if self.batchKB is None:
            self.P.put(("key", k))
        else:
            self.batchKB.append(k)
        self.handles[k] = f

    def frameUpdate(self):
        pass
    def postProcess(self):
        pass
    def onMove(self):
        pass
    def facing(self):
        return (self.α, self.β)

    def fps(self):
        print("fps:", self.frameNum / self.totTime)

    def frameProfile(self, i, end=False):
        try: _ = self.ftime
        except:
            self.ftime = {}
            self.ftx = {}; self.ftmax = {}
            self.prevT = 0
            self.totMax = 0
        if i not in self.ftime:
            self.ftime[i] = 0
            self.ftmax[i] = 0
            self.ftx[len(self.ftime)-1] = i

        t = time.perf_counter()
        self.ftime[i] += t - self.frameStart
        if self.frameNum > 10:
            self.ftmax[i] = max(self.ftmax[i], t - self.prevT)
            if end:
                self.totMax = max(self.totMax, t - self.frameStart)
        self.prevT = t

    def printProfile(self, recur=False):
        if self.frameNum == 0: return

        if recur:
            try: _ = self.firstRecur
            except:
                self.firstRecur = True
                print('\n' * len(self.ftx))
            print('\033[A' * (len(self.ftx) + 1), end='')

        print('Avg     Max')
        for i in range(len(self.ftx)):
            x = self.ftx[i]
            if x == '.': continue
            offset = 0 if i == 0 else self.ftime[self.ftx[i-1]]
            t = (self.ftime[x] - offset) / self.frameNum
            mt = self.ftmax[x]

            print(f'{fmtTime(t)}  {fmtTime(mt)} {x}')

        tt = (self.ftime[x] - self.ftime['.']) / self.frameNum
        print(f'\033[96m{tt:.4f}  {self.totMax:.4f} Total \033[0m')

        if not recur: return
        for i in self.ftime:
            self.ftmax[i] = 0
            self.totMax = 0

if __name__ == "__main__":
    pass
