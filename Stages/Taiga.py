# Taiga

from PIL import Image
import numpy as np
from math import pi, sin, cos
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


    self.skis = []
    self.poles = []
    for i in range(2*len(self.players)):
        self.addVertObject(VertModel, [0,0,0],
                           filename=mpath + 'Ski.obj', cache=False,
                           mip=2, useShaders={'spec': 0.4},
                           scale=0.6, rot=(0,-pi/2,0))
        self.skis.append(self.vertObjects[-1])
        self.addVertObject(VertModel, [0,-1.9,0], # obj is 1.6 height
                           filename=mpath + 'Pole.obj', cache=False,
                           useShaders={'spec': 0.4},
                           scale=1.2, rot=(0,pi/2,0))
        self.poles.append(self.vertObjects[-1])
    for s in self.skis:
        s.prevPos = np.array([0,0,0.])
        s.prevRot = np.identity(3)
    for s in self.poles:
        s.planted = False
        s.prevPos = np.array([0,0,0.])
        s.prevRot = np.identity(3)
        s.plantDir = None

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



def frameUpdateAfter(self):
    for i in range(2*len(self.players)):
        p = self.players[i//2]
        if p['id'] == 4: continue

        s = self.skis[i]
        objArgs = (s.cStart*3, s.cEnd*3, s.texNum)

        foot = p['b1'].children[1+(i%2)].children[0].children[0]
        pos = (np.array([0.3,-0.08-self.footSize[p['id']],0,1]) @ foot.TM)[:3]

        vv = (np.array([1,0,0,0.]) @ foot.TM)[:3]
        vv[1] = 0; vv /= Phys.eucLen(vv)
        vx = np.cross(vv, np.array([0,1,0.]))
        rot = np.array([vv, np.array([0,1,0.]), vx])
        self.draw.translate(-s.prevPos, *objArgs)
        self.draw.rotate(np.transpose(s.prevRot) @ rot, *objArgs)
        self.draw.translate(pos, *objArgs)
        s.prevPos = pos
        s.prevRot = rot


        s = self.poles[i]
        objArgs = (s.cStart*3, s.cEnd*3, s.texNum)

        hand = p['b1'].children[0].children[i%2].children[0].children[0]
        pos = (np.array([0,-0.04,-0.14 + 0.28*(i%2),1.]) @ hand.TM)[:3]

        plant1a = (self.keyFrames[1][0] + self.keyFrames[2][0]) / 2
        plant1b = self.keyFrames[6][0] + 0.1
        plant2a = (self.keyFrames[9][0] + self.keyFrames[10][0]) / 2
        plant2b = self.keyFrames[14][0] + 0.1
        if (plant1a < p['poset'] < plant1b or
            plant2a < p['poset'] < plant2b) and not s.planted:
            s.planted = True
            s.plantPos = np.array([s.prevPos[0],
                                   self.terrain.getHeight(*s.prevPos[::2]),
                                   s.prevPos[2]])

        if (plant1b < p['poset'] < plant2a or p['poset'] > plant2b) and s.planted:
            s.planted = False
            s.plantDir = pos - s.plantPos

        self.draw.translate(-s.prevPos, *objArgs)
        if s.planted:
            vy = pos - s.plantPos
            vy /= Phys.eucLen(vy)
            vv = np.array([cos(p['cr']),0,sin(p['cr'])])
            vx = np.cross(vv,vy)
            vx /= Phys.eucLen(vx)
            rot = np.array([np.cross(vx,vy),vy,vx])
            self.draw.rotate(np.transpose(s.prevRot) @ rot, *objArgs)
            s.prevRot = rot
        elif s.plantDir is not None:
            s.plantDir = s.plantDir + np.array([0,0.2,0])
            s.plantDir /= Phys.eucLen(s.plantDir)
            vy = s.plantDir
            vv = np.array([cos(p['cr']),0,sin(p['cr'])])
            vx = np.cross(vv,vy)
            vx /= Phys.eucLen(vx)
            rot = np.array([np.cross(vx,vy),vy,vx])
            self.draw.rotate(np.transpose(s.prevRot) @ rot, *objArgs)
            s.prevRot = rot

        self.draw.translate(pos, *objArgs)
        s.prevPos = pos
