# Strachan

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel, VertSphere
from TexObjects import TexSkyBox
from PIL import Image

import Phys


def setupStage(self):
    PX = 10
    PZ = 10
    PA = np.array([(PX,0,PZ)], 'float')
    self.stagePlatforms = np.array([(0,1,16),
                                    (0,2,19),
                                    (1,3,21),
                                    (0,5,23)]) + PA


    self.addVertObject(VertModel, [PX,0,PZ], rot=(0,0,0),
                       filename="../Models/Strachan/Test8A.obj",
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


    for p in self.stagePlatforms:
        self.addVertObject(VertSphere, p, scale=0.8,
                           n=8, texture="../Models/Strachan/DullTurq1.png")
        self.w.addCollider(Phys.CircleCollider(0.6, p))

    self.w.addCollider(Phys.PlaneCollider((PX, 5, PZ-16),
                                          (0,0,3),(10,0,0)))

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

    DInt = np.array([2.0,1.77,1.33])
    self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":DInt})
    self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":[0.2,0.15,0.1]})

    fi = np.array((1,0.6,0.25)) * 30
    self.envPointLights.extend([
        {'i':fi, 'pos':(5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,-8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,8+PZ)},
        {'i':fi, 'pos':(5+PX,7.5,24+PZ)},
        {'i':fi, 'pos':(-5+PX,7.5,24+PZ)},
        {'i':fi/2, 'pos':(-14+PX,4,22+PZ)},
    ])

    si = np.array((0.5,0.75,1)) * 50
    sv = np.array((-0.5,-0.5,0))
    sv /= Phys.eucLen(sv)
    for i in range(7):
        self.spotLights.append({'i':si, 'pos':(10+PX, 9.5, 8*(i-2)+PZ),
                                'vec':sv})

    self.skyBox = TexSkyBox(self, 12, PATH+"../Skyboxes/Autumn_Park_2k.ahdr",
                            rot=(0,0,0), hdrScale=48)
    self.skyBox.created()

def getHeight(self, pos):
    r = 0.8
    R = r + 2
    for p in self.stagePlatforms:
        if Phys.eucDist(pos, p) < R:
            if pos[1] > p[1]:
                if Phys.eucLen((pos - p) * np.array([1,0,1])) < r:
                    z = p[1] + r + 0.2
                    return z

    if 0 < pos[0] < 20 and pos[1] > 5 and -10 < pos[2] < -2:
        return 5

    return self.terrain.getHeight(*pos[::2])
