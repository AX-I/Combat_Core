# Taiga

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain, VertModel
from TexObjects import TexSkyBox

import random
import numpy.random as nr

import Phys


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

    self.directionalLights.append({"dir":[pi*1.7, 0.54], "i":[0.3,0.4,0.6]})
    self.directionalLights.append({"dir":[pi*1.7, 0.54+pi], "i":[0.1,0.1,0.1]})
    self.directionalLights.append({"dir":[pi*1.7, 0.54], "i":[0.1,0.1,0.1]})
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.1,0.2]})

    self.skyTex = np.zeros((1,6,3),"uint16")

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}
