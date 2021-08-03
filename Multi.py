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

import json

from Rig import Rig

import Phys

from Sound import SoundManager

from Network import TCPServer
import queue

import OpsConv
import AI
import Anim

from VertObjects import VertWater0

from IK import doFullLegIK

PATH = OpsConv.PATH
SWITCHABLE = True
SHOWALL = False
GESTLEN = 0.6
LOADALL = False

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

        self.si.put({"Play":(PATH + "../Sound/Noise.wav", volm, True)})

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

        stageNames = ["Desert", "CB Atrium", "Taiga", "New Stage", "Forest"]
        self.changeTitle("AXI Combat - " + stageNames[self.stage])

        self.ENVTRACKS = ["New_rv1.wav", "TextureA9.wav", "Haunted_2a.wav", "H8.wav", "Forest0a.wav"]

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
        self.lastTimes = {}

        self.expNum = 0
        self.exscale = 10.
        self.expPow = 2.7

        self.dofFoc = 3
        self.gamma = 1.75 if self.stage == 1 else 1.4
        self.tonemap = 'gamma' if self.stage == 1 else 'aces'
        self.doSSAO = False
        self.showAINav = False
        self.doMB = True

        self.camAvg = False
        self.cam1P = False
        self.envPointLights = []

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
        self.bindKey("x", lambda: self.fire("blank"))
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
            self.gestures.append(json.load(open(p+g)))

        self.bindKey("1", lambda: self.gesture(self.selchar, 0))
        self.bindKey("2", lambda: self.gesture(self.selchar, 1))
        self.bindKey("3", lambda: self.gesture(self.selchar, 2))
        self.bindKey("4", lambda: self.gesture(self.selchar, 3))
        self.bindKey("5", lambda: self.gesture(self.selchar, 4))

        self.bindKey("g", self.foc1)
        self.bindKey("G", self.foc2)
        self.bindKey("h", self.tgAO)
        self.bindKey("n", self.tgNav)
        self.bindKey("y", self.tgMB)
        self.bindKey('t', self.tgTM1)
        self.bindKey('T', self.tgTM2)
        self.bindKey('<F5>', self.tgCamAvg)
        self.bindKey('<F6>', self.tgCam1P)

        self.bindKey('p', self.printStuff)
        self.bindKey('o', self.lightTest)
        self.bindKey('i', self.respawnTest)

    def printStuff(self):
        print('pos', self.pos,
              'charpos', self.players[self.selchar]['b1'].offset[:3])

    # ==== Temple interactivity ====
    def lightTest(self):
        self.transStart = time.time()

        self.flashKF = Anim.loadAnim(PATH+'../Poses/FlashTest.ava', timeScale=1.2)
        for p in range(len(self.players)):
            self.players[p]['poseFlash'] = self.flashKF[0][0]

    def testTempleTrans(self):
        try:
            t = time.time() - self.transStart
        except:
            pos = self.players[self.selchar]['b1'].offset[:3]
            if Phys.eucDist(pos, (-14.5, 2, 20)) < 1:
                self.lightTest()
                t = 0
            else:
                t = -1

        if t > 12:
            return

        # rest 1, peak 600
        pointKF = [(0, 1), (0.4, 600), (1, 600), (3, 400), (4, 180),
                   (5, 90), (6, 42), (7, 20), (8.5, 5), (10, 1)]
        self.envPointLights[2]['i'] = np.array((1,1,1.)) * Anim.interpAttr(t, pointKF)


        d = self.directionalLights[0]
        dirKF = [(0, np.array([0.6,0.6,0.6])), (1, np.array([3.,3.,3.])),
                 (4, np.array([2.,2.,2.])), (10, np.array([1.8,1.6,0.9]))]

        d['i'] = Anim.interpAttr(t, dirKF)

        fogKF = [(0,   np.array((0.4, 0.2,400, 1))),
                 (0.8, np.array((1.6, 0.3,400, 1))),
                 (2,   np.array((1.6, 0.2,400, 1))),
                 (5, np.array((0.1, 0.01, 80,  0.6))),
                 (9, np.array((0.02,0.002,40,  0)))]

        fparams = Anim.interpAttr(t, fogKF)

        for i in range(len(self.matShaders)):
            if 'fog' in self.matShaders[i]:
                s = dict(self.matShaders[i])
                s['fog'] = fparams[0]
                s['fogAbsorb'] = fparams[1]
                s['fogDist'] = fparams[2]
                s['fogScatter'] = fparams[3]
                self.matShaders[i] = s

        self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

        if 0 < t < 3:
            tempObjs = np.array(self.castObjs)
            tempObjs = tempObjs * (1 - np.array(self.testRM()))
            self.shadowMap(0, tempObjs, bias=0.5)

        for p in self.actPlayers:
            a = self.players[p]
            dist = Phys.eucDist(a['b1'].offset[:3], (-14.5, 2, 20))
            if t > (dist/40) and a['poseFlash'] <= self.flashKF[-1][0]:
                a['moving'] = False
                a['animTrans'] = -1

                step = self.frameTime / (1 + dist/30 * (1 - (t > 4)))
                self.stepPoseLoop(a, a['obj'], self.flashKF, step,
                                  loop=False, timer='poseFlash')

    def testRM(self, rm=None):
        if rm is None:
            rm = [x <= self.players[-1]["obj"].texNum for x in range(len(self.vtNames))]
        if self.stage != 4:
            return rm

        try: t = time.time() - self.transStart
        except: t = 0

        if t > 2:
            r = list(rm)
            for f in self.vtNames:
                if 'rocks_ground_test' in f:
                    r[self.vtNames[f]] = True
            return r
        else:
            r = list(rm)
            for f in self.vtNames:
                if '3DRock004' in f or 'None' in f or 'Blank2' in f:
                    r[self.vtNames[f]] = False
                elif 'rocks_ground_test' in f or 'Cloud' in f:
                    r[self.vtNames[f]] = False
                elif self.vtNames[f] > self.players[-1]['obj'].texNum:
                    r[self.vtNames[f]] = True
            return r


    # ==== Respawning / recovery ====
    def setupRestKF(self):
        self.restKF = Anim.loadAnim(PATH+'../Poses/RestTest.ava')

        off_fact = 1 if self.selchar == 2 else 1.3
        arm_fact = (2.4, 2, 1, 2.4, 2.4, 2.5, 2.2, 2.3, 1.8)[self.selchar]
        for i in range(len(self.restKF)):
            tempPose = self.restKF[i][1]
            armPose = tempPose['children'][0]['children'][0]['angle']
            if armPose[2] > 0: armPose[2] -= 2*pi
            armPose[2] *= arm_fact
            self.restKF[i] = (self.restKF[i][0],
                              tempPose,
                              self.restKF[i][2] * off_fact)

    def respawnTest(self, sc=None):
        self.setupRestKF()

        if sc is None: sc = self.selchar
        a = self.players[sc]
        if 'restAnim' in a: return
        if a['jump'] > 0: return

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
        a = self.players[self.selchar]
        for xn in a["ctexn"]:
            if 'sub' in self.matShaders[xn]:
                temp = dict(self.matShaders[xn])
                del temp["sub"]
                self.matShaders[xn] = temp
            if "alphaTemp" in self.matShaders[xn]:
                self.matShaders[xn]['alpha'] = self.matShaders[xn]["alphaTemp"]

            self.draw.changeShader(xn, self.matShaders[xn], stage=self.stage)


        self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])
        for xn in a["ctexn"]:
            self.draw.highlight([0,0,0], xn, mult=True)
            self.matShaders[xn]['highlight'] = (0,0,0)

    def testRest(self, sc=None):
        if sc is None: sc = self.selchar
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

            self.matShaders[r.texNum]['add'] = Anim.interpAttr(t, addKF)

            self.draw.setUVOff(r.texNum, (0,0), (1,1), (t*0.2, 0))

            if self.getHealth(a['id']) < 0.6:
                a['pv'].colliders[0].hc -= self.frameTime * 4

            xn = a["ctexn"][0]
            if 'sub' in self.matShaders[xn]:
                self.matShaders[xn]['sub'] -= 0.6 * self.frameTime

                if self.matShaders[xn]['sub'] < 0:
                    self.matShaders[xn]['sub'] = 0
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
                if 'deathTime' in a:
                    del a['deathTime']
                self.draw.translate(-self.ringPos,
                                    r.cStart*3, r.cEnd*3, r.texNum)
                a['movingOld'] = True

    def setYoffsetTest(self, p):
        try: footR = p['b1'].children[1].children[0].children[0]
        except IndexError: return

        ihR = self.terrain.getHeight(*footR.TM[3,:3:2])
        offR = footR.TM[3,1] - 0.126 - ihR
        p['b1'].offset[1] -= offR


    # ==== Camera control ====
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
        self.gamma *= 1.1 #self.dofFoc *= 1.1
        print(self.gamma)
    def foc2(self):
        self.gamma /= 1.1 #self.dofFoc /= 1.1
        print(self.gamma)
    def tgNav(self): self.showAINav = not self.showAINav

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
        p['tempPose'] = p['rig'].b0.exportPose()

    def jump(self, pn=None):
        if pn is None: pn = self.selchar
        p = self.players[pn]
        if p["jump"] > 0:
            return

        p["jump"] = self.frameNum
        p["vertVel"] = 6.0

        LR = self.sndAttn(p['b1'].offset[:3], 5, 1.2)
        jfn = '../Sound/New/2H_Sharp_Swing_{}.wav'.format(random.randint(1, 4))
        self.si.put({"Play":(PATH + jfn, self.volmFX / 3 * LR)})

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

        initPose = self.idle if p['pstep'] < 0 else p['tempPose']
        p["rig"].interpPose(initPose, self.gestures[p["gestNum"]], p["poset"])
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

        try: _ = self.testTargs
        except:
            activeIds = list(self.actPlayers)
            pm = np.random.permutation(activeIds)
            targs = [0 for _ in range(self.NPLAYERS)]
            for t in range(len(pm)):
                targs[pm[t]] = activeIds[t]
                if pm[t] == activeIds[t]:
                    targs[pm[t]] = activeIds[t-1]
            self.testTargs = targs

            with open(PATH+'lib/EyeTracking.txt') as fuv:
                uvInfo = fuv.readlines()
                uvInfo = json.loads(''.join(uvInfo[3:]))
                self.eyeUV = {int(n):uvInfo[n] for n in uvInfo}


        head = p['b1'].children[0].children[2]

        ang = head.angles % (2*pi)
        rot = np.array(head.TM[:3,:3])
        pos = head.TM[3,:3] + np.array([0,0.1,0])

        target = self.players[self.testTargs[p['id']]]

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
        ih = self.terrain.getHeight(pos[0], pos[2]) + 0.114 # Account for foot
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


    def setYoffset(self, p):
        ih = self.terrain.getHeight(*(p['b1'].offset[::2] - p['animOffset'][::2]))

        p['b1'].offset[1] = ih + p['cheight'] + p['animOffset'][1]
        p['legIKoffset'] = 0

        if p['moving']: return

        try:
            legRU = p['b1'].children[1]
            legLU = p['b1'].children[2]
        except IndexError: return

        ihR = self.terrain.getHeight(*legRU.TM[3,:3:2])
        ihL = self.terrain.getHeight(*legLU.TM[3,:3:2])

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

    def sndAttn(self, src, mult=5, const=1.2):
        LR = (src - self.pos)
        dist = Phys.eucLen(LR)
        attn = mult / (dist + const)
        LR = (LR / dist) @ self.vVhorz()
        left = (LR + 1) / 2
        right = -(LR - 1) / 2
        return attn * np.array((left, right))

    def z1(self): self.setFOV(max(45, self.fovX * 0.96))
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
        self.updateShadowCam(0)
        sc["bias"] = (0.18 * abs(cos(ti)) + 0.12) * 2048 / self.shRes

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
        self.matShaders[e["obj"].texNum]["add"] = 4

        self.draw.translate(e["pos"], e["obj"].cStart*3, e["obj"].cEnd*3,
                            e["obj"].texNum)

        self.expNum = (self.expNum + 1) % len(self.exploders)

        LR = self.sndAttn(p, 6, 1)
        self.si.put({"Play":(PATH+"../Sound/Exp.wav",
                             self.volmFX / 3 * LR)})

    def addPlayer(self, o):
        pv = Phys.RigidBody(64, [0.,0,0], usegravity=0, noforces=True)
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
             "jump":-1, "vertVel":0, "fCam": False,
             "id":self.NPLAYERS, 'lastStep':0, 'legIKoffset':0,
             'animOffset':np.zeros(3), 'animTrans':-100,
             'frameFired':-100, 'fireColor':None, 'fireVH':0,
             'throwAnim':False, 'animFired':False,
             'poseThrow':0, 'poseIdle':0}

        self.NPLAYERS += 1
        self.players.append(a)
        self.w.addRB(pv)

        a["cheight"] = self.rpi[a["num"]][2]

        r = json.load(open(self.rpi[a["num"]][0]))
        a["rig"] = Rig(r, scale=self.rpi[a["num"]][1])
        a["b1"] = a["rig"].b0
        a["allBones"] = a["rig"].allBones

        a["Energy"] = 1

    def createObjects(self):
        self.NPLAYERS = 0

        st = time.time()
        print("Loading textures")

        self.w = Phys.World()

        mpath = PATH + "../Models/"

        # Rigfile, scale, height
        self.rpi = [(mpath + "Samus_PED/Samus_3.rig", 1.33, 1.66),
                    (mpath + "Zelda2/Test5b.rig", 0.33, 1.16),
                    (mpath + "L3/L3.rig", 0.75, 1.16),
                    (mpath + "Test3/Test3I.rig", 0.8, 1.32),
                    (mpath + "Zelda/Ztest3.rig", 1, 1.32),
                    (mpath + "LinkTP/Li.rig", 0.75, 1.5),
                    (mpath + "Ahri/Ahri4.rig", 1.8, 1.62),
                    (mpath + "Stormtrooper/Trooper5.rig", 1.4, 1.7),
                    (mpath + "Vader/Vader5.rig", 1.6, 1.56),
                    ]

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"Samus_PED/Samus_3B.obj",
                           animated=True, texMul=1, reflect="1a",
                           scale=1.33, shadow="")
        self.addPlayer(self.vertObjects[-1])

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"Zelda2/Test5b.obj",
                           animated=True,
                           texMul=2.5,
                           scale=0.33, shadow="R", rot=(0,0,0))
        self.addPlayer(self.vertObjects[-1])

        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath+"L3/L3.obj",
                           animated=True,
                           texMul=1,
                           scale=0.75, shadow="R")
        self.addPlayer(self.vertObjects[-1])

        if LOADALL:
            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Test3/Test3I.obj",
                               animated=True,
                               scale=0.8, shadow="R")
            self.addPlayer(self.vertObjects[-1])
            self.matShaders[self.vertObjects[-1].nextMtl.texNum]["sub"] = 0.6

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Zelda/Ztest4.obj",
                               animated=True,
                               texMul=2,
                               scale=1, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"LinkTP/Li.obj",
                               animated=True,
                               texMul=1.5,
                               scale=0.75, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Ahri/Ahri4.obj",
                               animated=True,
                               scale=1.8, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Stormtrooper/Trooper5.obj",
                               animated=True,
                               scale=1.4, shadow="R")
            self.addPlayer(self.vertObjects[-1])

            self.addVertObject(VertModel, [0,0,0],
                               filename=mpath+"Vader/Vader5.obj",
                               animated=True,
                               scale=1.6, shadow="R")
            self.addPlayer(self.vertObjects[-1])
            self.matShaders[self.vertObjects[-3].texNum]["phong"] = 1

        if self.stage == 0:
            self.addVertObject(VertTerrain, [-10, 0, -10],
                            heights=PATH+"../Assets/TerrainA.png",
                            texture=PATH+"../Assets/Sand.png",
                            scale=0.375, vertScale=26,
                            shadow="CR",# mip=1,
                            uvspread=4)
            self.terrain = self.vertObjects[-1]

            self.t2 = Phys.TerrainCollider([-10,0,-10], self.terrain.size[0],
                                           self.terrain.heights, 0.375)
            self.t2.onHit = lambda x: self.explode(x)
            self.w.addCollider(self.t2)

            self.directionalLights.append({"dir":[pi*2/3, 2.1], "i":[1.8,1.2,0.4]})
            self.directionalLights.append({"dir":[pi*2/3, 2.1+pi], "i":[0.5,0.4,0.1]})
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.2,0.4]})
            self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Desert_2k.ahdr",
                                    rot=(0,-pi/3,0), hdrScale=12)
            self.skyBox.created()

            self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

        elif self.stage == 1:
            hasNewAtrium = os.path.exists(PATH+"../Atrium/Atrium8.obj")
            atriumName = '8.obj' if hasNewAtrium else 'AtlasY.obj'

            self.addVertObject(VertModel, [13.32,0,20.4], rot=(0,0,0),
                               filename=PATH+"../Atrium/Atrium" + atriumName,
                               scale=1.2, mip=2,
                               useShaders={"cull":1},
                               subDiv=1, shadow="CR",
                               blender=hasNewAtrium)

            self.terrain = VertTerrain0([0,-0.6,0],
                                        PATH+"../Atrium/AtriumNav.png",
                                        scale=0.293, vertScale=20)

            hm = Image.open(PATH+"../Atrium/AtriumNavA.png")
            hm = np.array(hm)[:,:,0] < 80
            hs = 0.586
            ho = np.array([0.3,0,0.3])

            self.atriumNav = {"map":hm, "scale":0.586, "origin":ho}

            self.t2 = Phys.TerrainCollider([0,-0.6,0], self.terrain.size[0],
                                           self.terrain.heights, 0.293)
            self.t2.onHit = lambda x: self.explode(x)
            self.w.addCollider(self.t2)

            self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":[2.0,1.77,1.33]})
            self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":[0.3,0.2,0.15]})
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.075,0.15,0.3]})

            # Local lights are getting out of hand
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.2,0.2,0.2]})

            self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Autumn_Park_2k.ahdr",
                                    rot=(0,0,0), hdrScale=48)
            self.skyBox.created()

        elif self.stage == 2:
            self.addVertObject(VertTerrain, [-50, 0, -50],
                           heights=PATH+"../Assets/Terrain.tif",
                           texture=PATH+"../Assets/Blank1.png", scale=0.6,
                           vertScale=2.5/6553, vertPow=2, vertMax=50000,
                           uvspread=2, shadow="CR")
            self.terrain = self.vertObjects[-1]

            self.t2 = Phys.TerrainCollider([-50,0,-50], self.terrain.size[0],
                                           self.terrain.heights, 0.6)
            self.t2.onHit = lambda x: self.explode(x)
            self.w.addCollider(self.t2)

            nr.seed(1); random.seed(1)
            options = {"filename":mpath+"pine/Pine.obj", "static":True,
                   "texMode":None, "scale":0.2, "shadow":"C"}
            for i in range(-50, 70, 20):
                for j in range(-50, 70, 20):
                    c = numpy.array((i, 0, j), dtype="float")
                    c += nr.rand(3) * 8
                    c[1] = self.terrain.getHeight(c[0],c[2]) - 0.4
                    r = random.random() * 3
                    self.addVertObject(VertModel, c, **options, rot=(0,r,0))

            self.directionalLights.append({"dir":[pi*1.7, 0.54], "i":[0.3,0.4,0.6]})
            self.directionalLights.append({"dir":[pi*1.7, 0.54+pi], "i":[0.1,0.1,0.1]})
            self.directionalLights.append({"dir":[pi*1.7, 0.54], "i":[0.1,0.1,0.1]})
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.1,0.2]})

            self.skyTex = np.zeros((1,6,3),"uint16")

            self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}


        elif self.stage == 3:
            ox, oz = 15, 20
            mScale = 0.5
            self.addVertObject(VertModel, [ox, 0, oz], rot=(0,0,0),
                               filename=PATH+"../Models/NewStage.obj",
                               scale=mScale, mip=2,
                               useShaders={"cull":1},
                               subDiv=1, shadow="CR")

            a = Image.open(PATH+"../Models/NewStageX3.png")
            navScale = 0.1
            navScaleV = -20 / navScale * mScale
            s = -a.size[0] * navScale * mScale
            navOrigin = [s+ox, 20 * mScale, s+oz]

            self.terrain = VertTerrain0(navOrigin,
                                        PATH+"../Models/NewStageX3.png",
                                        scale=navScale, vertScale=navScaleV)

            hm = Image.open(PATH+"../Models/NewStageNav1.png")
            hm = np.array(hm)
            hm = 1 - ((hm[:,:,0] == 255) & (hm[:,:,1] == 0))
            hm = hm.astype('bool')

            hs = 4 * navScale
            ho = np.array(navOrigin) * np.array([1,0,1]) + np.array([0,0,-0.2])

            self.atriumNav = {"map":hm, "scale":hs, "origin":ho}

            self.t2 = Phys.TerrainCollider(navOrigin, self.terrain.size[0],
                                           self.terrain.heights, navScale)
            self.t2.onHit = lambda x: self.explode(x)
            self.w.addCollider(self.t2)

            self.directionalLights.append({"dir":[pi*2/3, 2.1], "i":[1.8,1.2,0.4]})
            self.directionalLights.append({"dir":[pi*2/3, 2.1+pi], "i":[0.5,0.4,0.1]})
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.2,0.4]})
            self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Autumn_Park_2k.ahdr",
                                    rot=(0,0,0), hdrScale=48)
            self.skyBox.created()

        elif self.stage == 4:
            tsize = 320
            tscale = 100 / tsize
            coords = [10 + tsize*tscale/2, -3.4, 20 + tsize*tscale/2]
            self.terrain = VertTerrain0(coords, PATH+"../Models/Temple/Height.png",
                                        rot=(0,pi,0),
                                        scale=tscale, vertScale=22,
                                        vertPow=2.2, vertMax=0.6)

            self.t2 = Phys.TerrainCollider(coords, self.terrain.size[0],
                                           self.terrain.heights, 0.5)
            self.t2.onHit = lambda x: self.explode(x)
            self.w.addCollider(self.t2)

            self.addVertObject(VertModel, [10, 0, 20], rot=(0,-pi/2,0),
                               filename=PATH+"../Models/Temple/Temple1.obj",
                               shadow="CR",
                               blender=True)

            self.addVertObject(VertModel, [10,0,20], rot=(0,-pi/2,0),
                               filename=PATH+"../Models/Temple/TempleTrans.obj",
                               shadow="CR")

            for f in self.vtNames:
                if 'Fog' in f:
                    self.matShaders[self.vtNames[f]]['fog'] = 0.01
                    self.matShaders[self.vtNames[f]]['fogAbsorb'] = 0.01
                    self.matShaders[self.vtNames[f]]['2d'] = 1
                    self.vertObjects[self.vtNames[f]].castShadow = False
                if 'Water' in f:
                    self.matShaders[self.vtNames[f]]['SSR'] = '0'
                    self.vertObjects[self.vtNames[f]].castShadow = False
                    self.water = VertWater0(
                        (0,0,0), self, pScale=0.04,
                        wDir=[(-0.4,0.17), (-0.4, -0.2)],
                        wLen=[(10, 4, 3), (7, 5, 2)],
                        wAmp=np.array([(0.8, 0.5, 0.3), (0.6, 0.35, 0.25)])*1.6,
                        wSpd=np.array([(0.6, 0.8, 1.1), (1, 1.1, 1.3)])*1.8, numW=3)
                    self.water.texNum = self.vtNames[f]
                if 'Plant' in f or '093' in f:
                    self.matShaders[self.vtNames[f]]['translucent'] = 1

            pp1 = np.array((-14.5,15,24.))
            pp2 = np.array((-14.5,15,16.))
            pi1 = np.array((1,0.91,0.72)) * 40
            pi2 = np.array((0.48,0.99,1)) * 32

            ppc = np.array((-14.5,2.3,20))
            pic = np.array((1,1,1.))
            self.envPointLights = [{'i':pi1, 'pos':pp1},
                                   {'i':pi2, 'pos':pp2},
                                   {'i':pic, 'pos':ppc}]

            self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6], "i":[1.8,1.6,0.9]})
            # First bounce
            self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6+pi], "i":[0.24,0.25,0.2]})
            # Second bounce
            self.directionalLights.append({"dir":[pi*2/3, 2.1], "i":[0.1,0.09,0.08]})
            # Sky
            self.directionalLights.append({"dir":[0, pi/2], "i":[0.04,0.1,0.2]})
            self.directionalLights.append({"dir":[pi*2/3+0.1, 2.1], "i":[0.1,0.25,0.5]})
            self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/lilienstein_2k.ahdr",
                                    rot=(0,0,0), hdrScale=14)
            self.skyBox.created()

            skyShader = self.matShaders[self.skyBox.texNum]
            skyShader['isEqui'] = 1
            skyShader['rotY'] = 0.22

            self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}


        self.spheres = []
        self.srbs = []
        for i in range(self.numBullets):
            p = [32, 3+i, 29]
            self.addVertObject(VertSphere, p, n=16, scale=0.25,
                               texture=PATH+"../Assets/Blank.png",
                               useShaders={"emissive":2})
            self.spheres.append(("blank", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(2, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.25, False,
                                                          rb=self.srbs[-1]))
            self.srbs[-1].disabled = True
            self.w.addRB(self.srbs[-1])

        for i in range(self.numBullets // 2):
            p = [-30, 3+i, 20]
            self.addVertObject(VertSphere, p, n=16, scale=0.5,
                               texture=PATH+"../Assets/Red.png",
                               useShaders={"emissive":2.5})
            self.spheres.append(("red", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(24, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.5, False,
                                                          rb=self.srbs[-1],
                                                          damage=4))
            self.srbs[-1].disabled = True
            self.w.addRB(self.srbs[-1])


        self.addVertObject(VertModel, [0,-0.6,0], scale=(1,0.6,1),
                           filename=PATH+'../Models/Rings.obj',
                           shadow='', useShaders={'add':0.5, 'noline':True})
        self.restRings = self.vertObjects[-1]


        if self.stage == 2 or self.stage == 4:
            fog = 1.4 if self.stage == 2 else 0.02
            fabs = 0.06 if self.stage == 2 else 0.002
            fdist = 0 if self.stage == 2 else 40

            self.addVertObject(VertPlane, [-1,-1,0],
                           h1=[2,0,0], h2=[0,2,0], n=1,
                           texture=PATH+"../Assets/Blank2.png",
                           useShaders={"2d":1, "fog":fog, 'fogAbsorb':fabs,
                                       'fogDist':fdist})

        if self.stage == 4:
            self.addVertObject(VertModel, [10,0,20], rot=(0,-pi/2,0),
                               filename=PATH+"../Models/Temple/Clouds.obj",
                               shadow="",
                               useShaders={'add':0.12, 'noline':True})

        for i in range(self.numBullets // 3):
            p = [20, 3+i, 20]
            self.addVertObject(VertSphere, p, n=12, scale=0.25,
                               texture=PATH+"../Assets/Orange.png",
                               useShaders={"add":0.4})
            self.spheres.append(("orange", self.vertObjects[-1]))

            self.srbs.append(Phys.RigidBody(10, p, vel=[0.,0,0.],
                                            usegravity=0, elasticity=0.8))
            self.srbs[-1].addCollider(Phys.BulletCollider(0.25, False,
                                                          rb=self.srbs[-1],
                                                          damage=6,
                                                          explode=True))
            self.srbs[-1].disabled = True
            self.w.addRB(self.srbs[-1])

        self.pickups = []
        for i in range(1):
            p = [0, 0, 0]
            self.addVertObject(VertSphere, p, n=12, scale=0.25,
                               texture=PATH+"../Assets/Green.png",
                               useShaders={"emissive":1.4})
            self.pickups.append({"pos":None, "t":-1, "obj":self.vertObjects[-1]})


        self.blackHoles = []
        for i in range(self.numBullets // 5):
            p = [20, 3+i, 15]
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
            self.srbs[-1].disabled = True
            self.srbs[-1].colliders[0].onHit = lambda x: self.explode(x)

            self.w.addRB(self.srbs[-1])

            ps = ContinuousParticleSystem(np.array([0,0,0.]), (0,pi/2),
                                          vel=0.0, randVel=0.01,
                                          nParticles=2400,
                                          randPos=0.2,
                                          lifespan=400,
                                          size=24 * (self.W/960), opacity=0.4,
                                          color=(0,0,0))
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
                           useShaders={"SSR":"0"})
            self.water = self.vertObjects[-1]

        for i in range(len(self.players)):
            ps = ContinuousParticleSystem(np.array([0,0,0.]), (0,pi/2),
                                          vel=0.03, randVel=0.01,
                                          nParticles=2400,
                                          randPos=0.2,
                                          lifespan=1200,
                                          size=32 * (self.W/960), opacity=0.4,
                                          color=(0,0,0))
            self.addParticleSystem(ps)
            self.players[i]["ghost"] = ps

        self.exploders = []
        self.expLights = {}
        for i in range(self.numBullets // 3):
            p = np.array([0., 0, 0])
            self.addVertObject(VertSphere, p, n=24, scale=0.25,
                               texture=PATH+"../Assets/Orange1.png",
                               useShaders={"add":2.})
            self.exploders.append({"pos":p, "active":False,
                                   "scale":1, "obj":self.vertObjects[-1]})


        bd = [(-10, 50), (-10, 50), (-20, 50), (0, 35), (-30, 60)]
        ss = [b[1] - b[0] for b in bd]
        self.BORDER = np.array(bd[self.stage], "float")
        self.stageSize = ss[self.stage]

        if self.stage != 1:
            b1, b2 = self.BORDER
            ss = self.stageSize
            c = [(b1, 0, b1), (b1, 0, b1), (b2, 0, b1), (b1, 0, b2)]
            h = [(ss, 0, 0), (0, 0, ss), (0, 0, ss), (ss, 0, 0)]
            for i in range(4):
                self.addVertObject(VertPlane, c[i], n=12,
                                   h1=h[i], h2=[0, 20, 0],
                                   texture=PATH+"../Assets/Magenta.png",
                                   useShaders={"border":0.1})

        sr = self.shRes
        fact = 0.5 if self.stage == 4 else 1
        self.shadowCams.append({"pos":[40, 5, 40], "dir":[pi/2, 1.1],
                                "size":sr, "scale":24*sr/2048 * fact})
        self.shadowCams.append({"pos":[40, 5, 40], "dir":[pi/2, 1.1],
                                "size":sr, "scale":200*sr/2048})

        self.makeObjects(1)

        self.si.put({"Fade":{'Time':0, 'Tracks':{PATH + "../Sound/Noise.wav",
                                                 PATH + '../Sound/Plains3v4.wav'}}})

        if self.stage == 1:
            with open(PATH + "../Atrium/LightsCB.txt") as x:
                a = json.loads(x.read())
                for x in a:
                    x["i"] = (1.5,1.5,1.5)
                    x["pos"] = np.array(x["pos"], "float32") * 1.2 + \
                               np.array([13.32,0,20.4])
                    x["vec"] = -np.array(x["vec"], "float32")
                self.spotLights.extend(a)

        print("Done in", time.time() - st, "s")

    def postProcess(self):
        if self.doSSAO:
            self.draw.ssao()

        if self.frameNum > 1:
            if self.doMB:
                self.draw.motionBlur(self.oldVPos, self.oldVMat)

        db = self.draw.getDB()
        target = max(0.8, min(6, db[self.H//2, self.W//2]))
        df = self.dofFoc
        if (target < self.dofFoc) or (self.frameNum & 1 == 0):
            self.dofFoc = sqrt(sqrt(df * df * df * target))

        self.draw.dof(self.dofFoc)
        if self.doBloom:
            self.draw.blur()

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

        self.draw.gamma(self.gamma, self.tonemap)

    def fireSnd(self, color):
        snd = {"blank":("A",4), "orange":("B",3), "red":("C",4), "black":("D",2.5)}
        self.si.put({"Play":(PATH+"../Sound/Fire" + snd[color][0] + ".wav",
                             self.volmFX / 2 / snd[color][1])})

    def fireAnim(self, color, sc=None, vh=None):
        if sc is None:
            sc = self.selchar
        a = self.players[sc]
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
        if cb is None:
            a["Energy"] += self.COSTS[color]
            return False

        self.srbs[cb].disabled = False
        s = self.bulletSpeed
        if color == "black": s *= 0.66
        d = np.array([cos(a["cr"]), vh, sin(a["cr"])])
        self.srbs[cb].v = d*s
        self.srbs[cb].pos = np.array(a["b1"].offset[:3]) + 0.8*(d*np.array([1,0,1]))
        self.srbs[cb].pos[1] += int(throw)

        snd = {"blank":("A",3), "orange":("B",2), "red":("C",3), "black":("D",2)}

        LR = self.sndAttn(a["b1"].offset[:3], 2.7, 1)
        self.si.put({"Play":(PATH+"../Sound/Fire" + snd[color][0] + ".wav",
                             self.volmFX / snd[color][1] * LR)})

        if sc == self.selchar:
            self.frameFired = color

        return color

    def onStart(self):
        self.gameStarted = False

        if self.isClient:
            snd = self.ENVTRACKS
            self.si.put({"Play":(PATH+"../Sound/" + snd[self.stage], self.volm * 0.8, True)})
            self.gameStarted = True

        self.qi.put(True)
        if self.stage == 4:
            self.cubeMap = CubeMap(self.skyTex, None, False)
        else:
            self.cubeMap = CubeMap(self.skyTex, 2, False)
        a = self.cubeMap.texture.reshape((-1, 3))
        self.draw.setReflTex("1a", a[:,0], a[:,1], a[:,2], self.cubeMap.m)
        self.draw.setReflTex("0", a[:,0], a[:,1], a[:,2], self.cubeMap.m)
        self.draw.setHostSkyTex(self.cubeMap.rawtexture)

        p = PATH+"../Poses/"
        self.poses = Anim.loadAnim(p+'WalkCycle8.ava', timeScale=0.9)
        self.keyFrames = self.poses
        self.idle = json.load(open(p+"Idle1.pose"))

        self.idleTest = Anim.loadAnim(p+'Idletest.ava')
        self.gestures.append(self.idleTest[0][1])

        self.idlingTest = Anim.loadAnim(p+'IdlingTest6.ava')
        for i in range(len(self.idlingTest)):
            self.idlingTest[i] = (self.idlingTest[i][0] * 1.6,
                                  self.idlingTest[i][1],
                                  self.idlingTest[i][2] * 0.6)

        self.throwKF = Anim.loadAnim(PATH+'../Poses/Throw.ava')
        for i in range(len(self.throwKF)):
            self.throwKF[i] = (self.throwKF[i][0],
                               self.throwKF[i][1]['children'][0],
                               self.throwKF[i][2])

        self.setupRestKF()

        space = 2 if self.stage == 3 else 3
        xpos = -20 if self.stage == 4 else 28

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
                    not ("sub" in self.matShaders[x]) \
                    for x in range(len(self.renderMask))]
            sobj[self.vtNames[PATH+"../Assets/Blank.png"]] = True
            sobj[self.vtNames[PATH+"../Assets/Red.png"]] = True
        return sobj

    def sendState(self):
        dat = {}
        for a in self.players:
            dat[a["num"]] = {
                "r1": np.round(a["b1"].offset, 3).tolist(),
                "m1": int(a["moving"]),
                "c1": a["cr"],
                "hc": [c.hc for c in a["pv"].colliders],
                "ee": a["Energy"],
                "gg": a["gestNum"], "gi": a["gestId"],
                "jp": a["jump"],
                #"hf": a["isHit"]
                }

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
                "time":self.frameNum, "rl":round(self.directionalLights[0]["dir"][1], 2)}
        if self.frameFired: adat["ff"] = self.frameFired

        try:
            self.qi.put_nowait(bytes(json.dumps(adat), "ascii"))
        except queue.Full: pass
        except: raise

    def sendPlayer(self):
        dat = {}
        a = self.players[self.selchar]
        dat[a["num"]] = {
            "r1": np.round(a["b1"].offset, 3).tolist(),
            "m1": a["moving"],
            "c1": a["cr"],
            "fire": self.frameFired,
            "fire2": self.frameFiredOld,
            "vh": float(self.vv[1]),
            "gg": a["gestNum"], "gi": a["gestId"],
            "jp": a["jump"]
            }

        adat = {"players":dat, "time":self.frameNum}
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
                    sc = self.players[int(pn)]
                    a = k[pn]
                    if "hc" in a:
                        for i in range(len(a["hc"])):
                            sc["pv"].colliders[i].hc = a["hc"][i]
                    if int(pn) == self.selchar: continue
                    sc["b1"].offset = np.array(a["r1"])
                    sc["moving"] = a["m1"]
                    sc["cr"] = a["c1"]
                    if "ee" in a: sc["Energy"] = a["ee"]
                    if "fire" in a:
                        if a["fire"]:
                            self.fire(a["fire"], int(pn), a["vh"])
                    if "fire2" in a:
                        if a["fire2"]:
                            self.fire(a["fire2"], int(pn), a["vh"])

                    if a["gg"] is not None:
                        if self.players[int(pn)]["gestNum"] != a["gg"]:
                            if self.players[int(pn)]["gestId"] != a["gi"]:
                                self.gesture(int(pn), a["gg"], a["gi"])

                    if a["jp"] > 0:
                        if self.players[int(pn)]["jump"] < 0:
                            if a["jp"] != -self.players[int(pn)]["jump"]:
                                self.jump(int(pn))

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

        LR = self.sndAttn(i["pos"], 4, 1)
        self.si.put({"Play":(PATH+"../Sound/Pickup.wav",
                             self.volmFX / 3 * LR)})

    def resetPickup(self):
        i = self.pickups[0]
        cs, ce, tn = i["obj"].cStart*3, i["obj"].cEnd*3, i["obj"].texNum
        self.draw.translate(-i["pos"], cs, ce, tn)
        i["pos"] = None

    def qq(self): self.doQuit = True

    def frameProfile(self, i):
        try: _ = self.ftime
        except:
            self.ftime = {}
            self.ftx = {}
        if i not in self.ftime:
            self.ftime[i] = 0
            self.ftx[len(self.ftime)-1] = i
        self.ftime[i] += time.time() - self.frameStart
    def printProfile(self):
        for i in range(len(self.ftx)):
            x = self.ftx[i]
            if x == '.': continue
            offset = 0 if i == 0 else self.ftime[self.ftx[i-1]]
            print(round((self.ftime[x] - offset) / self.frameNum, 5), x)

        print('Total', round((self.ftime[x] - self.ftime['.']) / self.frameNum, 5))

    def frameUpdate(self):
        if self.VRMode: self.frameUpdateVR()

        vf = 7 if self.VRMode else 1

        if self.frameNum == 0:
            self.waitFinished = False
            self.statTime = time.time()
        if self.frameNum == 1:
            self.rotateLight()

        self.frameStart = time.perf_counter()
        self.frameProfile('.')

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
            if not self.gameStarted:
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

        if self.stage == 4:
            self.testTempleTrans()

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
            self.lp = []
            for i in range(len(self.spheres)):
                self.lp.append(np.array(self.srbs[i].pos))

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
                if "deathTime" not in a: a["deathTime"] = time.time()
                a["pv"].pos[:] = -10.
                a["Energy"] = 0
                tr = 0.6 + 0.32 * min(40, (time.time() - a["deathTime"])*10) / 40
                for xn in a["ctexn"]:
                    self.matShaders[xn]["sub"] = tr
                    if "alpha" in self.matShaders[xn]:
                        self.matShaders[xn]['alphaTemp'] = self.matShaders[xn]["alpha"]
                        del self.matShaders[xn]["alpha"]
                g = a["ghost"]
                if (not self.VRMode) or (self.frameNum & 1):
                    g.changePos(a["b1"].offset[:3])
                    g.step()
            elif tn not in actPlayers:
                a["pv"].pos[:] = -10.
            else:
                a["pv"].pos = a["b1"].offset[:3] + np.array([0,-0.5,0])
                a["Energy"] += 0.05 * self.frameTime
                a["Energy"] = min(1, a["Energy"])

        self.frameProfile('Ghost/Energy')

        self.w.stepWorld(self.frameTime, checkColl=(self.frameNum & vf == 0))

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
                    self.srbs[i].disabled = True


        for i in range(len(self.spheres)):
            s = self.spheres[i][1]
            if (np.isnan(self.srbs[i].pos)).any():
                print("NaN, disable")
                self.srbs[i].pos[:] = 0.
                self.srbs[i].v[:] = 0.
                self.srbs[i].disabled = True
            diff = self.srbs[i].pos - self.lp[i]
            if sum(diff*diff) > 0:
                self.draw.translate(diff, s.cStart*3, s.cEnd*3, s.texNum)

            self.lp[i] = np.array(self.srbs[i].pos)

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
                self.matShaders[tn]["add"] = 2 / e["scale"]

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
                for a in self.players:
                    if a["id"] not in actPlayers: continue
                    if np.sum(np.abs(i["pos"] - a["b1"].offset[:3])) < 2:
                        a["Energy"] += 0.2
                        a["Energy"] = min(1, a["Energy"])
                        self.resetPickup()
                        break


        if "nameTag" in self.uInfo: del self.uInfo["nameTag"]
        for a in self.players:
            if a["id"] not in actPlayers: continue
            if a["jump"] > 0:
                dx = a["vertVel"] * self.frameTime - 9.81 * self.frameTime**2 / 2
                a["b1"].offset[1] += dx * 1.2
                a["vertVel"] -= self.frameTime * 9.81
                ih = self.terrain.getHeight(*(a["b1"].offset[::2] - a['animOffset'][::2]))
                if (ih + a["cheight"]) > a["b1"].offset[1]:
                    a["jump"] = -a["jump"]
                    self.setYoffset(a)

                    LR = self.sndAttn(a['b1'].offset[:3], 6, 1)
                    self.si.put({"Play":(PATH+"../Sound/New/Quiver.wav",
                                         abs(a['vertVel']) / 8 * self.volmFX / 3 * LR)})

                    if abs(a["vertVel"]) > 8:
                        a["pv"].colliders[0].hc += abs(abs(a["vertVel"]) - 6)
                        a["isHit"] = self.frameNum

            if a["gesturing"]:
                a["moving"] = 0
                self.stepGest(a, a["obj"], self.frameTime * self.poseDt)

            if a["moving"]:
                transKF = 2 if a['moving'] > 0 else 4
                if not a['movingOld']:
                    a['animTrans'] = CURRTIME
                    a['poset'] = self.keyFrames[transKF][0]
                    a['tempPose'] = a['rig'].exportPose()

                bx = hvel*a["moving"]*cos(a["cr"])
                by = hvel*a["moving"]*sin(a["cr"])
                if a["fCam"]:
                    bx += hvel/3 * cos(a["cr"] + pi/2) * a["cv"]
                    by += hvel/3 * sin(a["cr"] + pi/2) * a["cv"]

                    d = sqrt(bx*bx + by*by) / hvel
                    bx /= d; by /= d

                bx *= self.frameTime; by *= self.frameTime
                if a['moving'] < 0:
                    bx *= 0.9; by *= 0.9

                if CURRTIME - a['animTrans'] < 0.2:
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    bx *= fact; by *= fact

                ax, ay = a["b1"].offset[::2] - a['animOffset'][::2]
                ih = self.terrain.getHeight(ax + bx, ay + by) + a["cheight"]

                navheight = a["b1"].offset[1] + a['legIKoffset']
                slopeOk = (ih - navheight) < (hvel*self.frameTime * maxSlope)
                stepOk = (ih - navheight) < maxStep
                fx = a["b1"].offset[0] + bx
                fy = a["b1"].offset[2] + by
                b1, b2 = self.BORDER
                borderOk = (fx < b2) and (fx > b1) and (fy < b2) and (fy > b1)

                if (slopeOk or stepOk) and borderOk:
                    a["b1"].offset[0] += bx
                    a["b1"].offset[2] += by
                    if a["jump"] <= 0:
                        if (navheight - ih) > maxStep:
                            a['jump'] = self.frameNum
                            a['vertVel'] = 0.0
                    if a["jump"] <= 0:
                        self.setYoffset(a)

                        if time.time() - a['lastStep'] > 0.3 + 0.06 * random.random():
                            a['lastStep'] = time.time()

                            LR = self.sndAttn(a['b1'].offset[:3], 6, 1.2)
                            sfn = ['Short_Heavy_0{}.wav', 'StonyPath_0{}.wav']
                            sfn = sfn[self.stage&1].format(random.randint(1, 6))

                            self.si.put({"Play":(PATH+'../Sound/New/'+sfn,
                                                 self.volmFX / 2 * LR)})

                df = 1 + 3*self.VRMode

                if CURRTIME - a['animTrans'] < 0.2:
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    a["rig"].interpPose(a['tempPose'], self.keyFrames[transKF][1], fact)

                    off = np.array(self.keyFrames[transKF][2])
                    if a['moving'] < 0: off[1] = -0.4 * off[1] - 0.08
                    off = (off @ a['b1'].rotMat) * fact
                    off += a['b1'].lastOffset * (1-fact)
                    a['b1'].offset[:3] += off - a['b1'].lastOffset
                    a['b1'].lastOffset = off
                    a['animOffset'] = off
                else:
                    self.stepPoseLoop(a, a["obj"], self.keyFrames,
                                      df*self.frameTime * self.poseDt*a["moving"])

            elif a["movingOld"]:
                a['animTrans'] = CURRTIME
                a['tempPose'] = a['rig'].b0.exportPose()

            if not a['moving'] and not a['gesturing']:
                if CURRTIME - a['animTrans'] < 0.2:
                    fact = (CURRTIME - a['animTrans']) / 0.2
                    fact = 2*fact**2 if fact < 0.5 else 1 - 2*(fact-1)**2
                    a['rig'].interpPose(a['tempPose'], self.idle, fact)

                    off = a['b1'].lastOffset * (1-fact)
                    a['b1'].offset[:3] += off - a['b1'].lastOffset
                    a['b1'].lastOffset = off
                    a['animOffset'] = off

                elif a['animTrans'] > 0:
                    a['rig'].importPose(self.idle, updateRoot=False)
                    a['animTrans'] *= -1


            if self.frameNum - a['frameFired'] == 1:
                a['throwAnim'] = True
                a['animFired'] = False
                a['poseThrow'] = self.throwKF[0][0]

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

                try:
                    footR = a['b1'].children[1].children[0].children[0]
                    ihR = self.terrain.getHeight(*footR.TM[3,:3:2])
                    ikR = np.array((footR.TM[3,0], ihR, footR.TM[3,2]))
                    footL = a['b1'].children[2].children[0].children[0]
                    ihL = self.terrain.getHeight(*footL.TM[3,:3:2])
                    ikL = np.array((footL.TM[3,0], ihL, footL.TM[3,2]))
                    a['legIKPos'] = (ikR, ikL)
                except IndexError: pass
                a['b1TempOff'] = np.array(a['animOffset'])

            elif 'restAnim' not in a:
                self.testLegIK(a)

            if not a['moving'] and a['jump'] <= 0 and 'restAnim' not in a:
                self.setYoffset(a)

            if not a['moving'] and not a['gesturing'] \
               and not a['throwAnim'] and 'restAnim' not in a \
               and a['animTrans'] < 0 and ('poseFlash' not in a or \
                                           a['poseFlash'] > self.flashKF[-1][0]):

                breathRate = 0.5 # Between 0.5 and 1 is best

                breathRate *= (0.9, 1.1, 1, 1.12, 1.02, 1.08, 1.05, 0.98, 0.92)[a['id']]

                self.stepPoseLoop(a, a['obj'], self.idlingTest,
                                  self.frameTime * (breathRate + 0.6)/2,
                                  loop=True, timer='poseIdle',
                                  offsetMult=breathRate * 0.9)

                a['tempPose'] = a['rig'].b0.exportPose()
                a['rig'].interpPose(a['tempPose'], self.idle, 1 - breathRate * 0.9)

                if CURRTIME + a['animTrans'] < 0.5:
                    fact = (CURRTIME + a['animTrans']) / 0.5

                    a['tempPose'] = a['rig'].b0.exportPose()
                    a['rig'].interpPose(self.idle, a['tempPose'], fact)

                    off = (1-fact) * a['b1TempOff'] + fact * a['animOffset']
                    a['b1'].offset[:3] += off - a['animOffset']
                    a['b1'].lastOffset = off
                    a['animOffset'] = off

            # Include throwing for leg IK
            if not a['moving'] and not a['gesturing'] \
               and 'restAnim' not in a and a['animTrans'] < 0:

                a["rig"].b0.getTransform()

                footSize = (0.2, 0.1, 0.2, 0.1, None, 0.2, 0.08, 0.16, 0.16)[a['id']]

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

            if self.fCam and a['id'] == self.selchar:
                torso = a['b1'].children[0]
                head = a['b1'].children[0].children[2]
                ang = head.angles
                ang[1] = 0
                ang[2] = -asin(self.vv[1]) - torso.angles[2]
                head.rotate(ang)

            self.updateRig(a["rig"], a["ctexn"], a["num"], a["obj"])

            if not a["fCam"]:
                a["cr"] += a["cv"] * self.frameTime

            a["b1"].rotate([0,a["cr"],0])
            a["movingOld"] = a["moving"]

        self.frameProfile('PlayerMove')

        if not self.VRMode:
            self.pos = self.players[sc]["b1"].offset[:3] + np.array((0,0.5,0)) - 4 * self.vv
            self.pos[1] += self.players[sc]['legIKoffset']
            self.pos -= self.players[sc]['animOffset']

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
            if not self.VRMode and not self.cam1P:
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

        self.frameProfile('Postprocess')


    def debugOverlay(self):
        if not self.showAINav: return
        if self.stage in (0, 2): return

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

        self.rgb = np.array(self.rgb)
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
        fps = app.frameNum/app.totTime
        print("avg fps:", fps)

if __name__ == "__main__":
    mp.set_start_method('spawn')
    run()
