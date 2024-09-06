# New Stage

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertWater0, VertTerrain0, VertModel, VertPlane
from TexObjects import TexSkyBox
from PIL import Image
import time

import Anim
import Phys
from Utils import viewVec

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def getRenderMask(self, rm):
    try: t = time.time() - self.transStart
    except: t = 0

    if t > 2:
        r = list(rm)
        if t > 3:
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
        if t > 0.5:
            r[self.sandstoneBricksTex] = False
        return r

def setupStage(self):
    tsize = 320
    tscale = 100 / tsize
    coords = [10 + tsize*tscale/2, -3.15, 20 + tsize*tscale/2]
    self.terrain = VertTerrain0(coords, PATH+"../Models/Temple/HeightNewL.png",
                                scale=tscale, vertScale=42.5)

    self.t2 = Phys.TerrainCollider(coords, self.terrain.size[0],
                                   self.terrain.heights, tscale)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    self.addVertObject(VertModel, [10, 0, 20], rot=(0,-pi/2,0),
                       filename=PATH+"../Models/Temple/Temple9test.obj",
                       shadow="CR", mip=2,
                       blender=True)

    self.addVertObject(VertModel, [10,-0.05,20], rot=(0,-pi/2,0),
                       filename=PATH+"../Models/Temple/TempleTrans.obj",
                       shadow="CR")

    for f in self.vtNames:
        mat = self.matShaders[self.vtNames[f]]
        if 'Water' in f:
            mat['shader'] = 'SSR'
            self.vertObjects[self.vtNames[f]].castShadow = False
            self.water = VertWater0(
                (0,0,0), self, pScale=0.04,
                wDir=[(-0.4,0.17), (-0.4, -0.2)],
                wLen=[(10, 4, 3), (7, 5, 2)],
                wAmp=np.array([(0.8, 0.5, 0.3), (0.6, 0.35, 0.25)])*1.6,
                wSpd=np.array([(0.6, 0.8, 1.1), (1, 1.1, 1.3)])*1.8, numW=3)
            self.water.texNum = self.vtNames[f]
        if 'Plant' in f or '093' in f or 'BushTest' in f or 'ForestBg' in f:
            mat['args']['translucent'] = 1
        if 'Plant' in f:
            mat['alphaMip'] = 2
        if 'Flower' in f or 'ce0a' in f:
            mat['args']['translucent'] = 1
        if 'Flame' in f:
            self.flameMTL = self.vtNames[f]
            self.matShaders[self.flameMTL].update(shader='add', noline=1,
                                                  args={'emPow': 4})
            self.vertObjects[self.flameMTL].castShadow = False
        if 'SandFloor' in f:
            mat['normal'] = 'sand_floor'
        if '3DRock' in f:
            mat['normal'] = '3DRock'
        if '095' in f:
            mat['normal'] = '096'
        if 'Ground' in f:
            mat['normal'] = 'Grass'


    pp1 = np.array((-14.5,15,24.))
    pp2 = np.array((-14.5,15,16.))
    pi1 = np.array((1,0.91,0.72)) * 30 * 0.4
    pi2 = np.array((0.48,0.99,1)) * 24 * 0.4

    ppc = np.array((-14.5,2.3,20))
    pic = np.array((1,1,1.))
    self.envPointLights = [{'i':pi1, 'pos':pp1},
                           {'i':pi2, 'pos':pp2},
                           {'i':pic, 'pos':ppc}]

    # Torches
    fi = np.array((1,0.45,0.04)) * 10
    self.envPointLights.extend([
        {'i':fi, 'pos':(-6.3, 3.2,5.5)},
        {'i':fi, 'pos':(-22.7,3.2,5.5)},
        {'i':fi, 'pos':(-6.3, 3.2,34.5)},
        {'i':fi, 'pos':(-22.7,3.2,34.5)}
    ])

    # Will transition to this
    self.DIR0I = np.array([1.72,1.5,0.6]) * 2
    self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6], "i":self.DIR0I})
    # First bounce
    self.DIR1I = np.array([0.22,0.24,0.2]) * 0.7
    self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6+pi], "i":self.DIR1I})
    # Second bounce
    self.DIR2I = np.array([0.14,0.12,0.08])
    self.directionalLights.append({"dir":[pi*2/3, 2.8], "i":self.DIR2I})
    # Sky light
    self.DIR3I = np.array([0.04,0.12,0.24])
    self.directionalLights.append({"dir":[0, pi/2], "i":self.DIR3I})
    self.DIR4I = np.array([0.1,0.25,0.4]) * 0.4
    self.directionalLights.append({"dir":[pi*2/3+0.1, 2.1], "i":self.DIR4I})


    fn = "../Skyboxes/approaching_storm_1k.ahdr"
    self.skyBox = self.makeSkybox(TexSkyBox, 12, PATH+fn, hdrScale=12)

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['args'].update(isEqui=1,rotY=0.25)

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

    self.si.put({'Preload':[PATH+"../Sound/Forest5.ogg",
                            PATH+"../Sound/Forest4_Reverb.ogg",
                            PATH+"../Sound/NoiseOpen.flac",
                            PATH+"../Sound/ForestNoise.flac"]})

def setupPostprocess(self):
    # Sun glare
    self.addVertObject(VertPlane, [-1,-1,0],
            h1=[2,0,0], h2=[0,2,0], n=1,
            texture=PATH+'../Assets/DirtMaskTex_2x.webp',
            texMul=0.4, useShaders={'2d':1, 'shader':'lens', 'args':{'mul':0.5}})

def changeMusic(self):
    self.si.put({"Play":(PATH+"../Sound/Forest5.ogg", self.volm, True,
                         (np.array((-14.5,3,20.)), 20, 4, 0.4, 6))})

    reverb = PATH+"../Sound/Forest4_Reverb.ogg"

    # Front L/R
    self.si.put({"Play":(reverb, self.volm, True,
                         (np.array((10,3,40.)), 12, 8, True))})
    self.si.put({"Play":(reverb, self.volm, True,
                         (np.array((10,3,0.)), 12, 8, True))})
    # Back L/R
    self.si.put({"Play":(reverb, self.volm, True,
                         (np.array((-40,3,40.)), 12, 8, True))})
    self.si.put({"Play":(reverb, self.volm, True,
                         (np.array((-40,3,0.)), 12, 8, True))})
    self.changedMusic = 2

def changeNoise(self):
    self.si.put({"Play":(PATH+"../Sound/ForestNoise.flac", self.volmFX, True,
                         (np.array((55, 12, 20.)), 70, 16, 1.0))})
    self.changedMusic = 1

def testTempleTrans(self):
    try:
        t = time.time() - self.transStart
    except:
        t = -1
        for p in self.actPlayers:
            if self.isClient: break
            pos = self.players[p]['b1'].offset[:3]
            if Phys.eucDist(pos, (-14.5, 2.4, 20)) < 1:
                self.lightTest()
                t = 0

    self.draw.setUVOff(self.flameMTL, (0,0), (1,1),
                       (-int(t*14)//5*0.2, int(t*14-1)*0.2))

    if t > 10:
        # Fade out sky light if inside temple
        pos = self.players[self.selchar]['b1'].offset[:3]

        # Border x: (-30, 7)
        f = max(0, min(1, (pos[0] - 5)/8)) + max(0, min(1, (-30 - pos[0])/8))
        # Border z: (3, 35)
        f += max(0, min(1, (pos[2] - 32)/8)) + max(0, min(1, (5 - pos[2])/8))

        # f is 1 outside, 0 inside
        f = min(1, f)

        di = np.array(self.directionalLights[4]['i'])
        do = self.DIR4I
        self.directionalLights[4]['i'] = di * 0.9 + do * max(0.2, f) * 0.1

        di[:] = self.directionalLights[3]['i']
        do[:] = self.DIR3I
        self.directionalLights[3]['i'] = di * 0.8 + do * max(0.3, f) * 0.2

        # Fade out bounce light too
        di[:] = self.directionalLights[1]['i']
        do[:] = self.DIR1I
        self.directionalLights[1]['i'] = di * 0.8 + do * max(0.4, f) * 0.2

        # Fade out fog too
        di = self.matShaders[self.fogMTL]['args']['fogLight']
        do = 0.015
        fdist = di * 0.9 + do * max(0.4, 1-f) * 0.1
        self.matShaders[self.fogMTL]['args']['fogLight'] = fdist
        self.draw.changeShader(self.fogMTL, self.matShaders[self.fogMTL])

        return

    if t > 6 and self.changedMusic == 1:
        changeMusic(self)
    if t > 6 and not self.changedShader:
        sbt = self.sandstoneBricksTex
        self.matShaders[sbt] = {'shader':'sh', 'args':{}, 'normal':'sand_blocks'}
        self.draw.changeShaderZ(self.sandstoneBricksTex, {})
        self.draw.changeShader(sbt, self.matShaders[sbt], stage=self.stage)
        self.changedShader = True
    if t > 2.2 and self.changedMusic == 0:
        changeNoise(self)
    if t > 2:
        self.matShaders[self.clouds.texNum].update(shader='add', args={'emPow':0.02})
    if 6 > t > 0:
        self.matShaders[self.sandstoneBricksTex] = {
            'shader':'dissolve',
            'args':{'fadeOrigin':(-14.5,0.5,20), 'fadeFact':8 * t}}
        self.draw.changeShaderZ(self.sandstoneBricksTex,
                                self.matShaders[self.sandstoneBricksTex])

    # rest 1, peak 600
    pointKF = [(0, 1), (0.4, 600), (1, 600), (3, 400), (4, 180),
               (5, 90), (6, 42), (7, 20), (8.5, 5), (10, 1)]
    self.envPointLights[2]['i'] = np.array((1,1,1.)) * Anim.interpAttr(t, pointKF)


    d = self.directionalLights[0]
    dirKF = [(0, np.array([0.6,0.6,0.6])), (1, np.array([3.,3.,3.])),
             (4, np.array([2.,2.,2.])), (10, self.DIR0I)]

    d['i'] = Anim.interpAttr(t, dirKF)

    fogKF = [(0,   np.array((0.4, 0.2,400, 1))),
             (0.8, np.array((1.6, 0.3,400, 1))),
             (2,   np.array((1.6, 0.2,400, 1))),
             (5, np.array((0.1, 0.01, 80,  0.6))),
             (9, np.array((0.015,0.002,40, 0)))]

    fparams = Anim.interpAttr(t, fogKF)

    self.matShaders[self.fogMTL]['args'].update(
        fogLight=fparams[0],
        fogAbsorb=fparams[1],
        fogDist=fparams[2],
        fogScatter=fparams[3])
    self.draw.changeShader(self.fogMTL, self.matShaders[self.fogMTL])

    self.draw.setPrimaryLight(np.array([d["i"]]), np.array([viewVec(*d["dir"])]))

    if 0 < t < 3:
        tempObjs = np.array(self.castObjs)
        tempObjs = tempObjs * (1 - np.array(self.testRM()))
        self.shadowMap(0, tempObjs, bias=0.5)

    for p in self.actPlayers:
        a = self.players[p]
        dist = Phys.eucDist(a['b1'].offset[:3], (-14.5, 2, 20))
        if t > (dist/40) and 'poseFlash' in a \
           and a['poseFlash'] <= self.flashKF[-1][0]:
            a['moving'] = False
            a['animTrans'] = -1

            step = self.frameTime / (1 + dist/30 * (1 - (t > 4)))
            self.stepPoseLoop(a, a['obj'], self.flashKF, step,
                              loop=False, timer='poseFlash')

def frameUpdate(self):
    testTempleTrans(self)

    if self.frameNum == 1:
        tpath = PATH + '../Models/Temple/'
        self.addNrmMap(tpath + 'SandstoneBricks_nrm.jpg', 'sand_blocks', mip=True)
        self.addNrmMap(tpath + 'sandstone_cracks_nor_gl_1k.png', 'sand_floor')
        self.addNrmMap(PATH + '../Models/TaigaNew/3DRock004_Normal.jpg', '3DRock')
        self.addNrmMap(tpath + '096.png', '096')
        self.addNrmMap(tpath + 'Grass004_1K_NormalGL.png', 'Grass', mip=True, mipLvl=4)
        self.matShaders[self.fogMTL]['args']['fogAmbDistFac'] = 4
