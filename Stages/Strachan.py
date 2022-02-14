# Strachan

import numpy as np
from math import pi, sin
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel, VertSphere, VertPlane, VertRing
from TexObjects import TexSkyBox
from PIL import Image
import time

import Phys

SFX = '../Sound/Misc/'

def getTexN(obj):
    tn = [obj.texNum]
    while obj.nextMtl is not None:
        obj = obj.nextMtl
        tn.append(obj.texNum)
    return tn

def getRenderMask(self, rm):
    if not self.showPlatforms:
        for i in self.platTexn:
            rm[i] = True
    return rm

def setupStage(self):
    PX = 10
    PZ = 10
    PA = np.array([(PX,0,PZ)], 'float')

    self.stagePlatforms = np.array([(2, 5,   -4),
                                    (0, 4.5, 0),
                                    (-1,5.5, 3.5),
                                    (-2,5,   7.5)]) + PA


    self.addVertObject(VertModel, [PX,0,PZ], rot=(0,0,0),
                       filename="../Models/Strachan/T10.obj",
                       scale=1, mip=2,
                       useShaders={"cull":1},
                       shadow="CR")

    for f in self.vtNames:
        if "Chandelier" in f:
            self.matShaders[self.vtNames[f]]['emissive'] = 4.0
        if "Glass" in f:
            self.matShaders[self.vtNames[f]]['add'] = 0.04
            self.matShaders[self.vtNames[f]]['noline'] = True
            self.matShaders[self.vtNames[f]]['cull'] = 1
        if "Window" in f:
            if "Fro" in f or "Sid" in f:
                self.matShaders[self.vtNames[f]]['emissive'] = 4.0
            else:
                self.matShaders[self.vtNames[f]]['add'] = 1
                self.matShaders[self.vtNames[f]]['noline'] = True
            self.vertObjects[self.vtNames[f]].castShadow = False
        if "Metal" in f:
            self.matShaders[self.vtNames[f]]['spec'] = 0.6
        if "Wood066" in f:
            self.matShaders[self.vtNames[f]]['SSR'] = 2
        elif "Wood_Ceil" in f:
            pass
        elif "Wood" in f:
            self.matShaders[self.vtNames[f]]['spec'] = 1

        if "Silver" in f:
            self.matShaders[self.vtNames[f]]['metal'] = {'roughness':0.4}
        if "Transparent" in f:
            self.matShaders[self.vtNames[f]]['add'] = 0.002


    self.buttons = []
    for c in [(PX,0,PZ+32),(PX,5.02,PZ-17)]:
        self.addVertObject(VertModel, c,
                           filename="../Models/Strachan/Button.obj",
                           useShaders={"cull":1},
                           shadow='R')

        self.buttons.append({
            'obj': self.vertObjects[-1],
            'pos': 0, 'fullyPressed': False, 'fullyLifted': True,
        })

    for p in self.stagePlatforms:
        self.addVertObject(VertModel, p,
                           scale=0.85,
                           filename='../Models/Strachan/Floating2.obj',
                           mip=2, useShaders={'cull':1},
                           shadow='CR')
        self.addVertObject(VertSphere, p, scale=0.4,
                           n=8, texture="../Models/Strachan/Glass.png")
        self.addVertObject(VertSphere, p, scale=0.3,
                           n=6, texture="../Models/Strachan/Glass.png")

    if len(self.stagePlatforms) > 0:
        glass = self.vertObjects[-1].texNum
        self.matShaders[glass]['add'] = 0.001
        self.matShaders[glass]['noline'] = True
        self.platGlass = glass

        self.platTexn = getTexN(self.vertObjects[-3]) + [glass]

    self.w.addCollider(Phys.PlaneCollider((PX, 5, PZ-16),
                                          (0,0,3),(10,0,0)))

    for f in self.vtNames:
        if "Gold" in f:
            self.matShaders[self.vtNames[f]]['metal'] = {'roughness':0.5}

    self.pillars = []
    for i in range(6):
        self.addVertObject(VertModel, [PX+7.2,0,PZ-10 + 5.8*i],
                           filename="../Models/Strachan/TablePillar.obj",
                           mip=2, useShaders={"cull":1},
                           shadow="CR")
        self.pillars.append(self.vertObjects[-1])
        self.addVertObject(VertModel, [PX-5,0,PZ-10 + 5.8*i],
                           filename="../Models/Strachan/TablePillar.obj",
                           rot=(0,pi,0),
                           mip=2, useShaders={"cull":1},
                           shadow="CR")

    for f in self.vtNames:
        if "Wood066" in f and not "066P" in f:
            self.matShaders[self.vtNames[f]]['SSR'] = 2

    self.pillars.reverse()
    pa = self.vertObjects[-1]
    self.pillarTexn = getTexN(pa)

    tsize = 512
    hscale = 56
    tscale = hscale / tsize
    coords = (PX - tsize*tscale/2, -0.4, PZ - tsize*tscale/2 + 8)

    self.terrain = VertTerrain0(coords,
                                "../Models/Strachan/Height.png",
                                scale=tscale, vertScale=hscale+1,
                                maxInf=True)

    self.t2 = Phys.TerrainCollider(coords, self.terrain.size[0],
                                   self.terrain.heights, tscale)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

    DInt = np.array([2.0,1.77,1.33]) * 1.2
    RInt = np.array([0.2,0.15,0.1])
    RInt2 = np.array([0.08,0.06,0.04])
    self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":DInt})
    self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":RInt})
    self.directionalLights.append({"dir":[pi*2/3, -2.5], "i":RInt2})


    fi = np.array((1,0.6,0.25)) * 30
    self.envPointLights.extend([
        # Chandeliers
        {'i':fi, 'pos':(5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,24+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,24+PZ)},
        # Kitchen
        {'i':fi/2, 'pos':(-14+PX,4,22+PZ)},
    ])

    si = np.array((0.5,0.75,1)) * 50
    sv = np.array((-0.5,-0.5,0))
    sv /= Phys.eucLen(sv)
    for i in range(7):
        self.spotLights.append({'i':si, 'pos':(10+PX, 9.5, 8*(i-2)+PZ),
                                'vec':sv})

    si = np.array((0.55,0.75,0.95)) * 50
    sv = np.array((0.8,-0.2,0))
    sv /= Phys.eucLen(sv)
    self.spotLights.append({'i':si*0.6, 'pos':(-27+PX, 2.5, 16.8+PZ),
                            'vec':sv})
    self.spotLights.append({'i':si*0.6, 'pos':(-27+PX, 2.5, 23.8+PZ),
                            'vec':sv})


    self.addVertObject(VertPlane, [-1,-1,0],
            h1=[2,0,0], h2=[0,2,0], n=1,
            texture=PATH+'../Assets/Blank3.png',
            useShaders={'2d':1, 'lens':1})


    self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Autumn_Park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    self.skyBox.created()

    self.showPillars = -1
    self.showPlatforms = False

def movePillars(self, i):
    btn = self.buttons[i]
    if btn['fullyLifted']:
        self.si.put({'Play':(SFX+'brick_scrape2.wav', self.volmFX, False,
                             (np.array((10,0,42)), 4, 6, True))})
        btn['fullyLifted'] = False

    if self.showPillars == -1:
        self.si.put({'Play':(SFX+'chaingrind.wav', self.volmFX, False,
                             (np.array((12,-2,10)), 80, 8, True))})

    self.showPillars = max(0, self.showPillars)

    tr = np.array([0,-0.2*self.frameTime,0])

    if btn['pos'] < -0.1:
        btn['fullyPressed'] = True
        return
    btn['pos'] += tr[1]
    b = btn['obj']
    self.draw.translate(tr, b.cStart*3, b.cEnd*3, b.texNum)

def showPlatforms(self):
    if self.showPlatforms > 0:
        return
    for p in self.stagePlatforms:
        self.w.addCollider(Phys.CircleCollider(0.6, p))
    self.showPlatforms = time.time()

    # restore materials after dissolve in
    self.platMats = {i:self.matShaders[i] for i in self.platTexn}
    self.platFullyAppeared = False

def testPlatforms(self):
    if self.showPlatforms == 0:
        return

    t = time.time() - self.showPlatforms

    if t > 2.5:
        if self.platFullyAppeared:
            return
        self.platFullyAppeared = True
        for i in self.platTexn[:-1]:
            self.matShaders[i] = self.platMats[i]
            self.draw.changeShaderZ(i, {})
            self.draw.changeShader(i, self.matShaders[i], stage=self.stage)
        return

    self.matShaders[self.platGlass]['add'] = 0.04 * min(1, (t / 2.5))

    for i in self.platTexn[:-1]:
        self.matShaders[i] = {
            'dissolve':{'origin':(10,4,6), 'fact':np.float32(5*t)}}
        self.draw.changeShaderZ(i, self.matShaders[i])



def frameUpdate(self):
    if self.frameNum < 2:
        return

    buttonPressed = False
    for p in self.actPlayers:
        if self.isClient: break
        pos = self.players[p]['b1'].offset[:3]
        if Phys.eucDist(pos, (10, 1, 42)) < 0.8:
            movePillars(self, 0)
            buttonPressed = 1
        if Phys.eucDist(pos, (10, 6, -7)) < 0.8:
            movePillars(self, 1)
            showPlatforms(self)
            buttonPressed = 2

    testPlatforms(self)

    mov = 0.2 * self.frameTime
    tr = np.array([0,mov,0])

    for i in range(len(self.buttons)):
        btn = self.buttons[i]
        if not (buttonPressed - 1) == i and btn['pos'] < 0:
            if btn['fullyPressed']:
                self.si.put({'Play':(SFX+'brick_scrape2.wav', self.volmFX, False,
                                 (np.array((10,0,42)), 4, 6, True))})
                btn['fullyPressed'] = False
            b = btn['obj']
            btn['pos'] += mov
            self.draw.translate(tr, b.cStart*3, b.cEnd*3, b.texNum)
        if btn['pos'] >= 0:
            btn['fullyLifted'] = True

    if self.showPillars < 0:
        return
    if self.showPillars >= 1000:
        return
    if self.showPillars > 0.7:
        self.showPillars = 1000
        self.si.put({'Play':(SFX+'metal_hit4.wav', self.volmFX, False,
                             (np.array((20,-5,10)), 120, 8, True))})
        self.si.put({'Play':(SFX+'metal_hit6.wav', self.volmFX, False,
                             (np.array((12,-5,10)), 160, 8, True))})
        return

    self.showPillars += mov

    # terrain scale
    tScale = self.terrain.scale
    # dimensions of table
    pSize = np.array((2.8, 0, 1))

    for i in range(len(self.pillars)):
        p = self.pillars[i]

        tmin = (p.coords - pSize - self.terrain.coords) / tScale
        tmax = (p.coords + pSize - self.terrain.coords) / tScale
        self.terrain.heights[int(tmin[0]):int(tmax[0]),
                             int(tmin[2]):int(tmax[2])] += mov*i / tScale
        self.t2.pts[int(tmin[0]):int(tmax[0]),
                    int(tmin[2]):int(tmax[2])] += tr*i

        for tn in self.pillarTexn:
            self.draw.translate(tr*i, p.cStart*3, p.cEnd*3, tn)
            p = p.nextMtl

    tempObjs = np.array(self.castObjs)
    tempObjs = tempObjs * (1 - np.array(self.testRM()))

    self.shadowMap(0, tempObjs, bias=self.shadowCams[0]["bias"])

def getHeight(self, pos):
    r = 0.8
    R = r + 2
    if self.showPlatforms:
        for p in self.stagePlatforms:
            if Phys.eucDist(pos, p) < R:
                if pos[1] > p[1]:
                    if Phys.eucLen((pos - p) * np.array([1,0,1])) < r:
                        z = p[1] + r + 0.2
                        return z

    if 0 < pos[0] < 20 and pos[1] > 5 and -10 < pos[2] < -2:
        return 5

    return self.terrain.getHeight(*pos[::2])
