# ======== ========
# Copyright (C) 2020-2021 Louis Zhang
# Copyright (C) 2020-2021 AgentX Industries
#
# This file (Multi.py) is part of AXI Combat.
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

from tkinter import *
from math import sin, cos, sqrt, pi, atan2, asin, acos
import numpy
import numpy.random as nr
import random
import time

nr.seed(int((time.time() * 1000) % 1000))
random.seed(int((time.time() * 1000) % 1000))

from Compute import *
import multiprocessing as mp
import os, sys
PLATFORM = sys.platform

import importlib

import json

from Rig import Rig

import Phys

from Sound import SoundManager

from Network import TCPServer
import queue

import OpsConv
import AI
import Anim

from VertObjects import VertWater0, VertRing
from ParticleSystem import AttractParticleSystem

from IK import doFullLegIK, doArmIK

PATH = OpsConv.PATH
SWITCHABLE = True
SHOWALL = False
GESTLEN = 0.6
LOADALL = True

def mkServer(pi, po, kwargs):
    a = TCPServer(pi, po, isclient=False, **kwargs)
    a.run()
def mkClient(pi, po, kwargs):
    a = TCPServer(pi, po, isclient=True, **kwargs)
    a.run()

def playSound(si):
    a = SoundManager(si)
    a.run()

class CombatApp(ThreeDBackend, AI.AIManager, Anim.AnimManager):
    def __init__(self):

        self.maxFPS = 66

        kwargs = OpsConv.getSettings()
        width, height, fovx = kwargs["W"], kwargs["H"], kwargs["FOV"]
        volm = float(kwargs["Volume"])
        volm = np.array((volm, volm))

        super().__init__(width, height, fovx=fovx,
                         downSample=1)

        self.si = mp.Queue(64)
        self.SM = mp.Process(target=playSound, args=(self.si,), name="Sound")
        self.SM.start()
        self.si.put({"Play":(PATH + "../Sound/Plains3v4.wav", volm, True)})

        self.si.put({'Preload':[PATH + "../Sound/Noise.flac"]})

        self.proceed = True
        try:
            stage, gameId, server, name, isClient, selChar, aiNums = self.waitMenu()
        except TypeError:
            self.proceed = False

        self.si.put({"Fade":{'Time':0, 'Tracks':{PATH + '../Sound/Plains3v4.wav'}}})

        if not self.proceed: return

        if max(selChar, *aiNums, -1) > 2:
            global LOADALL
            LOADALL = True

        self.si.put({"Play":(PATH + "../Sound/Noise.flac", volm * 0.5, True)})

        kwargs = OpsConv.getSettings()
        width, height = kwargs["W"], kwargs["H"]
        self.setWH(width, height)

        volm = float(kwargs["Volume"])
        volm = np.array((volm, volm))

        volmFX = float(kwargs["VolumeFX"])
        volmFX = np.array((volmFX, volmFX))

        qi = mp.Queue(4)
        qo = mp.Queue(4)

        self.remoteServer = server
        self.gameId = gameId
        self.stage = stage
        self.uname = name
        self.volm = volm
        self.volmFX = volmFX
        self.aiNums = aiNums

        p = {"name":name, "host":server, "stage":stage, "gameId":gameId}
        if isClient:
            net = mp.Process(target=mkClient, args=(qi, qo, p), name="Network")
        else:
            net = mp.Process(target=mkServer, args=(qi, qo, p), name="Network")

        net.start()
        self.server = net
        self.qi = qi
        self.qo = qo
        self.isClient = isClient

        self.shRes = kwargs["SH"]
        self.doSh = kwargs["FS"]
        self.doVl = kwargs["FV"]
        self.doBloom = kwargs["BL"]
        self.doSSR = kwargs["SSR"]
        self.doRTVL = kwargs["RTVL"]
        self.renderBackend = kwargs["Render"]

        ssrLevels = [0, 160, 320, 640]

        with open(PATH + "Shaders_src/av_SSR_temp.c") as f:
            with open(PATH + "Shaders_src/av_SSR.c", "w") as g:
                for i in f.readlines():
                    if i[0] == "#":
                        if "REFL_LENGTH" in i:
                            i = " ".join(i.split(" ")[:-1]) + " "
                            i += str(ssrLevels[self.doSSR]) + "\n"
                    g.write(i)

        rvlLevels = [0, 8, 16, 64]
        absLevel = 0.06
        with open(PATH + "Shaders_src/av_fog_temp.c") as f:
            with open(PATH + "Shaders_src/av_fog.c", "w") as g:
                for i in f.readlines():
                    if i[0] == "#":
                        if "NSAMPLES" in i:
                            i = " ".join(i.split(" ")[:-1]) + " "
                            i += str(rvlLevels[self.doRTVL]) + "\n"
                        elif "ABSORB" in i:
                            i = " ".join(i.split(" ")[:-1]) + " "
                            i += str(absLevel) + "f\n"
                    g.write(i)

        stageNames = ["Desert", "CB Atrium", "Taiga",
                      "New Stage", "Forest", 'Strachan']
        self.changeTitle("AXI Combat - " + stageNames[self.stage])

        self.ENVTRACKS = ["New_rv1.ogg", "TextureA9.ogg", "Plains4v_ext.ogg",
                          "H8.ogg", '', '']

        self.α = 4.1; self.β = 0.1
        self.pos = numpy.array([35.8,  3.4, 31.3])

        self.ambLight = 0.08

        self.players = []
        self.maxHP = 40

        self.hvel = 4
        self.poseDt = 1.5
        self.gestLen = GESTLEN

        self.numBullets = 20
        self.bulletSpeed = 15
        self.COSTS = {"blank":0.02, "orange":0.2, "red":0.1, "black":0.35}

        self.selchar = selChar

        self.uInfo = {}

        self.fCam = False
        self.frameFired = False
        self.frameFiredOld = False

        self.activePlayers = {}
        self.actPlayers = {}
        self.lastTimes = {}

        self.expNum = 0
        self.exscale = 10.
        self.expPow = 2.7

        self.dofFoc = 3

        exps = [1.4 for _ in stageNames]
        exps[2] = 1.2
        self.exposure = exps[self.stage]
        self.blackPoint = 0.02

        self.tonemap = 'aces'
        self.doSSAO = False
        self.showDebug = False
        self.doMB = True

        self.camAvg = False
        self.cam1P = False
        self.camFree = False
        self.envPointLights = []

        self.stageFlags = {}

    def waitMenu(self):
        # server, gameId, stage, name, isClient
        wait = True
        while wait:
            try:
                action = self.evtQ.get(True, 0.2)
                if "Run" in action:
                    return action["Run"]
                elif "Vol" in action:
                    try: self.si.put_nowait(action)
                    except Full: pass
                elif "Play" in action or "Fade" in action or "Cresc" in action:
                    self.si.put(action)
            except Empty: pass

    def customizeFrontend(self):
        self.bindKey("r", self.rotateLight)
        if SWITCHABLE:
            self.bindKey("f", self.tgControl)
            self.bindKey("F", self.tgControl1)
        self.bindKey("e", self.mvCam)
        self.bindKey("x", lambda: self.fireAnim("blank"))
        self.bindKey("z", lambda: self.fireAnim("orange"))
        self.bindKey("c", lambda: self.fireAnim("red"))
        self.bindKey("v", lambda: self.fireAnim("black"))
        self.bindKey("<space>", self.jump)
        self.bindKey("<Up>", self.z1)
        self.bindKey("<Down>", self.z2)

        self.enableDOF(dofR=16, rad=0.04)

        self.gestures = []
        p = PATH + "../Poses/"
        for g in ["Armcross.pose", "Bow.pose", "Hi.pose", "Hold.pose"]:
            self.gestures.append(Anim.flattenPose(json.load(open(p+g))))

        self.bindKey("1", lambda: self.gesture(self.selchar, 0))
        self.bindKey("2", lambda: self.gesture(self.selchar, 1))
        self.bindKey("3", lambda: self.gesture(self.selchar, 2))
        self.bindKey("4", lambda: self.gesture(self.selchar, 3))
        self.bindKey("5", lambda: self.gesture(self.selchar, 4))

        self.bindKey("g", self.foc1)
        self.bindKey("G", self.foc2)
        self.bindKey("h", self.tgAO)
        self.bindKey("n", self.tgDebug)
        self.bindKey("y", self.tgMB)
        self.bindKey('t', self.tgTM1)
        self.bindKey('T', self.tgTM2)
        self.bindKey('<F5>', self.tgCamAvg)
        self.bindKey('<F6>', self.tgCam1P)
        self.bindKey('<F7>', self.tgCamFree)

        self.bindKey('p', self.printStuff)
        if self.stage == 4:
            self.bindKey('o', self.lightTest)
        self.bindKey('i', self.respawnTest)

        self.bindKey('b', self.testAniso)
        self.aniso = 4

        self.iceEffect = False
        self.bindKey('m', self.tgIce)

        self.bindKey('j', self.tgBlack1)
        self.bindKey('J', self.tgBlack2)

        self.bindKey('k', self.tgSpec)

        self.bindKey('0', self.pause)
        self.bindKey('9', self.tgFxaa)
        self.useFxaa = 1

        self.bindKey('<Control-r>', self.reloadStage)
        self.bindKey('<Control-R>', self.reloadStageHard)
        self.bindKey('<Control-t>', self.reloadShaders)

        self.bindKey('u', self.dofLess)
        self.bindKey('U', self.dofMore)
        self.apFac = 0.4

    def dofLess(self): self.apFac /= 1.1
    def dofMore(self): self.apFac *= 1.1

    def reloadStage(self):
        self.STAGECONFIG = importlib.reload(self.STAGECONFIG)
        print('Reloaded stage config')

    def dummyAddVertObject(self, *args, **kwargs):
        self.vertObjects.append(self.oldVertObjects.pop(self.baseVertObjN))
        vo = self.vertObjects[-1]
        if 'useShaders' in kwargs:
            self.matShaders[vo.texNum].update(kwargs['useShaders'])
        if Phys.eucDist(args[1], vo.coords) > 0.001:
            self.draw.translate(np.array(args[1]) - vo.coords,
                                vo.cStart*3, vo.cEnd*3, vo.texNum)
            vo.coords = args[1]
        if type(self.vertObjects[-1]) is VertModel:
            if self.vertObjects[-1].prevMtl is not None:
                self.dummyAddVertObject(*args)
        return True
    def reloadStageHard(self):
        self.STAGECONFIG = importlib.reload(self.STAGECONFIG)
        self.directionalLights = []
        self.envPointLights = []
        self.spotLights = []
        self.particleSystems = []
        self.oldVertObjects = list(self.vertObjects)
        self.vertObjects = self.oldVertObjects[:self.baseVertObjN]
        self.addVertObject = self.dummyAddVertObject
        self.makeSkybox = lambda *args, **kwargs: self.skyBox
        self.STAGECONFIG.setupStage(self)
        self.frameNum = 0
        self.rotateLight()
        for i in self.actPlayers:
            try: del self.players[i]['isHit']
            except KeyError: pass
        print('Reloaded stage config hard')

    def reloadShaders(self):
        self.draw.reloadShaders(stage=self.stage)
        print('Reloaded draw shaders')


    def tgFxaa(self):
        self.useFxaa = 1 - self.useFxaa
    def pause(self):
        input('Continue: ')

    def tgBlack1(self):
        self.blackPoint += 0.01
        print('black point', self.blackPoint)
    def tgBlack2(self):
        self.blackPoint -= 0.01
        print('black point', self.blackPoint)
    def tgSpec(self):
        tn = self.players[self.selchar]['obj'].texNum
        if 'spec' in self.matShaders[tn]:
            self.matShaders[tn]['spec'] = 1 - self.matShaders[tn]['spec']
            self.draw.changeShader(tn, self.matShaders[tn])
        d = self.directionalLights[0]
        self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

    def tgIce(self):
        if self.iceEffect is False:
            self.iceEffect = (True, self.selchar)
        elif self.iceEffect[1] == self.selchar:
            self.iceEffect = False

    def testAniso(self):
        self.aniso *= 2
        if self.aniso > 8:
            self.aniso = 1
        self.draw.setAnisotropy(self.aniso)
        print('Anisotropy', self.aniso)

    def printStuff(self):
        print('pos', self.pos,
              'charpos', self.players[self.selchar]['b1'].offset[:3])
        print('a', self.α, 'b', self.β)

    # ==== Temple interactivity ====
    def lightTest(self):
        self.transStart = time.time()
        try: _ = self.changedMusic
        except:
            self.changedMusic = 0
        self.changedShader = False

        self.si.put({'Fade':{'Time':0, 'Tracks':{PATH+'../Sound/NoiseOpen.flac'}}})

        self.si.put({'Play':(PATH+'../Sound/NoiseFlash.flac', self.volmFX * 1.1, False)})

        self.flashKF = Anim.loadAnim(PATH+'../Poses/FlashTest.ava', timeScale=1.2)
        for p in self.actPlayers:
            self.players[p]['poseFlash'] = self.flashKF[0][0]

        for v in self.vtNames:
            if 'Sandstone' in v:
                self.sandstoneBricksTex = self.vtNames[v]


    def testRM(self, rm=None):
        if rm is None:
            rm = [x <= self.players[-1]["obj"].texNum for x in range(len(self.vtNames))]
        if self.stage < 4:
            return rm
        return self.STAGECONFIG.getRenderMask(self, rm)


    # ==== Respawning / recovery ====
    def setupRestKF(self, sc):
        self.restKF = Anim.loadAnim(PATH+'../Poses/RestTest.ava')

        off_fact = 1 if sc == 2 else 1.3
        arm_fact = (2.7, 2.4, 2, 1.2, 2.4, 2.4, 2.5, 2.2, 2.3, 1.8)[sc]
        for i in range(len(self.restKF)):
            tempPose = self.restKF[i][1]
            armPose = tempPose['children'][0]['children'][0]['angle']
            if armPose[2] > 0: armPose[2] -= 2*pi
            armPose[2] *= arm_fact
            self.restKF[i] = (self.restKF[i][0],
                              tempPose,
                              self.restKF[i][2] * off_fact)

    def respawnTest(self, sc=None):
        if sc is None: sc = self.selchar

        a = self.players[sc]
        if a['jump'] > 0: return

        if self.restPlayer is None and sc != self.lastRestPlayer:
            self.restPlayer = sc
            self.lastRestPlayer = sc
        else: return False

        self.setupRestKF(sc)

        if 'restAnim' in a: return

        self.si.put({'Play':(PATH+'../Sound/Recover.flac', self.volmFX * 0.8,
                             False)})

        a['restStart'] = time.time()
        a['restFrame'] = -100
        a['restAnim'] = self.restKF[0][0]
        r = self.restRings
        self.ringPos = np.array(a['b1'].offset[:3])
        self.draw.translate(a['b1'].offset[:3],
                            r.cStart*3, r.cEnd*3, r.texNum)
        a['legIKoffset'] = 0
        a['tempYPos'] = float(a['b1'].offset[1])

        if self.getHealth(a['id']) < 0:
            a['pv'].colliders[1].hc += self.maxHP * self.getHealth(a['id']) - 0.01

    def undoGhost(self):
        sc = self.restPlayer
        a = self.players[sc]
        for xn in a["ctexn"]:
            if "temp" in self.matShaders[xn]:
                self.matShaders[xn] = self.matShaders[xn]["temp"]

            self.draw.changeShader(xn, self.matShaders[xn], stage=self.stage)


        self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])
        for xn in a["ctexn"]:
            self.draw.highlight([0,0,0], xn, mult=True)
            self.matShaders[xn]['highlight'] = (0,0,0)

    def testRest(self):
        sc = self.restPlayer
        if sc is None: return

        a = self.players[sc]
        r = self.restRings

        addKF = [(0, 0), (1, 0.3), (2, 0.4), (3, 0.2), (5, 0)]

        if 'restAnim' in a:
            t = time.time() - a['restStart']
            a['moving'] = False
            a['animTrans'] = -1
            self.stepPoseLoop(a, a['obj'], self.restKF, self.frameTime*0.4,
                              loop=False, timer='restAnim')

            self.setYoffsetTest(a)

            self.matShaders[r.texNum]['args']['emPow'] = Anim.interpAttr(t, addKF)
            self.draw.changeShader(r.texNum, self.matShaders[r.texNum])

            self.draw.setUVOff(r.texNum, (0,0), (1,1), (t*0.2, 0))

            if self.getHealth(a['id']) < 0.6:
                a['pv'].colliders[0].hc -= self.frameTime * 4

            xn = a["ctexn"][0]
            mat = self.matShaders[xn]
            if 'emPow' in mat['args']:
                mat['args']['emPow'] -= 0.6 * self.frameTime
                self.draw.changeShader(xn, mat)

                if mat['args']['emPow'] < 0:
                    mat['args']['emPow'] = 0
                    a['restFrame'] = self.frameNum
                    a['undoGhostTime'] = time.time()
                    self.undoGhost()
            elif 'undoGhostTime' in a:
                hl = max(0, min(1, 0.6 * (time.time() - a['undoGhostTime'])))
                for i in a["ctexn"]:
                    self.draw.highlight([hl,hl,hl], i, mult=True)

            if self.frameNum - a['restFrame'] == 1:
                d = self.directionalLights[0]
                self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

            if a['restAnim'] >= self.restKF[-1][0]:
                del a['restAnim']
                self.restPlayer = None
                if 'deathTime' in a:
                    del a['deathTime']
                self.draw.translate(-self.ringPos,
                                    r.cStart*3, r.cEnd*3, r.texNum)
                a['movingOld'] = True

    def setYoffsetTest(self, p):
        try: footR = p['b1'].children[1].children[0].children[0]
        except IndexError: return

        ihR = self.STAGECONFIG.getHeight(self, footR.TM[3,:3])
        offR = footR.TM[3,1] - 0.126 - ihR
        p['b1'].offset[1] -= offR


    # ==== Camera control ====
    def tgCamFree(self):
        self.camFree = not self.camFree
    def tgCamAvg(self):
        self.camAvg = not self.camAvg
    def tgCam1P(self):
        self.cam1P = not self.cam1P
        if self.cam1P:
            self.camAvg = False
            self.fCam = True
            self.cam1Pframe = self.frameNum
            self.α = -self.players[self.selchar]["cr"] + pi/2

    def tgTM1(self):
        tm = ('gamma', 'reinhard', 'reinhard2', 'aces')
        self.tonemap = tm[tm.index(self.tonemap) + 1 - len(tm)]
    def tgTM2(self):
        tm = ('gamma', 'reinhard', 'reinhard2', 'aces')
        self.tonemap = tm[tm.index(self.tonemap) - 1]

    def tgMB(self): self.doMB = not self.doMB
    def tgAO(self): self.doSSAO = not self.doSSAO
    def foc1(self):
        self.exposure *= 1.1
        print(self.exposure)
    def foc2(self):
        self.exposure /= 1.1
        print(self.exposure)
    def tgDebug(self): self.showDebug = not self.showDebug

    def gesture(self, pn, n, gi=None):
        p = self.players[pn]
        if p["gesturing"]: return

        p["gesturing"] = True
        p["gestStart"] = time.time()
        if gi is None:
            p["gestId"] = self.frameNum
        else:
            p["gestId"] = gi
        p["gestNum"] = n
        p["poset"] = 0
        p["pstep"] = 3
        p['tempPose'] = p['rig'].exportPoseFlat()

    def jump(self, pn=None):
        if pn is None: pn = self.selchar
        p = self.players[pn]
        if p["jump"] > 0:
            return

        p["jump"] = self.frameNum
        p["pv"].v[1] = 6.0
        p['pv'].forces[0,1] = -9.81

        jfn = '../Sound/New/2H_Sharp_Swing_{}.wav'.format(random.randint(1, 4))
        self.si.put({"Play":(PATH + jfn, self.volmFX / 3,
                             (p['b1'].offset[:3], 5, 1.2))})

    def stepGest(self, p, vobj, st=1):
        p["poset"] += p["pstep"] * st
        if p["poset"] > 1:
            p["poset"] = 1
            if not "gestMid" in p:
                p["gestMid"] = time.time()
            else:
                if (time.time() - p["gestMid"]) > self.gestLen:
                    p["pstep"] = -3

        if p["gestNum"] == 3:
            self.getHandPos(p["id"])

        finish = False
        if p["poset"] < 0:
            p["poset"] = 0; finish = True

        initPose = self.idleFlat if p['pstep'] < 0 else p['tempPose']
        p["rig"].interpPoseFlat(initPose, self.gestures[p["gestNum"]], p["poset"])
        self.updateRig(p["rig"], p["ctexn"], p["num"], vobj)

        if finish: self.gestFinish(p["id"])

    def gestFinish(self, pn):
        p = self.players[pn]
        p["gesturing"] = False
        p["poset"] = 0
        p["pstep"] = 6
        p["gestNum"] = None
        del p["gestMid"]


    def testAnim(self, p, interp=None):
        """p in self.players"""
        if self.frameNum < 4: return
        if p['moving']: return

        regenTargs = False

        try: _ = self.testTargs
        except:
            regenTargs = True

            with open(PATH+'../Models/EyeTracking.txt') as fuv:
                uvInfo = fuv.readlines()
                uvInfo = json.loads(''.join(uvInfo[3:]))
                self.eyeUV = {int(n):uvInfo[n] for n in uvInfo}
        else:
            if self.testTargNum != len(self.actPlayers):
                regenTargs = True

        if regenTargs:
            activeIds = list(self.actPlayers)
            self.testTargNum = len(activeIds)
            pm = np.random.permutation(activeIds)
            targs = [None for _ in range(self.NPLAYERS)]
            for t in range(len(pm)):
                targs[pm[t]] = activeIds[t]
                if pm[t] == activeIds[t]:
                    targs[pm[t]] = activeIds[t-1]
            # {src: targ, ...}
            self.testTargs = targs


        head = p['b1'].children[0].children[2]

        ang = head.angles % (2*pi)
        rot = np.array(head.TM[:3,:3])
        pos = head.TM[3,:3] + np.array([0,0.1,0])

        tg = self.testTargs[p['id']] or 0
        if tg == p['id']: return
        target = self.players[tg]

        thead = target['b1'].children[0].children[2]
        tpos = thead.TM[3,:3] + np.array([0,0.1,0])

        vec = (tpos - pos) @ np.transpose(rot)
        vec = vec / Phys.eucLen(vec)


        rz = atan2(vec[2], vec[0])
        ry = -asin(vec[1])

        targz = self.fmtAng(rz + ang[1])
        targy = self.fmtAng(ry + ang[2])


        targz = min(0.5, max(-0.5, targz/2))
        targy = min(0.5, max(-0.5, targy/3))
        if vec[0] < 0.5:
            targy *= max(0, 2*vec[0])

        if vec[0] < -0.5:
            fact = 2*(1+vec[0])
            targz = targz * fact

        if interp is None: interp = 1
        pose = {'angle': (0, targz, ang[2] if 'restAnim' in p else targy)}
        temp = head.exportPose()
        final = p['rig'].interpTree(temp, pose, interp)
        head.rotate(final['angle'])

        if p['id'] in self.eyeUV:
            uvp = self.eyeUV[p['id']]
            scale = uvp[1][0] - uvp[0][0]
            sigH = 1 if uvp[2] == 'L' else -1
            sigV = 1 if uvp[3] == 'U' else -1

            self.draw.setUVOff(p['obj'].texNum, *uvp[:2],
                               (targy * (0.2  * scale * sigV),  # vertical
                                targz * (0.12 * scale * sigH))) # horizontal

    def testLegIK(self, p, interp=None):
        """p in self.players"""
        if self.frameNum < 4: return
        if p['moving']: return

        try:
            legRU = p['b1'].children[1]
        except IndexError: return
        self.doLegIK(legRU, interp)

        legLU = p['b1'].children[2]
        self.doLegIK(legLU, interp)

    def doLegIK(self, legU, interp=None):
        legD = legU.children[0]
        foot = legD.children[0]

        pos = legU.TM[3,:3]
        ih = self.STAGECONFIG.getHeight(self, pos) + 0.114 # Account for foot
        targY = abs(pos[1] - ih)
        d1 = abs(legD.offset[1])
        d2 = abs(foot.offset[1])

        # Possible float precision issues
        if d1 + d2 < targY or d1 + targY < d2 or d2 + targY < d1:
            U = 0
            L = 0
        else:
            try:
                U = -acos((d1**2 + targY**2 - d2**2) / (2*d1*targY))
                L = pi - acos((d1**2 + d2**2 - targY**2) / (2*d1*d2))
            except ValueError:
                U = 0
                L = 0

        # -Z is UP, +Z is DOWN
        if interp is None:
            legU.rotate((0, 0, U))
            legD.rotate((0, 0, L))
            foot.rotate((0, 0, max(-pi/6, -U-L)))
            return

        pose = {'angle':(0,0,U), 'children':[
                {'angle':(0,0,L), 'children':[
                 {'angle':((0, 0, max(-pi/6, -U-L)))}
                ]}
               ]}

        temp = legU.exportPose()
        i = self.players[0]['rig'].interpTree(temp, pose, interp)
        legU.importPose(i)

    def setFullLegIKPos(self, a):
        try:
            footR = a['b1'].children[1].children[0].children[0]
            ihR = self.STAGECONFIG.getHeight(self, footR.TM[3,:3])
            ikR = np.array((footR.TM[3,0], ihR, footR.TM[3,2]))
            footL = a['b1'].children[2].children[0].children[0]
            ihL = self.STAGECONFIG.getHeight(self, footL.TM[3,:3])
            ikL = np.array((footL.TM[3,0], ihL, footL.TM[3,2]))
            a['legIKPos'] = (ikR, ikL)
            a['lastIKfacing'] = a['cr']
        except IndexError: pass

    def setYoffset(self, p):
        ih = self.STAGECONFIG.getHeight(self, (p['b1'].offset[:3] - p['animOffset'][:3]))

        p['b1'].offset[1] = ih + p['cheight'] + p['animOffset'][1]
        p['legIKoffset'] = 0

        if p['moving']: return

        try:
            legRU = p['b1'].children[1]
            legLU = p['b1'].children[2]
        except IndexError: return

        ihR = self.STAGECONFIG.getHeight(self, legRU.TM[3,:3])
        ihL = self.STAGECONFIG.getHeight(self, legLU.TM[3,:3])

        if abs(ihL - ihR) > 0.8: return
        p['b1'].offset[1] = min(ih, ihL, ihR) + p['cheight']
        p['legIKoffset'] = ih - min(ih, ihL, ihR)


    def getHandPos(self, pn):
        p = self.players[pn]

        b = p["b1"].children[0].children[0]
        while len(b.children) > 0: b = b.children[0]
        pr = np.array(b.TM[3,:3])

        b = p["b1"].children[0].children[1]
        while len(b.children) > 0: b = b.children[0]
        pl = np.array(b.TM[3,:3])

        i = np.array((1,1,1.)) * min(1, 1.33 * max(0, p["poset"] - 0.25))**2
        self.pointLights.append({"i":i, "pos":(pr + pl) / 2})

    def z1(self): self.setFOV(max(20, self.fovX * 0.96))
    def z2(self): self.setFOV(min(120, self.fovX * 1.04166))

    def tgControl(self):
        self.selchar = (self.selchar + 1) % len(self.players)
    def tgControl1(self):
        self.selchar = (self.selchar - 1) % len(self.players)

    def mvCam(self):
        if not self.fCam:
            self.α = -self.players[self.selchar]["cr"] + pi/2
        if not self.cam1P:
            self.fCam = not self.fCam
        self.players[self.selchar]["fCam"] = self.fCam

    def moveKey(self, key):
        rv = 3
        sa = self.players[self.selchar]
        if key == "u": sa["moving"] = 1
        elif key == "d": sa["moving"] = -1
        elif key == "r": sa["cv"] = -rv
        elif key == "l": sa["cv"] = rv
        elif key == "ZV": sa["moving"] = 0
        elif key == "ZH": sa["cv"] = 0

    def stepPose(self, p, vobj, st=1):
        p["poset"] += p["pstep"] * st
        if (p["poset"] > 1):
            if p["posen"] == (len(self.poses) - 2):
                p["pstep"] = -p["pstep"]
                p["poset"] = 1 - p["poset"] + int(p["poset"])
            else:
                p["posen"] += 1
                p["poset"] -= int(p["poset"])
        elif (p["poset"] < 0):
            if p["posen"] == 0:
                p["pstep"] = -p["pstep"]
                p["poset"] = -p["poset"] + int(p["poset"])
            else:
                p["posen"] -= 1
                p["poset"] += 1 - int(p["poset"])

        p["rig"].interpPose(self.poses[p["posen"]], self.poses[p["posen"]+1],
                            p["poset"])

    def rotateLight(self, rl=None):
        if rl is None: a = self.directionalLights[0]["dir"][1] + 0.05
        else: a = rl

        self.directionalLights[0]["dir"][1] = (a % pi)
        self.directionalLights[1]["dir"][1] = (a % pi) + pi
        ti = abs(self.directionalLights[0]["dir"][1])

        sc = self.shadowCams[0]
        sc["dir"] = self.directionalLights[0]["dir"]
        sc["pos"] = -40 * viewVec(*sc["dir"]) + numpy.array([20, 5, 20])
        self.updateShadowCam(0, updateShaders=True)
        sc["bias"] = (0.18 * abs(cos(ti)) + 0.12) * 2560 / self.shRes

        tempObjs = np.array(self.castObjs)
        tempObjs = tempObjs * (1 - np.array(self.testRM()))

        self.shadowMap(0, tempObjs, bias=sc["bias"])
        self.simpleShaderVert()

        d = self.directionalLights[0]
        self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

        self.shadowChar()

    def test(self, n):
        self.players[n]["isHit"] = self.frameNum

    def explode(self, p, force=False, eNum=None):
        if self.isClient and (not force): return
        if eNum is not None: self.expNum = eNum

        e = self.exploders[self.expNum]
        e["pos"] = np.array(p)
        e["active"] = True
        e["start"] = time.time()
        self.matShaders[e["obj"].texNum]['args'].update(emPow=4)

        self.draw.translate(e["pos"], e["obj"].cStart*3, e["obj"].cEnd*3,
                            e["obj"].texNum)

        self.expNum = (self.expNum + 1) % len(self.exploders)

        self.si.put({"Play":(PATH+"../Sound/Exp.wav",
                             self.volmFX / 3, (np.array(p), 6, 1))})

    def extractByUV(self, src, dst, u1,u2,v1,v2):
        """Origin is bottom left, u up, v right"""
        t1 = src
        t2 = dst
        t1.create()
        tu = np.array(t1.u)
        tv = np.array(t1.v)
        cond = ((tu >= u1) & (tu <= u2) & (tv >= v1) & (tv <= v2))
        #print(cond.shape, cond[0])
        cond = cond.all(axis=1)
        if type(t1.wedgePoints) is list:
            t1.wedgePoints = np.array(t1.wedgePoints)
            t1.vertNorms = np.array(t1.vertNorms)
        t2.wedgePoints = t1.wedgePoints[cond]
        t2.vertNorms = t1.vertNorms[cond]
        t2.bones = np.array(t1.bones)[cond]
        t2.u = (tu[cond] - u1) / (u2 - u1)
        t2.v = (tv[cond] - v1) / (v2 - v1)
        t2.numWedges = np.sum(cond)
        t2.create = lambda: 1
        cond = np.logical_not(cond)
        t1.wedgePoints = np.array(t1.wedgePoints)[cond]
        t1.vertNorms = np.array(t1.vertNorms)[cond]
        t1.bones = np.array(t1.bones)[cond]
        t1.u = tu[cond]
        t1.v = tv[cond]
        t1.numWedges = np.sum(cond)
        t1.create = lambda: 1

    def addPlayer(self, o):
        pv = Phys.RigidBody(64, [0.,0,0], forces=[(0,0,0)], noforces=False)
        pv.addCollider(Phys.CircleCollider(0.5, (0,-0.5,0), rb=pv))
        pv.addCollider(Phys.CircleCollider(0.5, (0,0.51,0), rb=pv))
        pv.colliders[0].prop = "player"
        pv.colliders[1].prop = "player"
        pv.colliders[0].hc = 0
        pv.colliders[1].hc = 0
        pv.colliders[0].num = len(self.players)
        pv.colliders[1].num = len(self.players)
        pv.colliders[0].isHit = lambda x: self.test(x)
        pv.colliders[1].isHit = lambda x: self.test(x)
        pv.colliders[0].onExplode = lambda x: self.explode(x)
        pv.colliders[1].onExplode = lambda x: self.explode(x)

        a = {"posen":0, "poset":0, "pstep":6,
             "moving":False, "movingOld":False, "cr":0, "cv":0,
             "ctexn":None, "rig":None, "obj":o,
             "pv":pv, "num":len(self.players), "isHit":-100,
             "gesturing":False, "gestNum":None, "gestId":None,
             "jump":-1, "fCam": False,
             "id":self.NPLAYERS, 'lastStep':0, 'legIKoffset':0,
             'animOffset':np.zeros(3), 'animTrans':-100,
             'frameFired':-100, 'fireColor':None, 'fireVH':0,
             'throwAnim':False, 'animFired':False,
             'poseThrow':0, 'poseIdle':0,
             'vh':0}

        self.NPLAYERS += 1
        self.players.append(a)
        self.w.addRB(pv)
        pv.disable()

        a["cheight"] = self.rpi[a["num"]][2] + 0.06 * (self.stage == 2)

        r = json.load(open(self.rpi[a["num"]][0]))
        a["rig"] = Rig(r, scale=self.rpi[a["num"]][1])
        a["b1"] = a["rig"].b0
        a["allBones"] = a["rig"].allBones

        a["Energy"] = 1


        ps = AttractParticleSystem(
                0.4, (0,0,0.), 6,
                (0,0,0.), (0,0),
                vel=0.0, randVel=0.0,
                nParticles=40,
                size=0.1, opacity=0.5,
                color=(0.2,0.2,0.2), randColor=0)
        self.addParticleSystem(ps)
        a['projFX'] = ps
        a['projFXstart'] = -1
        ps.shader = 2


    def createObjects(self):
        if self.stage < 4:
            snd = self.ENVTRACKS
            self.si.put({'Preload':[PATH+'../Sound/' + snd[self.stage]]})

        self.NPLAYERS = 0

        print("Loading textures")

        self.w = Phys.World()

        mpath = PATH + "../Models/"

        # Rigfile, scale, height
        self.rpi = [(mpath + "Body/B10Fc.rig", 0.2, 1.47),
                    (mpath + "Samus_PED/Samus_3B.rig", 1.33, 1.66),
                    (mpath + "Zelda2/Test5b.rig", 0.33, 1.16),
                    (mpath + "L3/L3.rig", 0.75, 1.16),
                    (mpath + "Test3/Test3J.rig", 0.8 / 1.08, 1.32 / 1.08),
                    (mpath + "Zelda/Ztest3.rig", 1, 1.32),
                    (mpath + "LinkTP/Li.rig", 0.75, 1.5),
                    (mpath + "Ahri/Ahri4.rig", 1.8, 1.62),
                    (mpath + "Stormtrooper/Trooper5.rig", 1.4, 1.7),
                    (mpath + "Vader/Vader5.rig", 1.6, 1.56),
                    ]
        self.footSize = (0.2, 0.2, 0.1, 0.2, 0.1, 0, 0.2, 0.08, 0.16, 0.16)


        self.addVertObject(VertModel, [0,0,0],
                       filename=mpath+'Body/B10Fc.obj',
                       animated=True, mip=1, texMode=None,
                       scale=0.2, rot=(0,0,0),
                       shadow='R')
        for f in self.vtNames:
            mat = self.matShaders[self.vtNames[f]]
            if 'Cornea' in f:
                mat.update(shader='SSRopaque', args={'fresnelExp':3})
                self.corneaMtl = self.vtNames[f]
            if 'Gold' in f:
                mat.update(shader='metallic', args={'roughness':0.3})
            if 'Hair' in f:
                mat.update(args={'specular':0.8,
                            'NMmipBias':0.1, 'translucent':1,
                            'roughness':0.12, 'f0':0.6,
                            'hairShading':1}, normal='Hair')
            if 'Face' in f:
                mat.update(args={'specular':1}, normal='Face')
            if 'Skin' in f:
                mat.update(args={'specular':1}, normal='Body')
            if 'Metal' in f:
                mat.update(shader='metallic', args={'roughness':0.6})
            if 'ClothTest' in f:
                mat.update(normal='ClothTrim')
            if 'Clothes' in f:
                mat.update(normal='Clothes', args={'NMmipBias':0.1})

        self.addPlayer(self.vertObjects[-1])

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"Samus_PED/Samus_3B.obj",
                           animated=True, texMul=1, reflect="1a",
                           useShaders={'args':{'specular':1}},
                           scale=1.33, shadow="")
        t1 = self.vertObjects[-1]
        t2 = self.vertObjects[-2]
        self.extractByUV(t1, t2, 0,0.25,0,0.25)
        self.matShaders[t2.texNum] = {'shader':'add', 'noline':1, 'args':{'emPow':0.8}}

        self.addPlayer(self.vertObjects[-1])

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"Zelda2/Test5b.obj",
                           animated=True, texMul=2.5,
                           useShaders={'args':{'specular': 1}, 'normal':'Zelda'},
                           scale=0.33, shadow="R")
        t1 = self.vertObjects[-1]
        t2 = self.vertObjects[-2]
        self.extractByUV(t1, t2, 0.5,0.75,0.25,0.5)
        self.matShaders[t2.texNum].update(args={'specular':0.8,
                            'NMmipBias':0.1, 'translucent':1,
                            'roughness':0.12, 'f0':0.6,
                            'hairShading':1, 'tangentDir': 1}, normal='Z2H')

        self.addPlayer(self.vertObjects[-1])

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"L3/L3.obj",
                           animated=True, texMul=1,
                           useShaders={'args':{'specular': 1}, 'normal':'Link'},
                           scale=0.75, shadow="R")
        t1 = self.vertObjects[-1]
        t2 = self.vertObjects[-2]
        self.extractByUV(t1, t2, 0.5,0.75,0,0.25)
        self.matShaders[t2.texNum].update(args={'specular':0.8,
                            'NMmipBias':0.1, 'translucent':1,
                            'roughness':0.12, 'f0':0.6,
                            'hairShading':1, 'tangentDir': 1}, normal='L3H')

        self.addPlayer(self.vertObjects[-1])

        if LOADALL:
            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Test3/Test3J.obj",
                               animated=True, useShaders={'args':{'specular':1}},
                               scale=0.8 / 1.08, shadow="R")

            t1 = self.vertObjects[-1]
            t2 = self.vertObjects[-3]
            self.extractByUV(t1, t2, 352/1024,(352+128)/1024,513/1024,(513+256)/1024)
            self.matShaders[t2.texNum]['nocast'] = 1

            self.addPlayer(self.vertObjects[-1])
            self.matShaders[self.vertObjects[-1].nextMtl.texNum].update(
                shader='sub', args={'emPow':0.6}, noline=True)

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Zelda/Ztest4.obj",
                               animated=True,
                               texMul=2, useShaders={'args':{'specular':1}},
                               scale=1, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"LinkTP/Li.obj",
                               animated=True,
                               texMul=1.5, useShaders={'args':{'specular':1}},
                               scale=0.75, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Ahri/Ahri4.obj",
                               animated=True, useShaders={'args':{'specular':1}},
                               scale=1.8, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Stormtrooper/Trooper5.obj",
                               animated=True, useShaders={'args':{'specular':1}},
                               scale=1.4, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Vader/Vader5.obj",
                               animated=True, useShaders={'args':{'specular':1}},
                               scale=1.6, shadow="R")
            self.addPlayer(self.vertObjects[-1])

        self.baseVertObjN = len(self.vertObjects)

        # Setup stage
        STAGENAMES = 'Desert Atrium Taiga NewStage Forest Strachan'.split(' ')
        cs = __import__('Stages.' + STAGENAMES[self.stage],
                        fromlist=('setupStage'))

        cs.setupStage(self)
        self.STAGECONFIG = cs

        try:
            ms = self.matShaders
            ms[self.corneaMtl]['envFallback'] = self.skyBox.texNum
            ms[self.corneaMtl]['args']['rotY'] = ms[self.skyBox.texNum]['args']['rotY']
        except (AttributeError, KeyError): pass

        # Add projectiles and game elements
        self.spheres = []
        self.srbs = []
        p = [0,0,0]
        for i in range(self.numBullets):
            self.addVertObject(VertSphere, p, n=12, scale=0.25,
                               texture=PATH+"../Assets/Blank.png",
                               useShaders={'shader':"emissive",'args':{'emPow':2}})
            self.spheres.append(("blank", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(2, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.25, False,
                                                          rb=self.srbs[-1]))
            self.srbs[-1].disable()
            self.w.addRB(self.srbs[-1])

        self.sphereTrails = []
        for i in range(self.numBullets):
            self.addVertObject(VertPlane, self.spheres[i][1].coords - np.array([0,0.2,0]),
                               n=(1,1), scale=1, h1=[0.01,0,0], h2=[0,0.4,0],
                               texture=PATH+"../Assets/BlankAdd.png",
                               useShaders={'shader':"add",'args':{'emPow':0.4},
                                           'noline':True, 'texMode':'clamp'})
            self.sphereTrails.append(self.vertObjects[-1])

        for i in range(self.numBullets // 2):
            self.addVertObject(VertSphere, p, n=16, scale=0.5,
                               texture=PATH+"../Assets/Red.png",
                               useShaders={'shader':"emissive",'args':{'emPow':2.5}})
            self.spheres.append(("red", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(24, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.5, False,
                                                          rb=self.srbs[-1],
                                                          damage=4))
            self.srbs[-1].disable()
            self.w.addRB(self.srbs[-1])


        self.addVertObject(VertModel, [0,-0.6,0], scale=(1,0.6,1),
                           filename=PATH+'../Models/Rings.obj',
                           shadow='', useShaders={'shader':'add','args':{'emPow':0.5},
                                                  'noline':True})
        self.restRings = self.vertObjects[-1]

        self.addVertObject(VertSphere, [0,0,0], scale=0.06,
                           n=8, texture=PATH+"../Assets/LightBlue.png",
                           useShaders={'emissive':1})
        self.testSphere = self.vertObjects[-1]


        numFX = 4
        for i in range(numFX):
            self.addVertObject(VertRing, [0,0,0], n=16,
                radius=(0.5,1.2), z=0.3, uMult=5,
                texture="../Assets/tex1_64x64_fa5ab1f63d767af9_14.png",
                shadow="", useShaders={'shader':'add', 'args':{'emPow':0.6},
                                       'noline':True})
            obj = self.vertObjects[-1]
            obj.prevCoord = np.array([0,0,0.])
            obj.prevRot = np.identity(3)
            obj.timeStart = -1

        self.impulseFX = self.vertObjects[-numFX:]


        fogParams = {2: (0.14,0.01, 60,10,np.array((0.1,0.15,0.4)) * 0.016),
                     4: (0.02,0.002,40,30, np.array((0.15,0.18,0.2)) * 0.003),
                     5: (0.04,0.001,24,0, (0,0,0))}
        if self.stage in fogParams:
            fog, fabs, fdist, fheight, famb = fogParams[self.stage]

            self.addVertObject(VertPlane, [-1,-1,0],
                           h1=[2,0,0], h2=[0,2,0], n=1,
                           texture=PATH+"../Assets/Blank2.png",
                           useShaders={"2d":1, 'shader':"fog",
                                       'args':{'fogLight':fog, 'fogAbsorb':fabs,
                                       'fogDist':fdist, 'fogHeight':fheight,
                                       'fogAmb':famb}})
            self.fogMTL = self.vertObjects[-1].texNum

        if self.stage == 4:
            self.addVertObject(VertModel, [10,0,20], rot=(0,-pi/2,0),
                               filename=PATH+"../Models/Temple/Clouds.obj",
                               shadow="",
                               useShaders={'shader':'add','args':{
                                   'emPow':0.04, 'fadeDist':2}, 'noline':True})
            self.clouds = self.vertObjects[-1]

        for i in range(self.numBullets // 3):
            self.addVertObject(VertSphere, p, n=12, scale=0.25,
                               texture=PATH+"../Assets/Orange.png",
                               useShaders={'shader':'add','args':{'emPow':0.4}})
            self.spheres.append(("orange", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(10, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.25, False,
                                                          rb=self.srbs[-1],
                                                          damage=6,
                                                          explode=True))
            self.srbs[-1].disable()
            self.w.addRB(self.srbs[-1])

        self.pickups = []
        for i in range(1):
            self.addVertObject(VertSphere, p, n=12, scale=0.25,
                               texture=PATH+"../Assets/Green.png",
                               useShaders={'shader':'emissive',
                                           'args':{'emPow':1.8}})
            self.pickups.append({"pos":None, "t":-1, "obj":self.vertObjects[-1]})


        self.blackHoles = []
        for i in range(self.numBullets // 5):
            self.addVertObject(VertSphere, p, n=12, scale=0.3,
                               texture=PATH+"../Assets/Black.png",
                               useShaders={"emissive":0.0})
            self.spheres.append(("black", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(16, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.2,
                                            noforces=True))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.3, False,
                                                          rb=self.srbs[-1],
                                                          damage=3, hl=0,
                                                          blackHole=True))
            self.srbs[-1].disable()
            self.srbs[-1].colliders[0].onHit = lambda x: self.explode(x)

            self.w.addRB(self.srbs[-1])

            ps = ContinuousParticleSystem(np.array([0,0,0.]), (0,pi/2),
                                          vel=0.0, randVel=0.01,
                                          nParticles=2400,
                                          randPos=0.2,
                                          lifespan=400,
                                          size=0.3, opacity=0.7,
                                          color=(0,0,0), randColor=0)
            self.addParticleSystem(ps)

            self.blackHoles.append({"rb":self.srbs[-1], "ps":ps})

        if self.stage == 0:
            self.addVertObject(VertWater, [-1, 2, -10], size=240,
                           scale=0.22, pScale=0.04,
                 wDir=[(0.4,-0.17), (0.4, 0.2)],
                 wLen=[(10, 4, 3), (7, 5, 2)],
                 wAmp=np.array([(0.8, 0.5, 0.3), (0.6, 0.35, 0.25)])*1.6,
                 wSpd=np.array([(0.6, 0.8, 1.1), (1, 1.1, 1.3)])*1.8, numW=3,
                           texture=PATH+"../Assets/Blue.png",
                           useShaders={'shader':"SSR"})
            self.water = self.vertObjects[-1]

        for i in range(len(self.players)):
            ps = ContinuousParticleSystem(np.array([0,0,0.]), (0,pi/2),
                                          vel=0.03, randVel=0.01,
                                          nParticles=2400,
                                          randPos=0.2,
                                          lifespan=1200,
                                          size=0.2, opacity=0.6,
                                          color=(0,0,0), randColor=0)
            self.addParticleSystem(ps)
            self.players[i]["ghost"] = ps

        self.exploders = []
        self.expLights = {}
        for i in range(self.numBullets // 3):
            p = np.array([0., 0, 0])
            self.addVertObject(VertSphere, p, n=24, scale=0.25,
                               texture=PATH+"../Assets/Orange1.png",
                               useShaders={'shader':"add", 'args':{'emPow':2.}})
            self.exploders.append({"pos":p, "active":False,
                                   "scale":1, "obj":self.vertObjects[-1]})

        # (Min xz, Max xz)
        bd = [(-10, 50), (-10, 50), (-25, 50),
              (0, 35), (-35, 60), (-20, 50)]
        ss = [b[1] - b[0] for b in bd]
        self.BORDER = np.array(bd[self.stage], "float")
        self.stageSize = ss[self.stage]

        if self.stage != 1:
            b1, b2 = self.BORDER
            ss = self.stageSize
            c = [(b1, 0, b1), (b1, 0, b1), (b2, 0, b1), (b1, 0, b2)]
            h = [(ss, 0, 0), (0, 0, ss), (0, 0, ss), (ss, 0, 0)]
            for i in range(4):
                self.addVertObject(VertPlane, np.array(c[i]) - np.array([0,2,0]),
                                   n=15, h1=h[i], h2=[0, 22, 0],
                                   texture=PATH+"../Assets/Magenta.png",
                                   useShaders={'shader':"border"})

        try: self.STAGECONFIG.setupPostprocess(self)
        except AttributeError: pass

        sr = self.shRes
        fact = (1,1,1,0.9,0.5,1)[self.stage]
        self.shadowCams.append({"pos":[40, 5, 40], "dir":[pi/2, 1.1],
                                "size":sr, "scale":24*sr/2048 * fact})
        self.shadowCams.append({"pos":[40, 5, 40], "dir":[pi/2, 1.1],
                                "size":sr, "scale":200*sr/2048})

        print('Textures in', time.time() - self.loadStart)
        self.makeObjects(1)

        self.si.put({"Fade":{'Time':0, 'Tracks':{PATH + "../Sound/Noise.flac",
                                                 PATH + '../Sound/Plains3v4.wav',
                                                 PATH + '../Sound/Env_Plains_R.wav'
        }}})


        print("Make in", time.time() - self.loadStart)

    def postProcess(self):
        self.draw.applyDoF()

        try: self.draw.applyLens(self.draw.lensTn)
        except AttributeError: pass

        if self.doSSAO:
            self.draw.ssao()

        if self.frameNum > 1:
            if self.doMB:
                self.draw.motionBlur(self.oldVPos, self.oldVMat)

        db = self.draw.getDB()
        target = max(0.6, min(6, db[self.draw.H//2, self.draw.W//2]))
        df = self.dofFoc
        if (target < self.dofFoc) or (self.frameNum & 1 == 0):
            self.dofFoc = sqrt(sqrt(df * df * df * target))

        ap = 0.7 / np.tan(self.fovX*pi/360)
        ap *= self.W / 752
        ap *= self.apFac

        self.draw.dof(self.dofFoc, aperture=8*ap if self.cam1P else 12*ap)
        if self.doBloom:
            self.draw.blur(self.exposure * 0.707)

        self.oldVMat = np.array(self.vMat)
        self.oldVPos = np.array(self.pos)

        for i in range(len(self.blackHoles)):
            b = self.blackHoles[i]
            if "dstrength" in b and b["dstrength"] > 0:
                tr = (b["lastPos"] - self.pos) @ self.vMat.T
                if tr[0] < 0: continue
                sc = (self.scale * self.H//2) / tr[0]
                bx = -tr[1] * sc + self.W//2
                by = tr[2] * sc + self.H//2
                portal = 0.3 * sc
                strength = (self.H / 400) * 300 * b["dstrength"] / tr[0]
                self.draw.distort(bx/self.W, by/self.H, tr[0],
                                  portal, strength)

        self.draw.gamma(self.exposure, self.tonemap, self.blackPoint, self.useFxaa)

    def fireSnd(self, color):
        snd = {"blank":("A",4), "orange":("B",3), "red":("C",4), "black":("D",2.5)}
        self.si.put({"Play":(PATH+"../Sound/Fire" + snd[color][0] + ".wav",
                             self.volmFX / 2 / snd[color][1])})

    def fireAnim(self, color, sc=None, vh=None):
        if sc is None:
            sc = self.selchar
        a = self.players[sc]
        if vh is not None: a['vh'] = vh
        if a['frameFired'] > 0: return True
        a['frameFired'] = self.frameNum
        a['fireColor'] = color
        a['fireVH'] = vh
        return a["Energy"] >= self.COSTS[color]

    def fire(self, color, sc=None, vh=None, throw=False):
        if sc is None:
            sc = self.selchar
        if vh is None:
            vh = self.vv[1]
        a = self.players[sc]

        if a["Energy"] < self.COSTS[color]: return
        a["Energy"] -= self.COSTS[color]

        cb = None
        for i in range(len(self.srbs)):
            if self.srbs[i].disabled and self.spheres[i][0] == color:
                cb = i
                break
        if cb is None:
            a["Energy"] += self.COSTS[color]
            return False

        self.srbs[cb].enable()
        s = self.bulletSpeed
        if color == "black": s *= 0.66
        d = np.array([cos(a["cr"]), vh, sin(a["cr"])])
        self.srbs[cb].v = d*s
        self.srbs[cb].pos = np.array(a["b1"].offset[:3]) + 0.8*(d*np.array([1,0,1]))
        self.srbs[cb].pos[1] += int(throw)

        snd = {"blank":("A",2), "orange":("B",1.5), "red":("C",2), "black":("D",1.5)}

        self.si.put({"Play":(PATH+"../Sound/Fire" + snd[color][0] + ".wav",
                             self.volmFX / snd[color][1], (a["b1"].offset[:3], 2.7, 1))})

        if sc == self.selchar and color == 'blank':
            self.frameFired = color

        return color

    def onStart(self):
        self.gameStarted = False

        if self.stage == 4:
            self.si.put({'Play':(PATH+'../Sound/NoiseOpen.flac', self.volmFX * 0.9, True)})
        elif self.stage == 5:
            pass
        elif self.isClient:
            snd = self.ENVTRACKS
            self.si.put({"Play":(PATH+"../Sound/" + snd[self.stage], self.volm * 0.8, True)})
            self.gameStarted = True

        self.qi.put(True)
        if 'isEqui' in self.matShaders[self.skyBox.texNum]['args']:
            self.cubeMap = CubeMap(self.skyTex, None, False)
        else:
            self.cubeMap = CubeMap(self.skyTex, 2, False)
        a = self.cubeMap.texture.reshape((-1, 3))
        self.draw.setReflTex("1a", a[:,0], a[:,1], a[:,2], self.cubeMap.m)
        self.draw.setReflTex("0", a[:,0], a[:,1], a[:,2], self.cubeMap.m)
        self.draw.setHostSkyTex(self.cubeMap.rawtexture)

        p = PATH+"../Poses/"
        if self.stage == 2:
            self.poses = Anim.loadAnim(p+'Ski4.ava', timeScale=0.9)
            self.transStartKF = 5
        else:
            self.poses = Anim.loadAnim(p+'WalkCycle8.ava', timeScale=0.9)
            self.transStartKF = 2

        self.keyFrames = self.poses
        self.idle = json.load(open(p+"Idle1.pose"))
        self.idleFlat = Anim.flattenPose(self.idle)

        self.idleTest = Anim.loadAnim(p+'IdleTest.ava')
        self.gestures.append(Anim.flattenPose(self.idleTest[0][1]))

        self.idlingTest = Anim.loadAnim(p+'IdlingTest6.ava')
        for i in range(len(self.idlingTest)):
            self.idlingTest[i] = (self.idlingTest[i][0] * 1.6,
                                  self.idlingTest[i][1],
                                  self.idlingTest[i][2] * 0.6,
                                  self.idlingTest[i][3])

        self.throwKF = Anim.loadAnim(PATH+'../Poses/Throw.ava')
        for i in range(len(self.throwKF)):
            self.throwKF[i] = (self.throwKF[i][0],
                               self.throwKF[i][1]['children'][0],
                               self.throwKF[i][2])

        self.restPlayer = None
        self.lastRestPlayer = None

        space = 2 if self.stage == 3 else 3
        xpos = (28, 28, 28, 28, -20, 10)[self.stage]

        for n in range(len(self.players)):
            a = self.players[n]
            ctexn = []
            c = a["obj"]
            ctexn.append(c.texNum)
            while c.nextMtl is not None:
                c = c.nextMtl
                ctexn.append(c.texNum)
            a["ctexn"] = ctexn

            self.draw.initBoneTransforms(a["num"], len(a["allBones"]))

            for b in range(len(a["allBones"])):
                for i in a["ctexn"]:
                    self.draw.initBoneOrigin(a["allBones"][b].origin, b, i)

            a['b1'].lastOffset = np.array((0,0,0), 'float32')

            a["b1"].offset = np.array((xpos, 0, 15 + space*n, 1.))
            a["b1"].offset[1] = self.terrain.getHeight(a["b1"].offset[0],
                                                       a["b1"].offset[2]) + 1.6
            a["rig"].importPose(self.idle, updateRoot=False)
            self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])

        self.shadowObjects()
        self.setupShadowCams()
        self.rotateLight()
        self.simpleShaderVert()
        self.shadowChar()

        self.w.start()

        if not self.isClient:
            self.setupAI(self.aiNums)
            host = self.remoteServer
            TO = {"timeout":1, "headers":{"User-Agent":"AXICombat/1.x"}}
            for x in self.aiNums:
                p = {"gd":self.gameId, "pname":"CPU " + str(x), "char":x}
                try:
                    requests.post(host + "/SelChar", data=p, **TO)
                except: pass

        self.draw.noisePos = np.zeros((3,), 'float32')

        mpath = PATH + '../Models/'
        self.addNrmMap(mpath + 'L3/Atlas1Nrm.png', 'Link')
        self.addNrmMap(mpath + 'L3/L3H_nrm.png', 'L3H')
        self.addNrmMap(mpath + 'Zelda2/Atlas1Nrm.png', 'Zelda')
        self.addNrmMap(mpath + 'Zelda2/Z2H_nrm.png', 'Z2H')
        self.addNrmMap(mpath + 'Body/HairNorm.png', 'Hair', mip=True, mipLvl=4)
        self.addNrmMap(mpath + 'Body/Face3xNrm.png', 'Face', mip=True)
        self.addNrmMap(mpath + 'Body/T_Skin_F_C_Body_NRM.png', 'Body', mip=True)
##        self.addNrmMap(mpath + 'Body/FrontTrimN1.png', 'Bracelet', mip=True)
        self.addNrmMap(mpath + 'Body/Fabric_Lace_017_normal.png', 'ClothTrim', mip=True)
        self.addNrmMap(mpath + 'Body/Fabric040_1K_NormalGL.png', 'Clothes', mip=True, mipLvl=4)

    def shadowChar(self):
        sc = self.shadowCams[1]
        sc["dir"] = self.directionalLights[0]["dir"]
        sc["pos"] = -20 * viewVec(*sc["dir"]) + np.array(self.players[self.selchar]["b1"].offset)[:3]
        self.updateShadowCam(1)
        self.shadowMap(1, self.shadowObjects2(), bias=0.02 * 2048/self.shRes)

    def shadowObjects2(self):
        if self.renderMask is None:
            sobj = np.full((len(self.vertU),), False)
        else:
            sobj = [(x <= self.players[-1]["obj"].texNum) and \
                    not self.renderMask[x] and \
                    not ('nocast' in self.matShaders[x]) and \
                    not (self.matShaders[x]['shader'] == 'sub') or \
                    'shadowDynamic' in self.matShaders[x] \
                    for x in range(len(self.renderMask))]
            sobj[self.vtNames[PATH+"../Assets/Blank.png"]] = True
            sobj[self.vtNames[PATH+"../Assets/Red.png"]] = True
            if self.stage == 2:
                sobj[self.skis[0].texNum] = True
                sobj[self.poles[0].texNum] = True
        return sobj

    def sendState(self):
        dat = {}
        for i in self.actPlayers:
            a = self.players[i]
            dat[a["num"]] = {
                "r1": np.round(a["b1"].offset[:3] - a['animOffset'], 3).tolist(),
                "m1": int(a["moving"]),
                "c1": a["cr"], 'c2': a['cv'],
                'throwAnim': a['throwAnim'],
                'fireColor': a['fireColor'],
                "hc": [c.hc for c in a["pv"].colliders],
                "ee": a["Energy"],
                "gg": a["gestNum"], "gi": a["gestId"],
                "jp": a["jump"],
                #"hf": a["isHit"]
                'vh': a['vh']
                }
            if 'vr' in a:
                dat[a['num']]['vr'] = float(a['cheight'])
            if 'vrC' in a:
                dat[a['num']]['vrC'] = a['vrC']
        dat[self.selchar]['vh'] = float(self.vv[1])
        dat[self.selchar]['fCam'] = self.fCam

        sp = [{"pos":np.round(self.srbs[i].pos, 3).tolist(),
               "vel":np.round(self.srbs[i].v, 3).tolist(),
               "dis":self.srbs[i].disabled}
              for i in range(len(self.spheres))]
        act = dict(self.activePlayers)
        act[self.uname] = self.selchar

        exp = [{"on":x["active"], "pos":np.round(x["pos"], 3).tolist(),
                "sc":round(x["scale"], 2)} for x in self.exploders]

        pp = self.pickups[0]["pos"]
        if pp is not None: pp = np.round(pp, 2).tolist()
        pick = {"p":pp, "t":self.pickups[0]["t"]}

        adat = {"players":dat, "sp":sp, "act":act, "exp":exp, "pu":pick,
                "time":self.frameNum, "rl":round(self.directionalLights[0]["dir"][1], 2),
                'restPlayer':self.restPlayer}
        if self.frameFired: adat["ff"] = self.frameFired

        try: adat['trans'] = self.transStart
        except: pass

        adat['STAGEFLAGS'] = self.stageFlags

        try:
            self.qi.put_nowait(bytes(json.dumps(adat), "ascii"))
        except queue.Full: pass
        except: raise

    def sendPlayer(self):
        dat = {}
        a = self.players[self.selchar]
        dat[a["num"]] = {
            "r1": np.round(a["b1"].offset[:3] - a['animOffset'], 3).tolist(),
            "m1": a["moving"],
            "c1": a["cr"], 'c2': a['cv'],
            "fire": self.frameFired,
            "fire2": self.frameFiredOld,
            'throwAnim': a['throwAnim'],
            'fireColor': a['fireColor'],
            "vh": float(self.vv[1]),
            "gg": a["gestNum"], "gi": a["gestId"],
            "jp": a["jump"],
            'fCam': self.fCam
            }
        if self.VRMode:
            dat[a['num']]['vr'] = float(a['cheight'])
            if 'vrC' in a:
                dat[a['num']]['vrC'] = a['vrC']

        adat = {"players":dat, "time":self.frameNum,
                'restPlayer':self.restPlayer}

        try:
            self.qi.put_nowait(bytes(json.dumps(adat), "ascii"))
        except queue.Full: pass
        except: raise

    def recvState(self):
        while not self.qo.empty():
            try:
                a = self.qo.get_nowait()
                if len(a[1]) == 0: continue
                try: b = json.loads(a[1])
                except:
                    print(a[1])
                    raise
                k = b["players"]
                if self.isClient:
                    try:
                        self.activePlayers = b["act"]
                    except KeyError:
                        print("Username conflict!")
                        return

                    if "Host" in self.lastTimes:
                        if self.lastTimes["Host"] == int(b["time"]):
                            continue
                    self.lastTimes["Host"] = int(b["time"])

                else:
                    if a[0] in self.lastTimes:
                        if self.lastTimes[a[0]] == int(b["time"]):
                            continue

                    self.activePlayers[a[0]] = list(k.keys())[0]
                    self.lastTimes[a[0]] = int(b["time"])

                for pn in k:
                    pM = int(pn)
                    sc = self.players[pM]
                    a = k[pn]
                    if "hc" in a:
                        for i in range(len(a["hc"])):
                            sc["pv"].colliders[i].hc = a["hc"][i]
                    if pM == self.selchar: continue
                    sc["b1"].offset[:3] = a["r1"][:3]
                    sc["moving"] = a["m1"]
                    sc["cr"] = a["c1"]
                    sc['cv'] = a['c2']
                    if 'vh' in a: sc['vh'] = a['vh']
                    if 'fCam' in a: sc['fCam'] = a['fCam']
                    if "ee" in a: sc["Energy"] = a["ee"]
                    if "fire" in a:
                        if a["fire"]:
                            self.fire(a["fire"], pM, a["vh"])
                    if "fire2" in a:
                        if a["fire2"]:
                            self.fire(a["fire2"], pM, a["vh"])

                    if 'throwAnim' in a: # IMPLIES 'fireColor' in a
                        #print(pn, a['throwAnim'])
                        if a['throwAnim'] and not sc['throwAnim']:
                            sc['throwAnim'] = a['throwAnim']
                            sc['fireColor'] = a['fireColor']
                            sc['animFired'] = False
                            sc['fireVH'] = a['vh']
                            sc['poseThrow'] = self.throwKF[0][0]

                    if a["gg"] is not None:
                        if self.players[pM]["gestNum"] != a["gg"]:
                            if self.players[pM]["gestId"] != a["gi"]:
                                self.gesture(pM, a["gg"], a["gi"])

                    if a["jp"] > 0:
                        if self.players[pM]["jump"] < 0:
                            if a["jp"] != -self.players[pM]["jump"]:
                                self.jump(pM)

                    if 'vr' in a:
                        self.players[pM]['vr'] = a['vr']
                        self.players[pM]['cheight'] = a['vr']
                        if 'vrC' in a:
                            self.players[pM]['vrC'] = a['vrC']

                    #if "hf" in a:
                    #    self.players[int(pn)]["isHit"] = a["hf"]
                if "sp" in b:
                    for x in range(len(b["sp"])):
                        self.srbs[x].pos = np.array(b["sp"][x]["pos"])
                        self.srbs[x].v = np.array(b["sp"][x]["vel"])
                        self.srbs[x].disabled = b["sp"][x]["dis"]
                if "exp" in b:
                    for x in range(len(b["exp"])):
                        cx = b["exp"][x]
                        if cx["on"] and not self.exploders[x]["active"]:
                            if cx["sc"] < 10:
                                vpos = np.array(cx["pos"])
                                self.explode(vpos, force=True, eNum=x)
                if "pu" in b:
                    p = b["pu"]
                    if p["p"] is not None:
                        if self.pickups[0]["pos"] is None:
                            self.plantPickup(np.array(p["p"]), p["t"])
                    else:
                        if self.pickups[0]["pos"] is not None:
                            self.resetPickup()
                if "ff" in b:
                    self.fireSnd(b["ff"])
                if "rl" in b:
                    if self.directionalLights[0]["dir"][1] != b["rl"]:
                        self.rotateLight(b["rl"])
                if 'restPlayer' in b:
                    if b['restPlayer'] is not None and self.restPlayer is None:
                        if b['restPlayer'] != self.lastRestPlayer:
                            self.respawnTest(b['restPlayer'])

                if 'trans' in b:
                    try:
                        if self.transSync != b['trans']:
                            self.lightTest()
                            self.transSync = b['trans']
                    except AttributeError:
                        self.lightTest()
                        self.transSync = b['trans']

                if 'STAGEFLAGS' in b:
                    self.stageFlags = b['STAGEFLAGS']

            except queue.Empty: pass
            except KeyError:
                raise #print("Game has already finished!")
            except: raise

    def getHealth(self, pn):
        dmg = sum([a.hc for a in self.players[pn]["pv"].colliders]) / self.maxHP
        return 1-dmg

    def plantPickup(self, pos, t=None):
        i = self.pickups[0]
        if t is not None:
            if i["t"] == t: return
        if t is None: t = self.frameNum

        cs, ce, tn = i["obj"].cStart*3, i["obj"].cEnd*3, i["obj"].texNum
        self.draw.translate(pos, cs, ce, tn)
        i["pos"] = pos; i["t"] = t

        self.si.put({"Play":(PATH+"../Sound/Pickup.wav",
                             self.volmFX / 3, (i["pos"], 4, 1))})

        if 'ps' in i:
            i['ps'].reset()
            i['ps'].changePos(pos)
            i['ps'].opacity = 0.3
            return

        ps = ContinuousParticleSystem(pos, (0,-pi/2),
                                      vel=0.02, randVel=0.0,
                                      nParticles=40,
                                      randPos=0.25,
                                      lifespan=1200,
                                      size=0.15, opacity=0.3,
                                      color=(0.08,0.4,0.06), randColor=0,
                                      circular=True)
        self.addParticleSystem(ps)
        i['ps'] = ps
        i['ps'].shader = 2

    def resetPickup(self):
        i = self.pickups[0]
        cs, ce, tn = i["obj"].cStart*3, i["obj"].cEnd*3, i["obj"].texNum
        self.draw.translate(-i["pos"], cs, ce, tn)
        i["pos"] = None
        i['t'] = -self.frameNum

    def qq(self): self.doQuit = True


    def frameUpdate(self):
        self.frameStart = time.perf_counter()
        self.frameProfile('.')

        try:
            self.STAGECONFIG.frameUpdate(self)
        except AttributeError:
            pass
        self.frameProfile('Stage')

        self.si.put({'SetPos':{'pos':self.pos,
                               'vvh':self.vVhorz()}})

        if self.VRMode: self.frameUpdateVR()

        vf = 1

        if self.frameNum == 0:
            self.waitFinished = False
            self.statTime = time.time()
        if self.frameNum == 1:
            self.rotateLight()


        CURRTIME = time.time()

        sc = self.selchar

        rm = [x <= self.players[-1]["obj"].texNum for x in range(len(self.vtNames))]
        actPlayers = {self.selchar}

        for pn in self.activePlayers:
            plNum = int(self.activePlayers[pn])
            actPlayers.add(plNum)

            for x in self.players[plNum]["ctexn"]:
                rm[x] = False

        self.actPlayers = actPlayers

        for x in self.players[self.selchar]["ctexn"]:
            rm[x] = False

        ic = self.isClient

        endText = [("WIN", (60, 220, 120, 255)),
                   ("LOSE", (220, 60, 80, 255)),
                   ("DRAW", (128, 192, 255, 255))]

        if len(actPlayers) > 1:
            if not self.gameStarted and self.stage < 4:
                snd = self.ENVTRACKS
                self.si.put({"Play":(PATH+"../Sound/" + snd[self.stage], self.volm * 0.8, True)})
                self.gameStarted = True

            alive = 0
            for pn in actPlayers:
                alive += self.getHealth(pn) > 0

            if alive <= 1:
                try: f = self.endTime
                except:
                    self.endTime = time.time()
                    snd = self.ENVTRACKS
                    self.si.put({'Loop':{'Track':PATH+"../Sound/" + snd[self.stage],
                                         'loop': False}})
                if (time.time() - self.endTime) > 16:
                    self.uInfo["Quit"] = "Press R to return to menu"
                    if not self.waitFinished:
                        self.bindKey("r", self.qq)
                        self.waitFinished = True
            if alive == 1:
                c = self.getHealth(self.selchar)
                if c > 0:
                    self.WIN = True
                    self.uInfo["End"] = endText[0]
                else: self.uInfo["End"] = endText[1]
            elif alive == 0: self.uInfo["End"] = endText[2]

        self.testRest()

        self.renderMask = self.testRM(rm)
        if SHOWALL:
            self.renderMask = [False for x in range(len(self.vtNames))]
            actPlayers = list(range(len(self.players)))


        hvel = self.hvel
        maxSlope = 1
        maxStep = 0.4


        if self.frameNum == 0:
            self.dt1 = time.perf_counter()
            self.lp = np.zeros((len(self.spheres), 6, 3), 'float')
            for i in range(len(self.spheres)):
                self.lp[i] = self.srbs[i].pos
            self.lpCount = np.zeros((len(self.spheres),), 'int')

        self.dt2 = time.perf_counter()

        self.frameTime = self.dt2 - self.dt1

        self.dt1 = time.perf_counter()

        if self.frameNum & vf == 0:
            if self.isClient:
                self.sendPlayer()
            else:
                self.sendState()
            self.recvState()


        if self.frameNum & vf == 1:
            if not self.isClient:
                self.updateAI()

        self.frameProfile('AI')

        self.frameFiredOld = self.frameFired
        self.frameFired = False

        if self.stage == 0 or self.stage == 4:
            self.water.update()


        for a in self.players:
            if a["Energy"] > 0.95:
                if self.getHealth(a["id"]) < 0.95:
                    a["pv"].colliders[0].hc -= 0.01

            tn = a["id"]
            if self.getHealth(tn) <= 0:
                if "deathTime" not in a:
                    a["deathTime"] = time.time()
                    for xn in a["ctexn"]:
                        self.matShaders[xn] = {'temp': self.matShaders[xn]}
                a["pv"].pos[:] = -10.
                a['pv'].disable()
                a["Energy"] = 0
                tr = 0.6 + 0.32 * min(40, (time.time() - a["deathTime"])*10) / 40
                for xn in a["ctexn"]:
                    self.matShaders[xn]['shader'] = "sub"
                    self.matShaders[xn]['args'] = {'emPow':tr}
                g = a["ghost"]
                if (not self.VRMode) or (self.frameNum & 1):
                    g.changePos(a["b1"].offset[:3])
                    g.step()
            elif tn not in actPlayers:
                a["pv"].pos[:] = -10.
                a['pv'].disable()
            else:
                a['pv'].enable()
                a["pv"].pos = a["b1"].offset[:3] + np.array([0,-0.5,0]) \
                              - a['animOffset'] + np.array([0,a['legIKoffset'],0])
                a["Energy"] += 0.05 * self.frameTime
                a["Energy"] = min(1, a["Energy"])

        self.frameProfile('Ghost/Energy')

        impulses = self.w.stepWorld(self.frameTime,
                                    checkColl=(self.frameNum & vf == 0))

        self.frameProfile('StepWorld')

        for i in range(min(len(impulses), 4)):
            im = impulses[i]
            idir = im[0]
            ipos = im[1]

            for fxobj in self.impulseFX:
                if fxobj.timeStart < 0:
                    break
            if fxobj.timeStart > 0:
                break

            objArgs = (fxobj.cStart*3, fxobj.cEnd*3, fxobj.texNum)

            norm = np.cross(idir, (1,1,1))
            norm /= Phys.eucLen(norm)
            binorm = np.cross(idir, norm)
            binorm /= Phys.eucLen(binorm)
            rot = np.array([norm, idir, binorm])

            self.draw.rotate(rot, *objArgs)
            self.draw.translate(ipos, *objArgs)
            fxobj.prevCoord = ipos
            fxobj.prevRot = rot
            fxobj.timeStart = CURRTIME

        for fxobj in self.impulseFX:
            if fxobj.timeStart > 0:
                objArgs = (fxobj.cStart*3, fxobj.cEnd*3, fxobj.texNum)

                ctime = CURRTIME - fxobj.timeStart
                life = 0.3

                self.matShaders[fxobj.texNum]['add'] = 0.5 - 0.5*sqrt(ctime/life)
                cscale = 0.1 + sqrt(ctime/life)
                self.draw.scale(fxobj.prevCoord, cscale / fxobj.scale, *objArgs)
                fxobj.scale = cscale
                if ctime > life:
                    self.draw.translate(-fxobj.prevCoord, *objArgs)
                    self.draw.rotate(np.transpose(fxobj.prevRot), *objArgs)
                    fxobj.prevCoord[:] = 0
                    fxobj.prevRot[:] = np.identity(3)
                    fxobj.timeStart = -1


        for a in self.players:
            if self.getHealth(a['id']) <= 0:
                continue
            if a['id'] not in self.actPlayers:
                continue
            if a['jump'] > 0:
                a["b1"].offset[:3] = a["pv"].pos + np.array([0,0.5,0]) \
                                     + a['animOffset'] - np.array([0,a['legIKoffset'],0])
                try:
                    if a['pv'].colDir[1] < -0.2:
                        a['jump'] = -a['jump']
                        self.setYOffset(a)
                except AttributeError:
                    pass
            try: del a['pv'].colDir
            except: pass

        self.frameProfile('Physics')

        dmg = sum([a.hc for a in self.players[sc]["pv"].colliders]) / self.maxHP
        self.uInfo["Health"] = max(0, 1-dmg)
        self.uInfo["Energy"] = self.players[sc]["Energy"]

        if (self.frameNum & 7 == 0):
            for i in range(len(self.srbs)):
                if (np.isnan(self.srbs[i].pos)).any(): pass
                elif ((self.srbs[i].pos > self.BORDER[1]) | \
                      (self.srbs[i].pos < self.BORDER[0])).any():
                    self.srbs[i].pos[:] = 0.
                    self.srbs[i].v[:] = 0.
                    self.srbs[i].disable()


        batch = {}
        for i in range(len(self.spheres)):
            s = self.spheres[i][1]
            lpi = self.lp[i]
            if (np.isnan(self.srbs[i].pos)).any():
                print("NaN, disable")
                self.srbs[i].pos[:] = 0.
                self.srbs[i].v[:] = 0.
                self.srbs[i].disable()
            diff = self.srbs[i].pos - lpi[self.lpCount[i]]
            if sum(diff*diff) > 0:
                if s.texNum not in batch:
                    batch[s.texNum] = []
                batch[s.texNum].append((diff, s.cStart*3, s.cEnd*3))

            if self.spheres[i][0] == 'blank':
                # 015 is one side of rect, 234 is other side
                s = self.sphereTrails[i]
                if s.texNum not in batch:
                    batch[s.texNum] = []

                if self.srbs[i].disabled or sum(lpi[self.lpCount[i]]) == 0:
                    lpi[self.lpCount[i]-4] = self.srbs[i].pos
                    lpi[self.lpCount[i]-3] = self.srbs[i].pos
                    lpi[self.lpCount[i]-2] = self.srbs[i].pos
                    lpi[self.lpCount[i]-1] = self.srbs[i].pos
                    lpi[self.lpCount[i]] = self.srbs[i].pos

                diff2 = lpi[self.lpCount[i]-4] - lpi[self.lpCount[i]-5]
                batch[s.texNum].append((diff, s.cStart*3, s.cStart*3+2))
                batch[s.texNum].append((diff2, s.cStart*3+2, s.cStart*3+5))
                batch[s.texNum].append((diff, s.cStart*3+5, s.cStart*3+6))

            self.lpCount[i] += 1
            self.lpCount[i] %= self.lp.shape[1]
            lpi[self.lpCount[i]] = np.array(self.srbs[i].pos)

        self.frameProfile('Batch')

        self.draw.translateBatch(batch)

        self.frameProfile('Translate')

        for i in range(len(self.exploders)):
            e = self.exploders[i]
            if e["active"]:
                for a in self.players:
                    if a["id"] not in actPlayers: continue
                    if sum((a["b1"].offset[:3] - e["pos"]) ** 2) < (e["scale"] ** 2 / 4):
                        a["pv"].colliders[0].hc += self.expPow / max(4, e["scale"]) * (self.frameTime * 20)
                        a["isHit"] = self.frameNum

                frameScale = self.exscale ** (time.time() - e["start"])

                cs, ce, tn = e["obj"].cStart*3, e["obj"].cEnd*3, e["obj"].texNum
                self.draw.scale(e["pos"], frameScale / e["scale"], cs, ce, tn)
                e["scale"] *= frameScale / e["scale"]
                self.matShaders[tn].update(args={'emPow': 2 / e["scale"]})

                self.expLights[i] = {"pos": e["pos"], "i":np.array((40,40,10.)) / e["scale"]}
                if e["scale"] > 30:
                    e["active"] = False
                    del self.expLights[i]
                    self.draw.scale(e["pos"], 1 / e["scale"], cs, ce, tn)
                    e["scale"] = 1
                    self.draw.translate(-e["pos"], cs, ce, tn)
                    e["pos"][:] = 0.


        self.pointLights = self.envPointLights + list(self.expLights.values())

        for i in range(len(self.blackHoles)):
            b = self.blackHoles[i]
            if b["rb"].disabled:
                self.w.delAttractor(i)
                try:
                    lf = b["lastFrame"]
                    if self.frameNum - lf > 20:
                        if b["ps"].started:
                            b["ps"].reset()
                            b["dstrength"] = -1
                            del b["lastFrame"]
                    else:
                        b["ps"].step()
                        b["dstrength"] = 1 - (self.frameNum - lf) / 20
                        ls = -5 * b["dstrength"]
                        self.pointLights.append({"i":(ls,ls,ls),
                                                 "pos":b["lastPos"]})
                except KeyError:
                    if b["ps"].started:
                        b["lastFrame"] = self.frameNum
                        self.pointLights.append({"i":(-5,-5,-5),
                                                 "pos":b["lastPos"]})
            else:
                b["dstrength"] = 1
                b["lastPos"] = np.array(b["rb"].pos)
                self.w.setAttractor(i, np.array(b["rb"].pos), 90)
                b["ps"].changePos(b["rb"].pos)
                b["ps"].step()
                self.pointLights.append({"i":(-5,-5,-5), "pos":b["rb"].pos})

        self.frameProfile('BlackHoles')

        if not self.isClient:
            if int(self.dt1) & 31 == 0:
                for i in self.pickups:
                    if i["pos"] is None:
                        xy = self.BORDER[0]+5 + nr.rand(2)*(self.stageSize-10)
                        plant = True
                        if self.stage == 1:
                            if self.terrain.getHeight(*xy) > 2:
                                continue
                        for a in self.players:
                            dist = np.sum(np.abs(xy - a["b1"].offset[::2]))
                            if dist < 5: plant = False
                        if plant:
                            newpos = np.array((xy[0], self.terrain.getHeight(*xy) + 0.8, xy[1]))
                            self.plantPickup(newpos)

        for i in self.pickups:
            if i["pos"] is not None:
                self.pointLights.append({"i":(0,4.,0), "pos":i["pos"]})
                i['ps'].step()
                for a in self.players:
                    if a["id"] not in actPlayers: continue
                    if np.sum(np.abs(i["pos"] - a["b1"].offset[:3])) < 2:
                        a["Energy"] += 0.2
                        a["Energy"] = min(1, a["Energy"])
                        self.resetPickup()
                        break
            if i['t'] < 0:
                try:
                    i['ps'].opacity *= 0.9
                    if self.frameNum + i['t'] > 40:
                        i['ps'].reset()
                        i['t'] = 0
                except: pass

        self.frameProfile('Pickup')

        p = self.players[sc]
        if self.cam1P and self.VRMode and self.frameNum > 1:
            p['cr'] = atan2(self.vv[2], self.vv[0])
            p['b1'].offset[:3] += self.VRpos - self.oldVRpos
            p['cheight'] += self.VRpos[1] - self.oldVRpos[1]
            p['vr'] = p['cheight']

        if "nameTag" in self.uInfo: del self.uInfo["nameTag"]
        for a in self.players:
            if a["id"] not in actPlayers: continue

            a['pv'].noforces = (a['jump'] < 0)

            if a["jump"] > 0:
                ih = self.STAGECONFIG.getHeight(self, a["b1"].offset[:3] - a['animOffset'][:3])
                if (ih + a["cheight"]) > a["b1"].offset[1]:
                    # stuck on side of terrain
                    vx,vy = a['pv'].v[::2]
                    if vx*vx+vy*vy > 0.0001:
                        a['b1'].offset[::2] -= a['pv'].v[::2] * self.frameTime

                ih = self.STAGECONFIG.getHeight(self, a["b1"].offset[:3] - a['animOffset'][:3])
                if (ih + a["cheight"]) > a["b1"].offset[1]:
                    # landed on terrain
                    a["jump"] = -a["jump"]
                    self.setYoffset(a)

                    self.si.put({"Play":(PATH+"../Sound/New/Quiver.wav",
                                         abs(a['pv'].v[1]) / 8 * self.volmFX / 3,
                                         (a['b1'].offset[:3], 6, 1))})

                    if abs(a["pv"].v[1]) > 8:
                        a["pv"].colliders[0].hc += abs(abs(a["pv"].v[1]) - 6)
                        a["isHit"] = self.frameNum

                    a['pv'].forces[0,1] = 0
                    a['pv'].v[:] = 0


            a['pv'].v[::2] *= 1 - 0.04 * Phys.eucLen(a['pv'].v) * self.frameTime
            print(np.round(a['pv'].v, 2), end='\r')

            if Phys.eucLen(a['pv'].v) < 0.01:
                a['pv'].v *= 0

            if a["gesturing"]:
                a["moving"] = 0
                self.stepGest(a, a["obj"], self.frameTime * self.poseDt)

            if a["moving"]:
                transKF = self.transStartKF if a['moving'] > 0 else 4
                if not a['movingOld']:
                    a['animTrans'] = CURRTIME
                    a['poset'] = self.keyFrames[transKF][0]
                    a['tempPose'] = a['rig'].exportPoseFlat()

                bx = hvel*a["moving"]*cos(a["cr"])
                by = hvel*a["moving"]*sin(a["cr"])
                if a["fCam"]:
                    bx += hvel/3 * cos(a["cr"] + pi/2) * a["cv"]
                    by += hvel/3 * sin(a["cr"] + pi/2) * a["cv"]

                    d = sqrt(bx*bx + by*by) / hvel
                    bx /= d; by /= d

                if a['moving'] < 0:
                    bx *= 0.9; by *= 0.9

                jbx = bx; jby = by
                bx *= self.frameTime; by *= self.frameTime

                if CURRTIME - a['animTrans'] < 0.2:
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    bx *= fact; by *= fact

                ax, ay = a["b1"].offset[::2] - a['animOffset'][::2]
                ih = self.STAGECONFIG.getHeight(self,
                        np.array([ax + bx, a['b1'].offset[1], ay + by])) + a["cheight"]

                navheight = a["b1"].offset[1] + a['legIKoffset']
                slopeOk = (ih - navheight) < (hvel*self.frameTime * maxSlope)
                stepOk = (ih - navheight) < maxStep
                fx = a["b1"].offset[0] + bx
                fy = a["b1"].offset[2] + by
                b1, b2 = self.BORDER
                borderOk = (b1 < fx < b2) and (b1 < fy < b2)

                if (slopeOk or stepOk) and borderOk:
                    if a["jump"] <= 0:
                        a["b1"].offset[0] += bx
                        a["b1"].offset[2] += by
                        if (navheight - ih) > maxStep:
                            # fell off terrain
                            a['jump'] = self.frameNum
                            a['pv'].forces[0,1] = -9.81
                            a['pv'].v[1] = 0.0

                    if a["jump"] <= 0:
                        a['pv'].v[::2] = (jbx, jby)

                        self.setYoffset(a)

                        if time.time() - a['lastStep'] > 0.3 + 0.06 * random.random():
                            a['lastStep'] = time.time()

                            sfn = ['Short_Heavy_0{}.wav', 'StonyPath_0{}.wav']
                            sf = sfn[self.stage&1]

                            if self.stage == 2:
                                sf = 'Short_Heavy_0{}.wav'
                                if self.iceMap.getHeight(*a['b1'].offset[::2]):
                                    sf = 'StonyPath_0{}.wav'

                            if self.stage == 4:
                                sf = 'Short_Heavy_0{}.wav'
                                if a['b1'].offset[0] < 12 and \
                                   -2 < a['b1'].offset[2] < 41:
                                    sf = 'StonyPath_0{}.wav'

                            sf = sf.format(random.randint(1, 6))
                            self.si.put({"Play":(PATH+'../Sound/New/'+sf,
                                                 self.volmFX / 2,
                                                 (a['b1'].offset[:3], 6, 1.2))})
                    playerStuck = False
                elif not borderOk:
                    if (a["b1"].offset[0] < b1): a["b1"].offset[0] = b1
                    elif (a["b1"].offset[0] > b2): a["b1"].offset[0] = b2
                    if (a["b1"].offset[2] < b1): a["b1"].offset[2] = b1
                    elif (a["b1"].offset[2] > b2): a["b1"].offset[2] = b2
                    playerStuck = True
                else:
                    playerStuck = True


                if not self.isClient:
                    if a['id'] in self.aiNums:
                        self.agents[a['id']].isStuck = playerStuck

                df = 1# + 3*self.VRMode

                if CURRTIME - a['animTrans'] < 0.2:
                    # print('Trans idle->walk')
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    a["rig"].interpPoseFlat(a['tempPose'], self.keyFrames[transKF][3], fact)

                    off = np.array(self.keyFrames[transKF][2])
                    if a['moving'] < 0: off[1] = -0.4 * off[1] - 0.08
                    off = (off @ a['b1'].rotMat) * fact
                    off += a['b1'].lastOffset * (1-fact)
                    a['b1'].offset[:3] += off - a['b1'].lastOffset
                    a['b1'].lastOffset = off
                    a['animOffset'] = off
                else:
                    self.stepPoseLoop(a, a["obj"], self.keyFrames,
                                      df*self.frameTime * self.poseDt*a["moving"],
                                      isFlat=True)

            elif a["movingOld"]:
                if a['jump'] <= 0:
                    a['pv'].v[:] = 0
                a['animTrans'] = CURRTIME
                a['tempPose'] = a['rig'].exportPoseFlat()

            if not a['moving'] and not a['gesturing']:
                if CURRTIME - a['animTrans'] < 0.2:
                    # print('Trans walk->idle')
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    a['rig'].interpPoseFlat(a['tempPose'], self.idleFlat, fact)

                    off = a['b1'].lastOffset * (1-fact)
                    a['b1'].offset[:3] += off - a['b1'].lastOffset
                    a['b1'].lastOffset = off
                    a['animOffset'] = off
                elif a['animTrans'] > 0:
                    a['rig'].importPose(self.idle, updateRoot=False)
                    a['animTrans'] *= -1

            if self.frameNum - a['frameFired'] == 1:
                if a['fireColor'] == 'blank':
                    a['projFXstart'] = CURRTIME
                else:
                    a['throwAnim'] = True
                    a['animFired'] = False
                    a['poseThrow'] = self.throwKF[0][0]

            if a['projFXstart'] > 0:
                fxpos = a["b1"].offset[:3]
                fxoff = np.array([cos(a["cr"]),0,sin(a["cr"])])

                a['projFX'].target = fxpos + fxoff
                a['projFX'].changePos(fxpos + 0.6*fxoff)
                a['projFX'].step(self.frameTime)
                if CURRTIME - a['projFXstart'] > 0.12:
                    a['projFX'].reset()
                    a['projFXstart'] = -1

                    vh = a['fireVH']
                    if vh is None: vh = self.vv[1]
                    self.fire('blank', a['id'], vh)
                    a['frameFired'] = -100

            if a['throwAnim']:
                self.stepPoseLoop(a, a['obj'], self.throwKF, self.frameTime*2.2,
                                  loop=False, bone=a['b1'].children[0],
                                  timer='poseThrow')
                if not a['animFired'] and a['poseThrow'] > self.throwKF[5][0]:
                    a['animFired'] = True
                    self.fire(a['fireColor'], a['id'], a['fireVH'], throw=True)
                    a['frameFired'] = -100
                if a['poseThrow'] > self.throwKF[-1][0]:
                    a['throwAnim'] = False


            a["b1"].updateTM()

            if CURRTIME - a['animTrans'] < 0.2:
                self.testLegIK(a, (CURRTIME - a['animTrans']) / 0.4)

                self.setFullLegIKPos(a)

                a['b1TempOff'] = np.array(a['animOffset'])

            if a['throwAnim'] or a['gesturing']:
                self.testLegIK(a)

            if not a['moving'] and a['jump'] <= 0 and 'restAnim' not in a:
                self.setYoffset(a)
                if 'lastIKfacing' in a:
                    if abs(a['cr'] - a['lastIKfacing']) > 0.45*pi:
                        a['animTrans'] = CURRTIME
                        a['tempPose'] = a['rig'].exportPoseFlat()

            if not a['moving'] and not a['gesturing'] \
               and not a['throwAnim'] and 'restAnim' not in a \
               and a['animTrans'] < 0 and ('poseFlash' not in a or \
                                           a['poseFlash'] > self.flashKF[-1][0]):

                breathRate = 0.5 # Between 0.5 and 1 is best

                breathRate *= (1, 0.9, 1.1, 1, 1.12, 1.02, 1.08, 1.05, 0.98, 0.92)[a['id']]

                self.stepPoseLoop(a, a['obj'], self.idlingTest,
                                  self.frameTime * (breathRate + 0.6)/2,
                                  loop=True, timer='poseIdle',
                                  offsetMult=breathRate * 0.9,
                                  isFlat=True)

                a['tempPose'] = a['rig'].exportPoseFlat()
                a['rig'].interpPoseFlat(a['tempPose'], self.idleFlat, 1 - breathRate * 0.9)


                if CURRTIME + a['animTrans'] < 0.5:
                    # print('Trans idle->breathing')
                    fact = (CURRTIME + a['animTrans']) / 0.5

                    a['tempPose'] = a['rig'].exportPoseFlat()
                    a['rig'].interpPoseFlat(self.idleFlat, a['tempPose'], fact)

                    off = (1-fact) * a['b1TempOff'] + fact * a['animOffset']
                    a['b1'].offset[:3] += off - a['animOffset']
                    a['b1'].lastOffset = off
                    a['animOffset'] = off

            # Include throwing for leg IK
            if not a['moving'] and 'restAnim' not in a and a['animTrans'] < 0:

                if 'vrC' in a:
                    armU = a['b1'].children[0].children[0]
                    armU.rotate((0,0,0))
                    armU.children[0].rotate((0,0,0))

                a["rig"].b0.getTransform()

                if a['id'] == sc and self.cam1P \
                   and self.VRMode and self.frameNum > 1:
                    head = a['b1'].children[0].children[2]
                    hpos = (np.array([0.15,0.18,0,1]) @ head.TM)[:3]
                    hpos -= a['b1'].offset[:3]
                    test = self.VRHandPos - self.VRpos + hpos
                    a['vrC'] = np.round(test, 3).tolist()

                    # For debug
                    ts = self.testSphere
                    diff = a['b1'].offset[:3] + test - ts.coords
                    self.draw.translate(diff, ts.cStart*3,
                                        ts.cEnd*3, ts.texNum)
                    ts.coords += diff

                if 'vrC' in a:
                    test = np.array(a['vrC'])
                    handLen = 0.7 if a['id'] == 0 else 0.1
                    doArmIK(a['b1'].children[0].children[0],
                            a['b1'].offset[:3] + test, handLen)

                footSize = self.footSize[a['id']]

                # Skis
                if self.stage == 2:
                    if a['id'] == self.selchar:
                        footSize += 0.08

                try: ikR, ikL = a['legIKPos']
                except KeyError: pass
                else:
                    try:
                        interp = None
                        if CURRTIME + a['animTrans'] < 0.4:
                            interp = (CURRTIME + a['animTrans']) / 0.4
                        doFullLegIK(a['b1'].children[1], ikR, a, footSize, interp)
                        doFullLegIK(a['b1'].children[2], ikL, a, footSize, interp)
                    except IndexError:
                        pass


            if not self.fCam or a['id'] != self.selchar:
                interp = None
                if not a['moving'] and CURRTIME - a['animTrans'] < 0.2:
                    interp = (CURRTIME - a['animTrans']) / 0.2
                self.testAnim(a, interp)

            if a['fCam'] and a['id'] not in self.aiNums:
                if a['id'] == self.selchar:
                    a['vh'] = self.vv[1]
                torso = a['b1'].children[0]
                head = a['b1'].children[0].children[2]
                ang = head.angles
                ang[1] = 0
                ang[2] = -asin(a['vh']) - torso.angles[2]
                head.rotate(ang)

            self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])

            if not a["fCam"]:
                a["cr"] += a["cv"] * self.frameTime

            a["b1"].rotate([0,a["cr"],0])
            a["movingOld"] = a["moving"]

        self.frameProfile('PlayerMove')


        try:
            self.STAGECONFIG.frameUpdateAfter(self)
        except AttributeError:
            pass

        nd = self.draw.noiseDist
        if self.iceEffect:
            self.draw.noiseDist = min(0.1, nd + 0.6*self.frameTime)
            ppos = self.players[self.iceEffect[1]]['b1'].offset[:3]
            self.draw.noisePos = ppos
            self.pointLights.append({'i':(0.2,0.6,1.5),
                                        'pos': ppos + 1.5*self.vVhorz() + np.array((0,1,0))})
            self.pointLights.append({'i':(0.3,0.5,1.1),
                                        'pos': ppos - 1.5*self.vVhorz() + np.array((0,1,0))})
        else:
            self.draw.noiseDist = max(-1, nd - 0.2*self.frameTime)

        if not self.VRMode and not self.camFree:
            sp = self.players[sc]
            self.pos = sp["b1"].offset[:3] + np.array((0,0.5,0)) - 4 * self.vv
            self.pos[1] += sp['legIKoffset']
            self.pos -= sp['animOffset']

        if self.camAvg:
            self.pos = np.average([p['b1'].offset[:3] for p in self.players
                                   if p['id'] in self.actPlayers], axis=0)
            self.pos += self.players[sc]['cheight'] * 0.66

        if self.cam1P:
            if self.frameNum == self.cam1Pframe + 2:
                d = self.directionalLights[0]
                self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

            p = self.players[sc]
            p['fCam'] = True
            head = p['b1'].children[0].children[2]
            self.pos = (np.array([0.15,0.18,0,1]) @ head.TM)[:3]

            for tn in p['ctexn']:
                self.matShaders[tn]['cull'] = 1

        if self.fCam:
            a = self.players[sc]
            a["cr"] = atan2(self.vv[2], self.vv[0])
            if not a["moving"]:
                self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])
            if not self.VRMode and not self.cam1P and not self.camFree:
                self.pos += -0.45*self.vVvert() -0.3*self.vVhorz()
                self.pos[1] -= a['legIKoffset']

            playerIndex = {int(v):k for k, v in self.activePlayers.items()}
            for a in self.players:
                if a["id"] not in actPlayers: continue
                tn = a["id"]
                if tn != sc:
                    if raySphereIntersect(self.pos, self.vv, a["b1"].offset[:3], 0.5):
                        try:
                            px = playerIndex[tn]
                            self.uInfo["nameTag"] = str(px)
                        except KeyError: pass


        if self.doSh: self.shadowChar()

        if (not self.VRMode) or (self.frameNum & vf == 0):
            if self.doVl: self.simpleShaderVert()

            for p in self.players:
                if ("isHit" in p) and (self.frameNum - p["isHit"]) < 8:
                    for i in p["ctexn"]:
                        self.draw.highlight([1.,0,0], i)

        self.frameProfile('Postprocess', end=True)

##        if self.stage == 4:
##            test = 0.6 + 0.3 * sin(time.time() / 13) + 0.1 * sin(time.time() / 5)
##            d = self.directionalLights[0]
##            d['i'] = np.array([1.8,1.6,0.9]) * test
##            self.draw.setPrimaryLight(d['i'], np.array([viewVec(*d["dir"])]))


    def debugOverlay(self):
        if not self.showDebug: return

        self.rgb = np.array(self.rgb)
        fps = int((1 / self.frameTime))
        if fps > 30:
            col = [[0,192,255]]
        elif fps > 20:
            col = [[192,255,0]]
        elif fps > 15:
            col = [[255,192,0]]
        else:
            col = [[255,32,0]]
        self.rgb[:8,:5*fps] = col
        self.rgb[:8,5*30-2:5*31+2] = [[0,0,0]]
        self.rgb[:8,5*30:5*31] = [[0,255,0]]

        self.showAINav()

    def showAINav(self):
        if self.stage not in (1, 3): return

        hm = self.atriumNav['map']
        n = hm.shape[0]

        overlay = np.zeros((n, n, 3))
        overlay[:,:,0] = 128 * (1-hm)

        try:
            cpos, tpos, path = self.navDebug
            overlay[cpos[0], cpos[1]] = (64, 255, 0)
            overlay[tpos[0], tpos[1]] = (0, 128, 255)
            for i in path:
                overlay[i[0], i[1]] = (255, 255, 255)
        except AttributeError:
            pass

        out = 0.7 * overlay + 0.3 * self.rgb[self.H-n:self.H,:n]
        self.rgb[self.H-n:self.H,:n] = out

def run():
    global app

    import warnings
    warnings.simplefilter("ignore")
    import urllib3
    urllib3.disable_warnings()

    if PLATFORM == "darwin":
        os.system("defaults write -g ApplePressAndHoldEnabled -bool false")

    while True:
        app = CombatApp()
        if app.proceed:
            print("Starting")
            app.start()
            print("Running")
            app.runBackend()
            app.printProfile()
            if hasattr(app, 'statTime'):
                games = 1
                tim = time.time() - app.statTime
                try:
                    with open(PATH+"lib/Stat2.txt") as f:
                        games += int(f.readline().split(': ')[1])
                        tim += float(f.readline().split(': ')[1])
                except: pass
                with open(PATH+"lib/Stat2.txt", "w") as f:
                    text = 'Games Played: {}\nTime Spent (secs): {}'
                    f.write(text.format(games, round(tim, 2)))

            if hasattr(app, "WIN"):
                state = 0
                try:
                    with open(PATH+"lib/Stat.txt") as f:
                        state = int(f.read())
                except: pass
                with open(PATH+"lib/Stat.txt", "w") as f:
                    state = state | (1 << app.stage)
                    f.write(str(state))
            fps = app.frameNum/app.totTime
            print("avg fps:", fps)
            print("Closing network")
            app.qi.put(None)
            while not app.qo.empty():
                try: app.qo.get(True, 0.2)
                except: pass
            app.qi.close()
            app.qo.close()
            app.qi.join_thread()
            app.qo.join_thread()
            app.server.terminate()
            app.server.join()
            try: app.navProcess.terminate()
            except: pass
            try:
                with open(PATH+"lib/Stat.txt") as f: pass
            except FileNotFoundError:
                with open(PATH+"lib/Stat.txt", "w") as f: f.write("")
        print("Closing sound")
        app.si.put({"Fade":{'Time':0, 'Tracks':{'*'}}}, True, 0.1)
        time.sleep(2.1)
        app.si.put(None, True, 0.1)
        app.finish()
        print("Finished")
        if not app.proceed: break

if __name__ == "__main__":
    mp.set_start_method('spawn')
    run()
