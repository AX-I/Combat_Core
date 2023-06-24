# New Stage

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain, VertTerrain0, VertModel
from TexObjects import TexSkyBox
from PIL import Image

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):
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
    self.skyBox = self.makeSkybox(TexSkyBox, 12, PATH+"../Skyboxes/autumn_Park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['args'].update(isEqui=1, rotY=3.27)
