# Taiga

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain, VertModel
from TexObjects import TexSkyBox

import random
import numpy.random as nr

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):
    mpath = PATH + '../Models/'

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
            c = np.array((i, 0, j), dtype="float")
            c += nr.rand(3) * 8
            c[1] = self.terrain.getHeight(c[0],c[2]) - 0.4
            r = random.random() * 3
            self.addVertObject(VertModel, c, **options, rot=(0,r,0))

    LInt = np.array([0.5,0.2,0.15]) * 2.8
    self.directionalLights.append({"dir":[pi*1.7, 0.1], "i":LInt})
    self.directionalLights.append({"dir":[pi*1.7, 0.1+pi], "i":[0.12,0.08,0.1]})
    self.directionalLights.append({"dir":[pi*1.7, 0.1], "i":[0.12,0.1,0.08]})
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.14,0.18,0.5]})


    fn = "../Skyboxes/kiara_1_dawn_1k.ahdr"
    self.skyBox = TexSkyBox(self, 12, PATH+fn, hdrScale=6)
    self.skyBox.created()

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['isEqui'] = 1
    skyShader['rotY'] = 0.25


    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}
