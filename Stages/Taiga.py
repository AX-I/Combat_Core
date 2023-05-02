# Taiga

from PIL import Image
import numpy as np
from math import pi, sin, cos
from OpsConv import PATH
import time

from VertObjects import VertTerrain, VertModel, VertPlane, VertTerrain0
from TexObjects import TexSkyBox
from ParticleSystem import ContinuousParticleSystem

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

    tgpath = mpath + 'TaigaNew/'
    pfile = tgpath + "TaigaPillar.obj"
    self.addVertObject(VertModel, [-2.12, 6.27, 17.52], filename=pfile,
                       rot=(0,-47.8 * 3.14/180, 0), static=True,
                       mip=2, useShaders={'spec': 0.4, 'normal': 'rock'},
                       shadow="CR")

    # Large rocks
    pfile = tgpath + "LargeRocks.obj"
    objs = [{'pos':(0,0,0), 'rot':(0,0,0)},
            {'pos':(21,  6.9,-21.6), 'rot':(0,23/180*3.14,0)},
            {'pos':(37.6,4.8,-22), 'rot':(0,-34/180*3.14,0)},
            {'pos':(-1,5.5,-36.3), 'rot':(0,201/180*3.14,0)},
            {'pos':(-29,3.5,3.1), 'rot':(0,127/180*3.14,0)}]
    for o in objs:
        self.addVertObject(VertModel, o['pos'], rot=o['rot'], static=True,
                           filename=pfile,
                           mip=2, useShaders={'spec':0.4, 'normal':'largeRock'},
                           shadow="CR")

    # Background Mountain
    pfile = tgpath + "Mountain.obj"
    opts = {'filename':pfile, 'mip':2, 'useShaders':
            {'spec':0.4, 'normal':'mountain', 'ignoreShadow':1},
            'shadow':'', 'static':True}
    self.addVertObject(VertModel, [22,32,-271], rot=(0,0,0), scale=2,
                       **opts)
    self.addVertObject(VertModel, [-366,50,-11], rot=(0,pi/2,0), scale=2.5,
                       **opts)


    iceW = 16
    self.addVertObject(VertPlane, [8.5-iceW, 1.8, 7-iceW],
                       h1=[iceW*2,0,0], h2=[0,0,iceW*2], n=16,
                       texture=PATH+'../Assets/Blank3.png', uvspread=0.333,
                       useShaders={'SSR':'0', 'normal': 'ice'})
    self.iceMTL = self.vertObjects[-1].texNum


    self.skis = []
    self.poles = []
    self.skiParticles = []
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
        ts = 1
        ps = ContinuousParticleSystem([0,0,0.], (0,-pi/2),
                                      vel=0.03/ts, force=(0,-0.01/ts/ts,0),
                                      lifespan=90*ts, nParticles=30,
                                      randPos=0.02, randVel=0.01/ts,
                                      size=0.15, opacity=0.15,
                                      color=np.array([1,0.3,0.24]) * 0.3)
        self.addParticleSystem(ps)
        self.skiParticles.append(ps)

    for s in self.skis:
        s.prevPos = np.array([0,0,0.])
        s.prevRot = np.identity(3)
    for s in self.poles:
        s.planted = False
        s.prevPos = np.array([0,0,0.])
        s.prevRot = np.identity(3)
        s.plantDir = None


    for i in range(2000):
        p = nr.rand(3) * np.array([70,12,70]) + np.array([-20,1.5,-20])
        r = random.random()*3
        self.addVertObject(VertPlane, p, n=1, h1=[0,0.2,0], h2=[0.2,0,0],
                           texture=PATH+'../Assets/Snowflake.png',
                           useShaders={'add': 1, 'noline':1}, mip=2,
                           rot=(0,r,0))

    LInt = np.array([1,0.3,0.24]) * 0.9 * 0.8 * 1.6 * 1.5
    #LInt = np.array([0.1,0.3,0.9]) * 1
    #LInt = np.array([0.5,0.6,0.9])
    #LInt = np.array([1,0.4,0.2])
    # 255, 122, 2
    # 63, 125, 252, black point 0.15
    LDir = pi*1.45
    skyI = np.array([0.2,0.25,0.5]) * 0.8 * 0.6
    #skyI = np.array([0.1,0.15,0.5]) * 0.3
    self.directionalLights.append({"dir":[LDir, 0.1], "i":LInt})
    self.directionalLights.append({"dir":[LDir, 0.1+pi], "i":
                                   np.array([0.08,0.06,0.1]) * 0.6})
    self.directionalLights.append({"dir":[LDir, 0.1], "i":
                                   np.array([0.12,0.1,0.08]) * 0.6})
    self.directionalLights.append({"dir":[0, pi/2], "i":skyI})


    # Sun glare
    self.addVertObject(VertPlane, [-1,-1,0],
            h1=[2,0,0], h2=[0,2,0], n=1,
            texture=PATH+'../Assets/DirtMaskTextureExample.webp',
            useShaders={'2d':1, 'lens':1})

    fn = "../Skyboxes/kiara_1_dawn_1k.ahdr"
    self.skyBox = TexSkyBox(self, 12, PATH+fn, hdrScale=2)
    self.skyBox.created()

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['isEqui'] = 1
    skyShader['rotY'] = 0.4

    self.matShaders[self.iceMTL]['envFallback'] = self.skyBox.texNum
    self.matShaders[self.iceMTL]['rotY'] = skyShader['rotY']
    self.matShaders[self.iceMTL]['roughness'] = 0.02


    self.atriumNav = {"map":None, "scale":0, "origin":np.zeros(3)}

def frameUpdate(self):
    if self.frameNum == 0:
        self.terrain.heights = self.tmpHeights
        self.terrain.interpLim = 2

        s = Image.open(PATH + '../Assets/Sh2.png').convert('L')
        s = np.array(s)
        self.draw.addBakedShadow(0, s)

        tpath = PATH + '../Models/TaigaNew/'
        self.addNrmMap(tpath + '3DRock004_Normal.jpg', 'rock')
        self.addNrmMap(tpath + 'Snow005_Normal.jpg', 'snow')
        self.addNrmMap(tpath + 'Ice004_Normal.jpg', 'ice')
        self.addNrmMap(tpath + 'Bark012_Normal.png', 'bark')
        self.addNrmMap(tpath + 'LargeRocks_normal.png', 'largeRock')
        self.addNrmMap(tpath + 'Mountain_normal.png', 'mountain')

        s = Image.open(PATH+'../Assets/Snowflake.png').convert('L').rotate(-90)
        s = np.array(s)
        s = np.array(s > 30, 'uint8')
        self.draw.addTexAlpha(s, 'snowflake')

    self.matShaders[self.fogMTL]['fogHeight'] = max(10, self.pos[1] + 4)
    self.draw.changeShader(self.fogMTL, self.matShaders[self.fogMTL])



def frameUpdateAfter(self):
    CURRTIME = time.time()

    batchT1 = []
    batchR = []
    batchT2 = []

    for i in range(2*len(self.players)):
        p = self.players[i//2]
        if p['id'] not in self.actPlayers: continue
        if p['id'] == 4: continue

        s = self.skis[i]
        objArgs = (s.cStart*3, s.cEnd*3)

        foot = p['b1'].children[1+(i%2)].children[0].children[0]
        relpos = np.array([0.3,-0.08-self.footSize[p['id']],0,1])
        pos = (relpos @ foot.TM)[:3]

        vv = (np.array([1,0,0,0.]) @ foot.TM)[:3]
        vv[1] = 0; vv /= Phys.eucLen(vv)

        vy = np.array([0,1,0.])

        vx = np.cross(vv, vy)
        rot = np.array([vv, vy, vx])

        batchT1.append((-s.prevPos, *objArgs))
        batchR.append((np.transpose(s.prevRot) @ rot, *objArgs))
        batchT2.append((pos, *objArgs))

        s.prevPos = pos
        s.prevRot = rot

        ps = self.skiParticles[i]
        active = self.keyFrames[11][0] > p['poset'] > self.keyFrames[3][0]

        if ((i + active)&1) and (p['moving'] or (CURRTIME - p['animTrans'] < 0.1)):
            ps.changePos(pos + 0.5*vv)
            ps.step()
        elif (CURRTIME - p['animTrans'] > 0.1) and ps.started:
            ps.reset()

    tn = self.skis[0].texNum
    self.draw.translateBatch({tn: batchT1})
    self.draw.rotateBatch({tn: batchR})
    self.draw.translateBatch({tn: batchT2})


    batchT1 = []
    batchR = []
    batchT2 = []

    for i in range(2*len(self.players)):
        p = self.players[i//2]
        if p['id'] == 4: continue

        s = self.poles[i]
        objArgs = (s.cStart*3, s.cEnd*3)

        hand = p['b1'].children[0].children[i%2].children[0].children[0]
        pos = (np.array([0,-0.04,-0.14 + 0.28*(i%2),1.]) @ hand.TM)[:3]

        plant1a = (self.keyFrames[1][0] + self.keyFrames[2][0]) / 2
        plant1b = self.keyFrames[6][0] + 0.1
        plant2a = (self.keyFrames[9][0] + self.keyFrames[10][0]) / 2
        plant2b = self.keyFrames[14][0] + 0.1
        if (plant1a < p['poset'] < plant1b or
            plant2a < p['poset'] < plant2b) and not s.planted:
            s.planted = True
            pI = s.prevPos + np.array([-sin(p['cr']), 0, cos(p['cr'])]) * \
                 (-0.15 + 0.3 * (i&1))
            s.plantPos = np.array([pI[0], self.terrain.getHeight(*pI[::2]), pI[2]])

        if (plant1b < p['poset'] < plant2a or p['poset'] > plant2b) and s.planted:
            s.planted = False
            s.plantDir = pos - s.plantPos

        batchT1.append((-s.prevPos, *objArgs))
        if s.planted:
            vy = pos - s.plantPos
            vy /= Phys.eucLen(vy)
            vv = np.array([cos(p['cr']),0,sin(p['cr'])])
            vx = np.cross(vv,vy)
            vx /= Phys.eucLen(vx)
            rot = np.array([np.cross(vx,vy),vy,vx])
            batchR.append((np.transpose(s.prevRot) @ rot, *objArgs))
            s.prevRot = rot
        elif s.plantDir is not None:
            off = np.array([0,0.1 * (self.frameTime*25),0])
            s.plantDir = s.plantDir + off
            s.plantDir /= Phys.eucLen(s.plantDir)
            vy = s.plantDir
            vv = np.array([cos(p['cr']),0,sin(p['cr'])])
            vx = np.cross(vv,vy)
            vx /= Phys.eucLen(vx)
            rot = np.array([np.cross(vx,vy),vy,vx])
            batchR.append((np.transpose(s.prevRot) @ rot, *objArgs))
            s.prevRot = rot

        batchT2.append((pos, *objArgs))
        s.prevPos = pos

    tn = self.poles[0].texNum
    self.draw.translateBatch({tn: batchT1})
    if batchR:
        self.draw.rotateBatch({tn: batchR})
    self.draw.translateBatch({tn: batchT2})
