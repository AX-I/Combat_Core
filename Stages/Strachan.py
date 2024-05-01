# Strachan

import numpy as np
from math import pi, sin
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel, VertSphere, VertPlane, VertRing
from TexObjects import TexSkyBox
from PIL import Image
import time
from ParticleSystem import CentripetalParticleSystem

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
        rm[self.ringTest.texNum] = True
    return rm

def setupStage(self):
    PX = 10
    PZ = 10
    PA = np.array([(PX,0,PZ)], 'float')

    self.stagePlatforms = np.array([(-1, 5,   -4),
                                    (0.5,4.5, 0),
                                    (2,  5.5, 4),
                                    (1.5,5,   8.5)]) + PA
    self.stagePlatformPS = []


    self.addVertObject(VertModel, [PX,0,PZ], rot=(0,0,0),
                       filename="../Models/Strachan/T10.obj",
                       scale=1, mip=2,
                       useShaders={"cull":1},
                       shadow="CR")

    for f in self.vtNames:
        mat = self.matShaders[self.vtNames[f]]
        if "Chandelier" in f:
            mat.update(shader='emissive', args={'emPow':4.0})
            self.chandelierMat = self.vtNames[f]
        if "Glass" in f:
            mat.update(shader='add', noline=True, cull=1, args={'emPow':0.04})
        if "Window" in f:
            if "Fro" in f or "Sid" in f:
                mat.update(shader='emissive', args={'emPow':4.0})
            else:
                mat.update(shader='add', noline=True, args={'emPow':1})
            self.vertObjects[self.vtNames[f]].castShadow = False
        if "Metal" in f:
            mat['args']['specular'] = 0.6
        if "Wood066" in f:
            mat['shader'] = 'SSRopaque'
        elif "Wood_Ceil" in f:
            mat.update(noise=1, normal='wood_coffers')
        elif "Wood" in f:
            mat.update(noise=1, args={'specular': 0.5})#, 'roughness': 0.002})
        elif 'Wtest' in f or 'Material' in f or 'GraySt' in f or 'Turq' in f:
            mat['noise'] = 1
        if 'Wtest' in f:
            self.vtextures[self.vtNames[f]] = (self.vtextures[self.vtNames[f]]*1.2).astype('uint16')
            #mat.update({'spec': 0.02, 'roughness': 0.002})
        if "Silver" in f:
            mat.update(shader='metallic', args={'roughness':0.4})
        if "Transparent" in f:
            mat.update(shader='add', args={'emPow':0.002})

        if 'floor' in f:
            mat['noise'] = 1


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
        tg = "../Assets/Blob.png"
        self.addVertObject(VertSphere, p, scale=0.7,
                           n=16, texture=tg)
        self.addVertObject(VertSphere, p, scale=-0.5,
                           n=12, texture=tg)

    if len(self.stagePlatforms) > 0:
        glass = self.vertObjects[-1].texNum
        self.matShaders[glass].update(shader='special', noline=1, args={'emPow':0.1})
        self.platGlass = glass

        self.platTexn = getTexN(self.vertObjects[-3]) + [glass]

    self.w.addCollider(Phys.PlaneCollider((PX, 5, PZ-16),
                                          (0,0,3),(10,0,0)))

    self.addVertObject(VertModel, self.stagePlatforms[-1] + np.array([0,1.2,0]),
                       scale=(-1,1,1), filename='../Models/Strachan/Ring.obj',
                       useShaders={'shader':'add','args':{'emPow':4}, 'noline':1})
    self.addVertObject(VertModel, self.stagePlatforms[-1] + np.array([0,1.3,0]),
                       scale=1.3, filename='../Models/Strachan/Ring.obj',
                       rot=(0,pi/3,0),
                       useShaders={'shader':'add','args':{'emPow':4}, 'noline':1})
    self.ringTest = self.vertObjects[-1]

    for f in self.vtNames:
        if "Gold" in f:
            self.matShaders[self.vtNames[f]].update(
                shader='metallic', args={'roughness':0.5})

    self.pillars = []
    for i in range(6):
        self.addVertObject(VertModel, [PX+7.2,0,PZ-10 + 5.8*i],
                           filename="../Models/Strachan/TablePillar.obj",
                           mip=2, useShaders={"cull":1},
                           shadow="CR")
        self.addVertObject(VertModel, [PX-5,-0.01,PZ-10 + 5.8*i],
                           filename="../Models/Strachan/TablePillar.obj",
                           rot=(0,pi,0),
                           mip=2, useShaders={"cull":1},
                           shadow="CR")
        self.pillars.append(self.vertObjects[-1])

    for f in self.vtNames:
        if "Wood066" in f and not "066P" in f:
            self.matShaders[self.vtNames[f]]['shader'] = 'SSRopaque'
        if 'WoodT' in f:
            self.matShaders[self.vtNames[f]]['noise'] = 1

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

    DInt = np.array([2.0,1.6,1.]) * 1.5
    RInt = np.array([0.2,0.15,0.1])
    RInt2 = np.array([0.08,0.06,0.04])
    self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":DInt})
    self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":RInt})
    self.directionalLights.append({"dir":[pi*2/3, -2.5], "i":RInt2})


    fi = np.array((1,0.6,0.25)) * 20
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

    self.skyBox = self.makeSkybox(TexSkyBox, 12, PATH+"../Skyboxes/autumn_park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['args'].update(isEqui=1, rotY=3.27)

    self.showPillars = -1
    self.showPlatforms = False
    self.lightsToggled = False

    self.trackTime = -1
    self.pillarTrackTime = -1

def setupPostprocess(self):
    # Sun glare
    self.addVertObject(VertPlane, [-1,-1,0],
            h1=[2,0,0], h2=[0,2,0], n=1,
            texture=PATH+'../Assets/DirtMaskTex_2x.webp',
            texMul=0.4, useShaders={'2d':1, 'shader':'lens', 'args':{'mul':0.8}})

def movePillars(self, i):
    btn = self.buttons[i]
    if btn['fullyLifted']:
        self.si.put({'Play':(SFX+'brick_scrape2.wav', self.volmFX, False,
                             (np.array((10,0,42)), 4, 6, True))})
        btn['fullyLifted'] = False

    if self.showPillars == -1:
        self.si.put({'Play':(SFX+'chaingrind.wav', self.volmFX, False,
                             (np.array((12,-2,10)), 80, 8, True))})

        if time.time() - self.trackTime > 84:
            self.si.put({'Play':(SFX+'Sac_a.flac', self.volm, False)})
            self.pillarTrackTime = time.time()


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
        ps = CentripetalParticleSystem(p, (0, 0),
                                       nParticles=30, lifespan=1200,
                                       randPos=0.08, vel=0.0, randVel=0.0,
                                       size=0.08, opacity=0.9,
                                       color=(0.1,0.1,0.1), randColor=0,
                                       f=0.001, r=0.6, cc=1)
        ps.shader = 2
        self.addParticleSystem(ps)
        self.stagePlatformPS.append(ps)

    self.showPlatforms = time.time()

    # restore materials after dissolve in
    self.platMats = {i:self.matShaders[i] for i in self.platTexn}
    self.platFullyAppeared = False

def toggleLights(self):
    self.matShaders[self.chandelierMat].update(shader='emissive', args={'emPow':0.1})
    self.envPointLights = []
    self.directionalLights[2]['i'] *= 4
    FInt = np.array([0.5,0.3,0.1]) * 0.6
    self.directionalLights.append({'dir':[pi*2/3,pi*0.6], 'i':FInt})
    self.simpleShaderVert()
    self.lightsToggled = True

def testPlatforms(self):
    if self.showPlatforms == 0:
        return

    t = time.time() - self.showPlatforms

    self.draw.setUVOff(self.ringTest.texNum, (0,0), (1,1),
                       (0, t/3))
    self.matShaders[self.ringTest.texNum].update(args={'emPow': 2 + 2 * sin(t*2)})

##    if not self.lightsToggled:
##        for p in self.actPlayers:
##            if Phys.eucDist(self.players[p]['b1'].offset[:3],
##                            self.stagePlatforms[-1] + np.array([0,2,0])) < 1:
##                toggleLights(self)


    if t > 2.5:
        if self.platFullyAppeared:
            return
        self.platFullyAppeared = True
        for i in self.platTexn[:-1]:
            self.matShaders[i] = self.platMats[i]
            self.draw.changeShaderZ(i, {})
            self.draw.changeShader(i, self.matShaders[i], stage=self.stage)
        return

    self.matShaders[self.platGlass].update(args={'emPow': 0.04 * min(1, (t / 2.5))})

    for i in self.platTexn[:-1]:
        self.matShaders[i].update(shader='dissolve',
            args={'fadeOrigin':(10,4,6), 'fadeFact':np.float32(5*t)})
        self.draw.changeShaderZ(i, self.matShaders[i])



def frameUpdate(self):
    if self.frameNum < 2:
        self.addNrmMap(PATH + '../Models/Strachan/Wood_Ceiling_Coffers_002_nrm.png',
                       'wood_coffers')
        return


    if self.isClient:
        try:
            self.showPillars = self.stageFlags['showPillars']
            self.showPlatforms = self.stageFlags['showPlatforms']
            self.iceEffect = self.stageFlags['iceEffect']
        except: pass
    else:
        self.stageFlags['showPillars'] = self.showPillars
        self.stageFlags['showPlatforms'] = self.showPlatforms
        self.stageFlags['iceEffect'] = self.iceEffect



    CURRTIME = time.time()

    if self.showPlatforms > 0:
        for ps in self.stagePlatformPS:
            ps.step()

    if self.frameNum == 4:
        self.si.put({'Play':('../Sound/StrachanLoop.ogg', self.volm*0.6, True)})

    if self.frameNum == 10:
        #showPlatforms(self)
        self.si.put({'Play':('../Sound/F_3c.ogg', self.volm*0.9, False)})
        self.trackTime = CURRTIME

    if self.showPillars == 1000 and self.trackTime > 0 \
      and CURRTIME - self.trackTime > 84 \
      and CURRTIME - self.pillarTrackTime > 18:
        self.si.put({'Play':('../Sound/FE2a.ogg', self.volm*0.42, False)})
        self.trackTime = -1


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
