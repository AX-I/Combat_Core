# Atrium

import numpy as np
from math import pi
from OpsConv import PATH

from VertObjects import VertTerrain0, VertModel
from TexObjects import TexSkyBox
from PIL import Image

import Phys

def getHeight(self, pos):
    return self.terrain.getHeight(*pos[::2])

def setupStage(self):
    self.addVertObject(VertModel, [13.32,0,20.4], rot=(0,0,0),
                       filename=PATH+"../Atrium/Atrium8AtlasOpt.obj",
                       scale=1.2, mip=2,
                       subDiv=1, shadow="CR")

    for f in self.vtNames:
        mat = self.matShaders[self.vtNames[f]]
        if "CV" in f:
            mat.update(shader='emissive', args={'emPow':1.0})
        if "BackgroundLight" in f:
            mat.update(shader='add', noline=1, args={'emPow':0.5}, cull=1)
        if "FieldBackground" in f:
            mat.update(shader='emissive', args={'emPow':2.0})
        if 'AtlasG_opt' in f:
            mat.update(args={'specular':1}, normal='AtlasG')
        if 'Copy' in f:
            mat.update(shader='SSRopaque', normal='AtlasG',
                args={'roughness':0.1}, cull=1)
            self.ssrMTL = mat
        if 'AtlasW' in f:
            mat.update(args={'specular':1, 'roughness':0.4})
        if 'Lights' in f:
            mat.update(shader='emissive', args={'emPow':1.4})
        if 'Glass' in f:
            mat.update(shader='SSRglass')

    self.terrain = VertTerrain0([0,-0.6,0],
                                PATH+"../Atrium/AtriumNav.png",
                                scale=0.293, vertScale=20)

    hm = Image.open(PATH+"../Atrium/AtriumNavA.png")
    hm = np.array(hm)[:,:,0] < 80
    hs = 0.586
    ho = np.array([0.3,0,0.3])

    self.atriumNav = {"map":hm, "scale":0.586, "origin":ho}

    self.t2 = Phys.TerrainCollider([0,-0.6,0], self.terrain.size[0],
                                   self.terrain.heights, 0.293)
    self.t2.onHit = lambda x: self.explode(x)
    self.w.addCollider(self.t2)

    DIR0I = np.array([2.0,1.77,1.33]) * 1.5
    self.directionalLights.append({"dir":[pi*2/3, 2.5], "i":DIR0I})
    self.directionalLights.append({"dir":[pi*2/3, 2.5+pi], "i":[0.3,0.2,0.15]})
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.075,0.15,0.3]})

    # Local lights are getting out of hand
    self.directionalLights.append({"dir":[0, pi/2], "i":[0.2,0.2,0.2]})

    self.skyBox = self.makeSkybox(TexSkyBox, 12, PATH+"../Skyboxes/autumn_park_2k.ahdr",
                                  rot=(0,0,0), hdrScale=48)

    skyShader = self.matShaders[self.skyBox.texNum]
    skyShader['args'].update(isEqui=1, rotY=3.27)

    self.ssrMTL['envFallback'] = self.skyBox.texNum
    self.ssrMTL['args']['rotY'] = skyShader['args']['rotY']

def frameUpdate(self):
    if self.frameNum == 0:
        tpath = PATH + '../Atrium/'
        self.addNrmMap(tpath + 'AtlasG_opt_nrm.png', 'AtlasG', mip=True)
