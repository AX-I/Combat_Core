# Atrium

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel
from TexObjects import TexSkyBox
from PIL import Image

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):
    self.addVertObject(VertModel, [13.32,0,20.4], rot=(0,0,0),
                       filename=PATH+"../Atrium/Atrium8AtlasOpt.obj",
                       scale=1.2, mip=2,
                       useShaders={"cull":1},
                       subDiv=1, shadow="CR")

    for f in self.vtNames:
        if "CV" in f:
            self.matShaders[self.vtNames[f]]['emissive'] = 1.0
        if "BackgroundLight" in f:
            self.matShaders[self.vtNames[f]]['add'] = 0.5
            self.matShaders[self.vtNames[f]]['noline'] = True
            self.matShaders[self.vtNames[f]]['cull'] = 1
        if "FieldBackground" in f:
            self.matShaders[self.vtNames[f]]['emissive'] = 2.0
        if 'AtlasG_opt' in f:
            self.matShaders[self.vtNames[f]]['spec'] = 1
            self.matShaders[self.vtNames[f]]['normal'] = 'AtlasG'
        if 'Copy' in f:
            self.ssrMTL = self.vtNames[f]
            self.matShaders[self.ssrMTL]['SSR'] = 2
            self.matShaders[self.ssrMTL]['roughness'] = 0.1
            self.matShaders[self.ssrMTL]['normal'] = 'AtlasG'
        if 'AtlasW' in f:
            self.matShaders[self.vtNames[f]]['spec'] = 1
            self.matShaders[self.vtNames[f]]['roughness'] = 0.4

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

    self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/autumn_park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    self.skyBox.created()

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['isEqui'] = 1
    skyShader['rotY'] = 3.27

    self.matShaders[self.ssrMTL]['envFallback'] = self.skyBox.texNum
    self.matShaders[self.ssrMTL]['rotY'] = skyShader['rotY']

def frameUpdate(self):
    if self.frameNum == 0:
        tpath = PATH + '../Atrium/'
        self.addNrmMap(tpath + 'AtlasG_opt_nrm.png', 'AtlasG', mip=True)
