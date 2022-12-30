# Taiga

from PIL import Image
import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain, VertModel, VertPlane, VertTerrain0
from TexObjects import TexSkyBox

import random
import numpy.random as nr

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def grassClump(self, c, options):
    d = c + (nr.rand(3) - 0.5) * 5
    d[1] = self.terrain.getHeight(d[0],d[2]) + 0.4
    r = random.random() * 3
    self.addVertObject(VertModel, d, **options, rot=(0,r,0))

def setupStage(self):
    mpath = PATH + '../Models/'

    self.addVertObject(VertTerrain, [-50, 0, -50],
                   heights=PATH+"../Assets/Terrain.tif",
                   texture=PATH+"../Assets/Blank1.png",
                   scale=0.6,
                   vertScale=2.5/6553, vertPow=2, vertMax=50000,
                   useShaders={'spec': 1, 'normal': 'snow'},
                   uvspread=11, shadow="CR")
    self.terrain = self.vertObjects[-1]

    tmpHeights = np.array(self.terrain.heights)
    iceMap = np.zeros_like(tmpHeights)
    c = tmpHeights[50:-50,50:-50]
    iceMap[50:-50,50:-50][c < 1.8/0.6] = 1
    c[c < 1.8/0.6] = 1.8/0.6
    tmpHeights[50:-50,50:-50] = c
    self.iceMap = VertTerrain0([-50,0,-50], iceMap, scale=0.6)

    p = Image.open(PATH+'../Assets/PillarHeight1.png').convert('L')
    pdim = 17
    pdim2 = pdim//2
    p = (np.array(p).astype('float')[:,::-1] - 1) / 254
    p = (22.5 - 22.5 * p) / 0.63
    q = np.zeros_like(tmpHeights)
    q[80-pdim2:80+pdim2+1,112-pdim2:112+pdim2+1] = p

    tmpHeights = np.maximum(tmpHeights, q)
    self.tmpHeights = tmpHeights

    self.t2 = Phys.TerrainCollider([-50,0,-50], self.terrain.size[0],
                                   tmpHeights, 0.6)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    nr.seed(1); random.seed(1)
    options = {"filename":mpath+"pine/Pine.obj", "static":True,
           "texMode":None, "scale":0.2, "shadow":"C"}
    options2 = {'filename':mpath+'TaigaNew/GrassClump.obj',
                'static':True, 'texMode':None, 'scale':1, 'shadow':'R',
                'useShaders':{'translucent':1}}

    cn = []
    for i in range(-50, 70, 20):
        for j in range(-50, 70, 20):
            c = np.array((i, 0, j), dtype="float")
            c += nr.rand(3) * 8
            options['scale'] = 0.2
            if (i == 10) and (j == 10):
                c = np.array([12.52, 0, 13.73], 'float')
                options['scale'] = 0.2 * 0.8
            c[1] = self.terrain.getHeight(c[0],c[2]) - 0.4
            r = random.random() * 3
            self.addVertObject(VertModel, c, **options, rot=(0,r,0))
            cn.append([round(x, 3) for x in c])

    # Grass around trees
    for i in range(len(cn)):
        c = cn[i]
        for j in range(7):
            grassClump(self, c, options2)

    # Random grass
    for i in range(-40, 60, 13):
        for j in range(-40, 60, 13):
            c = np.array((i, 0, j), dtype="float")
            c += nr.rand(3) * 18
            for k in range(random.randint(3, 9)):
                grassClump(self, c, options2)

    # Tree to cover fake shadow
    c = np.array((51,0,26.5))
    c[1] = self.terrain.getHeight(c[0],c[2]) - 0.4
    options['scale'] = 0.2 * 0.7
    self.addVertObject(VertModel, c, **options)
    cn.append([round(x, 3) for x in c])
    for j in range(7):
        grassClump(self, c, options2)

    for f in self.vtNames:
        if f.endswith('Piney.png'):
            self.matShaders[self.vtNames[f]]['normal'] = 'bark'

    pfile = mpath + "TaigaNew/TaigaPillar.obj"
    self.addVertObject(VertModel, [-2.12, 6.27, 17.52], filename=pfile,
                       rot=(0,-47.8 * 3.14/180, 0), static=True,
                       mip=2, useShaders={'spec': 0.4, 'normal': 'rock'},
                       shadow="CR")

    iceW = 16
    self.addVertObject(VertPlane, [8.5-iceW, 1.8, 7-iceW],
                       h1=[iceW*2,0,0], h2=[0,0,iceW*2], n=16,
                       texture=PATH+'../Assets/Blank3.png', uvspread=0.333,
                       useShaders={'SSR':'0', 'normal': 'ice'})
    self.iceMTL = self.vertObjects[-1].texNum

    LInt = np.array([1,0.3,0.24]) * 0.9 * 0.8 * 1.6
    LDir = pi*1.45
    skyI = np.array([0.1,0.15,0.5]) * 0.8
    self.directionalLights.append({"dir":[LDir, 0.1], "i":LInt})
    self.directionalLights.append({"dir":[LDir, 0.1+pi], "i":[0.08,0.06,0.1]})
    self.directionalLights.append({"dir":[LDir, 0.1], "i":[0.12,0.1,0.08]})
    self.directionalLights.append({"dir":[0, pi/2], "i":skyI})


    fn = "../Skyboxes/kiara_1_dawn_1k.ahdr"
    self.skyBox = TexSkyBox(self, 12, PATH+fn, hdrScale=5)
    self.skyBox.created()

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['isEqui'] = 1
    skyShader['rotY'] = 0.4

    self.matShaders[self.iceMTL]['envFallback'] = self.skyBox.texNum
    self.matShaders[self.iceMTL]['rotY'] = skyShader['rotY']
    self.matShaders[self.iceMTL]['roughness'] = 0.02


    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

def frameUpdate(self):
    if self.frameNum == 1:
        self.terrain.heights = self.tmpHeights
        self.terrain.interpLim = 2

        s = Image.open(PATH + '../Assets/Sh2.png').convert('L')
        s = np.array(s)
        self.draw.addBakedShadow(0, s)

        self.addNrmMap(PATH + '../Models/TaigaNew/3DRock004_Normal.jpg', 'rock')
        self.addNrmMap(PATH + '../Models/TaigaNew/Snow005_Normal.jpg', 'snow')
        self.addNrmMap(PATH + '../Models/TaigaNew/Ice004_Normal.jpg', 'ice')
        self.addNrmMap(PATH + '../Models/TaigaNew/Bark012_Normal.png', 'bark')

    self.matShaders[self.fogMTL]['fogHeight'] = max(10, self.pos[1] + 4)
    self.draw.changeShader(self.fogMTL, self.matShaders[self.fogMTL])
