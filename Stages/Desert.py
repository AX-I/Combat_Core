# Desert

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain
from TexObjects import TexSkyBox

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):
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
    self.directionalLights.append({"dir":[pi*2/3, 2.1+pi], "i":[0.5,0.32,0.1]})
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.2,0.4]})
    self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Desert_2k.ahdr",
                            rot=(0,-pi/3,0), hdrScale=12)
    self.skyBox.created()

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}
