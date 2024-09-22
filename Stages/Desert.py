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


    nCloth = 31
    self.nCloth = nCloth
    self.addVertObject(VertPlane, [20,8,20],
                       n=nCloth, h2=[2,0,1.5], h1=[0.2,-3,0.1],
                       texture=PATH+'../Assets/Preview_Forest.jpg',
                       shadow="R",
                       useShaders={'calcNorm': 1, 'args':{'translucent':1,'NMmipBias':0.1},
                                   'normal':'Clothes', 'shadowDynamic':1})
    self.cloth = self.vertObjects[-1]
    pinned = np.array([0, nCloth, (nCloth+1)*nCloth])
    self.clothSim = PhysCloth.MassSprings(self.cloth.getVertices(),
                                          self.cloth.getEdges(), 64000,
                                          np.ones((nCloth+1)**2),
                                          pinned, 1/20,
                                          damp=0.002)
    self.clothI = self.cloth.getIndices()


    self.t2 = Phys.TerrainCollider([-10,0,-10], self.terrain.size[0],
                                   self.terrain.heights, 0.375)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    self.directionalLights.append({"dir":[pi*2/3, 2.1], "i":np.array([1.8,1.2,0.4])*1.5})
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
        self.clothTime = 0
    updateCloth(self)
    print('Cloth', self.clothTime / self.frameNum, end='\r')

def updateCloth(self):
    g = np.repeat(np.array([[0,-9.81,0.2 * sin(time.time())]], dtype='float32'),
                  (self.nCloth+1)**2, 0)

    coll = self.players[self.selchar]['pv'].colliders[1]

    for s in self.srbs:
        if not s.disabled:
            coll = s.colliders[0]

    st = time.perf_counter()
    self.clothSim.step(g, collider=coll, collVMult=2, iters=16)
    self.clothTime += time.perf_counter() - st

    tn = self.cloth.texNum
    cStart, cEnd = self.cloth.cStart*3, self.cloth.cEnd*3

    size = 8*4
    raw = self.draw.VBO[tn].read(size=(cEnd-cStart)*size, offset=cStart*size)
    dat = np.array(np.frombuffer(raw, 'float32')).reshape((cEnd-cStart, 8))

    U = self.clothSim.Ucur

    dat[:,:3] = U[self.clothI]

    self.draw.VBO[tn].write(dat, offset=cStart*size)

