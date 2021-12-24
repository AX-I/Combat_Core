# Strachan

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel
from TexObjects import TexSkyBox
from PIL import Image

import Phys


def setupStage(self):
    PX = 10
    PZ = 10

    self.addVertObject(VertModel, [PX,0,PZ], rot=(0,0,0),
                       filename="../Models/Strachan/Test6.obj",
                       scale=1, mip=2,
                       useShaders={"cull":1},
                       #subDiv=1,
                       shadow="CR")

    for f in self.vtNames:
        if "Chandelier" in f:
            self.matShaders[self.vtNames[f]]['emissive'] = 4.0
        if "Glass" in f:
            self.matShaders[self.vtNames[f]]['add'] = 0.04
            self.matShaders[self.vtNames[f]]['noline'] = True
            self.matShaders[self.vtNames[f]]['cull'] = 1
        if "Window" in f:
            self.matShaders[self.vtNames[f]]['add'] = 0.7
            self.matShaders[self.vtNames[f]]['noline'] = True
            self.vertObjects[self.vtNames[f]].castShadow = False
        if "Wood066" in f:
            self.matShaders[self.vtNames[f]]['SSR'] = 2
        elif "Wood_Ceil" in f:
            pass
        elif "Wood" in f:
            self.matShaders[self.vtNames[f]]['spec'] = 1

    self.terrain = VertTerrain0([0,-0.4,0],
                                np.zeros((32,32)),
                                scale=1, vertScale=20)

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

    self.t2 = Phys.TerrainCollider([0,-0.3,0], self.terrain.size[0],
                                   self.terrain.heights, 1)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":[2.0,1.77,1.33]})
    self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":[0.2,0.15,0.1]})

    fi = np.array((1,0.6,0.3)) * 20
    self.envPointLights.extend([
        {'i':fi, 'pos':(5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,16+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,16+PZ)},
    ])

    si = np.array((0.5,0.75,1)) * 60
    sv = np.array((-0.5,-0.5,0))
    sv /= Phys.eucLen(sv)
    for i in range(5):
        self.spotLights.append({'i':si, 'pos':(10+PX, 9, 8*(i-2)+PZ),
                                'vec':sv})

    self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Autumn_Park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    self.skyBox.created()
