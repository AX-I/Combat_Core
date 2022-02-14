# New Stage

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertWater0, VertTerrain0, VertModel, VertPlane
from TexObjects import TexSkyBox
from PIL import Image

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

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
        if 'Plant' in f or '093' in f or 'BushTest' in f or 'ForestBg' in f:
            self.matShaders[self.vtNames[f]]['translucent'] = 1
        if 'Flower' in f or 'ce0a' in f:
            self.matShaders[self.vtNames[f]]['translucent'] = 1
        if 'Flame' in f:
            self.flameMTL = self.vtNames[f]
            self.matShaders[self.flameMTL] = {'add': 1.6, 'noline': 1}
            self.vertObjects[self.flameMTL].castShadow = False
        if 'Sandstone' in f:
            tm = self.vtextures[self.vtNames[f]] * 0.8
            self.vtextures[self.vtNames[f]] = tm.astype('uint16')

    pp1 = np.array((-14.5,15,24.))
    pp2 = np.array((-14.5,15,16.))
    pi1 = np.array((1,0.91,0.72)) * 30
    pi2 = np.array((0.48,0.99,1)) * 24

    ppc = np.array((-14.5,2.3,20))
    pic = np.array((1,1,1.))
    self.envPointLights = [{'i':pi1, 'pos':pp1},
                           {'i':pi2, 'pos':pp2},
                           {'i':pic, 'pos':ppc}]

    # Torches
    fi = np.array((1,0.6,0.35)) * 2
    self.envPointLights.extend([
        {'i':fi, 'pos':(-6.3, 3.2,5.5)},
        {'i':fi, 'pos':(-22.7,3.2,5.5)},
        {'i':fi, 'pos':(-6.3, 3.2,34.5)},
        {'i':fi, 'pos':(-22.7,3.2,34.5)}
    ])

    # Overwritten by transition
    self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6], "i":[1.8,1.6,0.9]})
    # First bounce
    self.directionalLights.append({"dir":[pi*2/3+0.14, 2.6+pi], "i":[0.22,0.24,0.2]})
    # Second bounce
    self.directionalLights.append({"dir":[pi*2/3, 2.8], "i":[0.14,0.12,0.08]})
    # Sky light
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.04,0.12,0.18]})
    self.directionalLights.append({"dir":[pi*2/3+0.1, 2.1], "i":[0.1,0.25,0.4]})

    # Sun glare
    self.addVertObject(VertPlane, [-1,-1,0],
            h1=[2,0,0], h2=[0,2,0], n=1,
            texture=PATH+'../Assets/Blank3.png',
            useShaders={'2d':1, 'lens':1})


    fn = "../Skyboxes/approaching_storm_1k.ahdr"
    self.skyBox = TexSkyBox(self, 12, PATH+fn, hdrScale=16)
    self.skyBox.created()

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['isEqui'] = 1
    skyShader['rotY'] = 0.25

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

    self.si.put({'Preload':[PATH+"../Sound/Forest5.wav",
                            PATH+"../Sound/Forest4_Reverb.wav",
                            PATH+"../Sound/NoiseOpen.wav",
                            PATH+"../Sound/ForestNoise.wav"]})
