# Desert

import numpy as np
from math import pi,sin
from OpsConv import PATH
import time

from VertObjects import VertTerrain, VertPlane
from TexObjects import TexSkyBox

import Phys
import PhysCloth

VIEWER = None

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):

    self.addVertObject(VertTerrain, [-10, 0, -10],
                    heights=PATH+"../Assets/TerrainA.png",
                    texture=PATH+"../Assets/aerial_beach_01_diff_2k.jpg",
                    scale=0.375, vertScale=26,
                    shadow="CR", mip=2,
                    uvspread=20, useShaders={'normal':'sand'})
    self.terrain = self.vertObjects[-1]


    nCloth = 16
    self.nCloth = nCloth
    self.addVertObject(VertPlane, [20,7,20],
                       n=nCloth, h2=[2,0,1.5], h1=[0.2,-2,0.1],
                       texture=PATH+'../Assets/Preview_Forest.jpg',
                       useShaders={'calcNorm': 1})
    self.cloth = self.vertObjects[-1]
    self.clothSim = PhysCloth.MassSprings(self.cloth.getVertices(),
                                          self.cloth.getEdges(), 800,
                                          np.ones((nCloth+1)**2),
                                          np.array([0,nCloth]), 1/20)
    self.clothI = self.cloth.getIndices()


    self.t2 = Phys.TerrainCollider([-10,0,-10], self.terrain.size[0],
                                   self.terrain.heights, 0.375)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    self.directionalLights.append({"dir":[pi*2/3, 2.1], "i":[1.8,1.2,0.4]})
    self.directionalLights.append({"dir":[pi*2/3, 2.1+pi], "i":[0.5,0.32,0.1]})
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.1,0.2,0.4]})
    self.skyBox = self.makeSkybox(TexSkyBox, 12, PATH+"../Skyboxes/Desert_2k.ahdr",
                                  rot=(0,-pi/3,0), hdrScale=12)

    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

def frameUpdate(self):
    if self.frameNum == 1:
        tpath = 'C:/Users/L/Downloads/Textures/ornate-celtic-gold/'
        self.addNrmMap(tpath + "ornate-celtic-gold-normal.png", 'gold')
        self.addNrmMap(PATH + '../Assets/aerial_beach_01_nor_gl_1k.png', 'sand',
                       mip=True)
##    if self.frameNum == 1:
##        self.bindKey('j', self.STAGECONFIG.updateCloth)
##        global VIEWER
##        VIEWER = self
    updateCloth(self)

def updateCloth(self):
##    global VIEWER
##    self = VIEWER

    g = np.repeat(np.array([[0,-1,0.4 * sin(time.time())]]), (self.nCloth+1)**2, 0)
    st = time.perf_counter()
    self.clothSim.step(g)
    print('Cloth', time.perf_counter() - st)

    tn = self.cloth.texNum
    cStart, cEnd = self.cloth.cStart*3, self.cloth.cEnd*3

    size = 8*4
    raw = self.draw.VBO[tn].read(size=(cEnd-cStart)*size, offset=cStart*size)
    dat = np.array(np.frombuffer(raw, 'float32')).reshape((cEnd-cStart, 8))

    U = self.clothSim.Ucur

    dat[:,:3] = U[self.clothI]

    self.draw.VBO[tn].write(dat, offset=cStart*size)

