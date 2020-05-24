# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (VertObjects.py) is part of AXI Visualizer and AXI Combat.
#
# AXI Combat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# AXI Combat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AXI Combat. If not, see <https://www.gnu.org/licenses/>.
# ======== ========

from math import sin, cos, pi, log2, ceil
import numpy
import numpy as np
import time
from Utils import anglesToCoords
from PIL import Image

def rgbToString(rgb):
    return "#{0:02x}{1:02x}{2:02x}".format(*rgb)

class VertObject:    
    def __init__(self, *args, texture=None, texMode="default", gamma=True,
                 maxWedgeDims=1, useShaders={}, **kwargs):
        self.maxWedgeDims = maxWedgeDims
        self.numWedges = 0
        self.estWedges = 0
        self.enabled = True

        self.castShadow = False
        self.receiveShadow = False

        self.texMode = texMode
        self.cgamma = gamma

        self.texMul = 1
        if "texMul" in kwargs:
            self.texMul = kwargs["texMul"]
        
        self.mip = None
        self.reflection = False

        self.useAlpha = None
        
        self.wedgePoints = []
        self.vertNorms = []
        self.u = []
        self.v = []
        self.origin = False
        self.static = False

        self.animated = False
        self.bones = None
        
        self.viewer = args[0]
        self.coords = numpy.array(args[1], dtype="float")
        self.scale = numpy.array([1, 1, 1])
        self.angles = [0.,0.,0.]
        self.rotMat = numpy.array([[1, 0, 0],
                                   [0, 1, 0],
                                   [0, 0, 1]])

        self.emissive = None
        if "emissive" in kwargs:
            ef = kwargs["emissive"]
        
        self.boneOffset = 0
        if "boneOffset" in kwargs:
            self.boneOffset = kwargs["boneOffset"]
        
        if "mip" in kwargs:
            self.mip = kwargs["mip"]

        if "Lights" in texture or "plant" in texture or "as12lef" in texture: self.mip = None
        
        if "shadow" in kwargs:
            self.castShadow = "C" in kwargs["shadow"]
            self.receiveShadow = "R" in kwargs["shadow"]
        if "reflect" in kwargs:
            self.reflection = kwargs["reflect"]

        self.overrideNorms = None
        if "overrideNorms" in kwargs:
            self.overrideNorms = numpy.expand_dims(kwargs["overrideNorms"], 0)
        
        if "alpha" in kwargs:
            af = kwargs["alpha"]
            if af in self.viewer.vaNames:
                pass
            else:
                ti = Image.open(af).rotate(-90)
                if ti.mode == "1":
                    ta = np.array(ti).astype("bool")
                elif ti.mode == "RGB":
                    ta = np.floor(np.array(ti, dtype="float")[:,:,0] / 255 + 0.4).astype("bool")
                elif ti.mode == "RGBA":
                    ta = np.array(ti, dtype="float")[:,:,3]
                    ta = np.floor(ta / 255 + 0.4).astype("bool")
                else:
                    print(ti.mode)
                self.viewer.texAlphas.append(ta)
                self.viewer.vaNames[af] = len(self.viewer.texAlphas) - 1
            self.useAlpha = self.viewer.vaNames[af]
        
        if texture is None:
            texture = "../Assets/Magenta.png"
            print("Texture missing")
            #raise ValueError("Texture must be supplied!")
        self.texName = texture

        if texture in self.viewer.vtNames:
            self.texNum = self.viewer.vtNames[texture]
        else:
            ti = Image.open(texture).convert("RGBA")
            if ti.size[0] != ti.size[1]:
                print("Texture is not square")
                n = max(ti.size)
                ti = ti.resize((n,n))
            if (ti.size[0] & (ti.size[0] - 1)) != 0:
                print("Texture is not a power of 2, resizing up.")
                n = 2**ceil(log2(ti.size[0]))
                ti = ti.resize((n,n))
            ta = numpy.array(ti.rotate(-90)).astype("float")
            if self.cgamma:
                ta *= ta
                ta /= 8. # Gamma correction
            else:
                ta *= 64
            ta *= self.texMul
            #numpy.clip(ta, None, 256*256-1, ta)
            self.viewer.vtextures.append(ta.astype("uint16"))
            self.viewer.vtNames[texture] = len(self.viewer.vtextures) - 1
            self.texNum = self.viewer.vtNames[texture]
            
            self.viewer.vertpoints.append([])
            self.viewer.vertnorms.append([])
            self.viewer.vertu.append([])
            self.viewer.vertv.append([])
            self.viewer.vertBones.append([])
            
            s = {}
            if self.mip is not None: s["mip"] = self.mip
            if self.receiveShadow: s["shadow"] = "R"
            if self.useAlpha is not None: s["alpha"] = self.useAlpha
            if self.reflection: s["refl"] = self.reflection
            
            if "Lights" in texture: s["emissive"] = 1.4
            
            for i in useShaders:
                s[i] = useShaders[i]

            self.viewer.matShaders[self.texNum] = s
            
        self.texNum = self.viewer.vtNames[texture]
        
        if "enabled" in kwargs:
            self.enabled = kwargs["enabled"]
        if "scale" in kwargs:
            self.scale = numpy.array(kwargs["scale"])
        if "rot" in kwargs:
            rr = kwargs["rot"]
            rotX = numpy.array([[1, 0, 0],
                                [0, cos(rr[0]), -sin(rr[0])],
                                [0, sin(rr[0]), cos(rr[0])]])
            rotY = numpy.array([[cos(rr[1]), 0, sin(rr[1])],
                                [0, 1, 0],
                                [-sin(rr[1]), 0, cos(rr[1])]])
            rotZ = numpy.array([[cos(rr[2]), -sin(rr[2]), 0],
                                [sin(rr[2]), cos(rr[2]), 0],
                                [0, 0, 1]])
            self.rotMat = rotX @ rotZ @ rotY
            self.angles = list(rr)
        if "origin" in kwargs:
            self.origin = kwargs["origin"]

        if "static" in kwargs:
            self.static = True
        self.invertNorms = False
        if "invertNorms" in kwargs:
            self.invertNorms = True

    def created(self):
        self.create()
        self.cStart = len(self.viewer.vertpoints[self.texNum])
        self.cEnd = self.cStart + self.numWedges
        self.wedgePoints = numpy.array(self.wedgePoints)
        if self.overrideNorms is None:
            self.vertNorms = numpy.array(self.vertNorms).reshape((-1, 3))
            self.vertNorms /= numpy.expand_dims(numpy.linalg.norm(self.vertNorms, axis=1), 1)
            self.vertNorms = self.vertNorms.reshape((-1, 3, 3))
        else:
            self.vertNorms = numpy.repeat(self.overrideNorms,
                                          self.wedgePoints.shape[0]*3, 0)
            self.vertNorms = self.vertNorms.reshape((-1, 3, 3))
        if self.invertNorms:
            self.vertNorms *= -1
        self.u = numpy.array(self.u)
        self.v = numpy.array(self.v)
        if self.texMode == "repeat":
            self.u %= 1
            self.v %= 1
        elif self.texMode == "safe":
            self.u *= 0.999
            self.v *= 0.999
        elif self.texMode == "clamp":
            numpy.clip(self.u, 0, 1, out=self.u)
            numpy.clip(self.v, 0, 1, out=self.v)
        self.transform(origin=self.origin, early=True)
        del self.u, self.v
        if self.static:
            del self.wedgePoints, self.vertNorms
    
    def transform(self, origin=False, early=False):
        tn = self.texNum
        if origin is False:
            newpoints = (self.wedgePoints * self.scale) @ self.rotMat + self.coords            
            newnorms = self.vertNorms @ self.rotMat
        else:
            origin = numpy.expand_dims(origin, 0)
            newpoints = ((self.wedgePoints-origin) * self.scale) @ self.rotMat + origin + self.coords
            newnorms = self.vertNorms @ self.rotMat
        
        if early:
            self.viewer.vertpoints[tn].extend(newpoints)
            self.viewer.vertnorms[tn].extend(newnorms)
            self.viewer.vertu[tn].extend(self.u)
            self.viewer.vertv[tn].extend(self.v)
            if self.animated:
                if len(self.viewer.vertBones[tn]) > 0:
                    self.viewer.vertBones[tn] = numpy.concatenate(
                        (self.viewer.vertBones[tn],
                         numpy.array(self.bones) + self.boneOffset), axis=0)
                else:
                    self.viewer.vertBones[tn] = numpy.array(self.bones) + self.boneOffset
        else:
            if origin is False:
                origin = numpy.array((0.,0.,0.))
            origin += self.coords
            cStart, cEnd = self.cStart*3, self.cEnd*3
            self.viewer.draw.transform(self.oldRM, self.rotMat, origin,
                                       cStart, cEnd, tn)

        self.oldRM = numpy.array(self.rotMat.T)
    
    def appendWedge(self, coords, norms, uv):
        self.wedgePoints.append(coords)
        self.vertNorms.append(norms)
        self.u.append(uv[:,0])
        self.v.append(uv[:,1])
        self.numWedges += 1

    def appendWedgeSafe(self, coords, norms, uv, r=0):
        #if (((np.max(coords, axis=0) -
        #      np.min(coords, axis=0)) > self.maxWedgeDims).any() and (r < 2)):
        if (r < self.subDiv):
            #print(r, end="")
            #if r > 5:
            #    print("test", self.texNum)
            nc, nn, nuv = self.splitFace(coords, norms, uv)
            for f in range(4):
                self.appendWedgeSafe(nc[f], nn[f], nuv[f], r+1)
        else:
            self.wedgePoints.append(coords)
            self.vertNorms.append(norms)
            self.u.append(uv[:,0])
            self.v.append(uv[:,1])
            self.numWedges += 1

    def splitFace(self, c, n, uv):
        nc = (c + np.roll(c, -1, 0)) / 2
        nn = (n + np.roll(n, -1, 0)) / 2
        nn = nn / np.expand_dims(np.linalg.norm(nn, axis=1), axis=1)
        nuv = (uv + np.roll(uv, -1, 0)) / 2
        fc = np.array([(c[0], nc[0], nc[2]), (c[1], nc[1], nc[0]),
                       (c[2], nc[2], nc[1]), nc])
        fn = np.array([(n[0], nn[0], nn[2]), (n[1], nn[1], nn[0]),
                       (n[2], nn[2], nn[1]), nn])
        fuv = np.array([(uv[0], nuv[0], nuv[2]), (uv[1], nuv[1], nuv[0]),
                        (uv[2], nuv[2], nuv[1]), nuv])
        
        return fc, fn, fuv

    def rotate(self, rr):
        rotX = numpy.array([[1, 0, 0],
                            [0, cos(rr[0]), -sin(rr[0])],
                            [0, sin(rr[0]), cos(rr[0])]])
        rotY = numpy.array([[cos(rr[1]), 0, sin(rr[1])],
                            [0, 1, 0],
                            [-sin(rr[1]), 0, cos(rr[1])]])
        rotZ = numpy.array([[cos(rr[2]), -sin(rr[2]), 0],
                            [sin(rr[2]), cos(rr[2]), 0],
                            [0, 0, 1]])
        self.rotMat = rotX @ rotZ @ rotY
        self.angles = list(rr)


class VertWater(VertObject):
    def __init__(self, *args, size=60, pScale=1, wDir=[(0.4,-0.1), (0.4, 0.1)],
                 wLen=[(10, 4, 3), (7, 5, 2)],
                 wAmp=[(0.8, 0.5, 0.3), (0.6, 0.4, 0.3)], aScale=1,
                 wSpd=[(0.6, 0.8, 1.1), (1, 1.1, 1.3)], numW=3, **ex):
        super().__init__(*args, **ex)

        self.wDir = numpy.array(wDir)
        self.pS = pScale
        self.wLen = numpy.array(wLen)
        self.wAmp = numpy.array(wAmp) * 0.1 * aScale
        self.wSpd = numpy.array(wSpd)
        self.numW = numW
        self.size = size
        self.estWedges = size*size*2
        self.hasSetup = False

    def create(self):
        n = numpy.array([[0, 1., 0]] * 3)
        for i in range(self.size):
            for j in range(self.size):
                wc = numpy.array([(i,0.,j), (i+1,0,j), (i,0,j+1)])
                tx = numpy.array([(0., 0), (1, 0), (0, 1)])
                self.appendWedge(wc, -n, tx)

                wc = numpy.array([(i+1,0.,j+1), (i,0,j+1), (i+1,0,j)])
                tx = numpy.array([(1., 1), (0, 1), (1, 0)])
                self.appendWedge(wc, -n, tx)
        self.stTime = time.time()
        
    def update(self):
        if not self.hasSetup:
            self.viewer.draw.setupWave(self.coords, self.wDir,
                                       self.wLen, self.wAmp, self.wSpd,
                                       self.numW)
            self.hasSetup = True
        self.viewer.draw.updateWave(self.pS, self.stTime, self.texNum)

class VertSphere(VertObject):
    def __init__(self, *args, n=16, size=1, **ex):
        super().__init__(*args, **ex)
        
        self.dims = {"n":n, "size":size}
        self.n = n
        self.estWedges = n * (n-1) * 2

    def create(self):
        self.numWedges = 0
        pos = numpy.array(self.coords)
        n = self.n
        self.pts = []
        
        for i in range(1, n):
            a = (i/n - 0.5)*pi
            p = []
            for j in range(n):
                b = j*2*pi/n
                tc = anglesToCoords([b, a])
                p.append(tc)
            self.pts.append(p)

        self.np = numpy.array([0, 1, 0])
        self.sp = numpy.array([0, -1, 0])

        for k in range(n):
            uv = numpy.array([(1/n, k/n), (0, k/n), (1/n, (k+1)/n)])
            wc = numpy.array([self.pts[0][k-1], self.sp, self.pts[0][k]])
            self.appendWedge(wc, -wc, uv)
            
        for i in range(n - 3, -1, -1):
            for j in range(n):
                uv = numpy.array([((i+1)/n, j/n), ((i+1)/n, (j+1)/n), ((i+2)/n, (j+1)/n)])
                wc = numpy.array([self.pts[i][j-1], self.pts[i][j], self.pts[i+1][j]])

                self.appendWedge(wc, -wc, uv)
                uv = numpy.array([((i+1)/n, j/n), ((i+2)/n, (j+1)/n), ((i+2)/n, j/n)])
                wc = numpy.array([self.pts[i][j-1], self.pts[i+1][j], self.pts[i+1][j-1]])
                self.appendWedge(wc, -wc, uv)

        for k in range(n):
            uv = numpy.array([((n-1)/n, k/n), ((n-1)/n, (k+1)/n), (1, k/n)])
            wc = numpy.array([self.pts[-1][k-1], self.pts[-1][k], self.np])
            self.appendWedge(wc, -wc, uv)

modelList = {}
class VertModel(VertObject):
    def __init__(self, *args, filename=None, size=1, mtlNum=0,
                 animated=False, mc=False, blender=False, **ex):
        """Loads .obj files, special cases for Mineways and Blender exports"""

        if "/" in filename:
            self.path = "/".join(filename.split("/")[:-1]) + "/"
        else:
            self.path = ""
        self.mtlName = None
        self.nextMtl = None
        alpha = None
        mip = False
        c = False
        refl = None
        add = None
        if "texture" in ex:
            self.mtlTex = ex["texture"]
            c = True
            del ex["texture"]

        self.subDiv = False
        if "subDiv" in ex:
            self.subDiv = ex["subDiv"]

        if not c:
            with open(filename) as f:
                for line in f:
                    if (line == "\n") or (line[0] == "#"):
                        continue
                    else:
                        t = line.split()
                        if t[0] == "mtllib":
                            self.mtl = self.path + t[1]
                            break
            cmtl = -1
            texnames = []
            self.texMap = {}
            cMtlName = None
            with open(self.mtl) as f:
                for line in f:
                    if (line == "\n") or (line[0] == "#"):
                        continue
                    else:
                        t = line.split()
                        if len(t) == 0: continue
                        if t[0] == "newmtl":
                            if not blender:
                                cmtl += 1
                                if cmtl == mtlNum:
                                    self.mtlName = t[1]
                            else:
                                cMtlName = t[1]
                        elif t[0] == "map_Kd":
                            if not blender and cmtl == mtlNum:
                                self.mtlTex = self.path + t[1]
                                c = True
                            if blender:
                                self.texMap[cMtlName] = "tex_" + t[1]
                                if t[1] not in texnames:
                                    texnames.append(t[1])
                                    cmtl += 1
                                    if cmtl == mtlNum:
                                        self.mtlName = "tex_" + t[1]
                                        self.mtlTex = self.path + t[1]
                                        c = True

                        elif t[0] == "map_d":
                            if cmtl == mtlNum:
                                alpha = self.path + t[1]
                        elif t[0] == "mip":
                            if cmtl == mtlNum:
                                mip = True
                        elif t[0] == "add":
                            if cmtl == mtlNum:
                                add = float(t[1])
                        elif t[0] == "refl":
                            if cmtl == mtlNum:
                                refl = t[1]
            if not mc:
                if cmtl > mtlNum:
                    self.nextMtl = VertModel(*args, filename=filename, size=size,
                                             animated=animated,
                                             mtlNum=mtlNum+1, blender=blender,
                                             **ex)
                    args[0].vertObjects.append(self.nextMtl)
        if not c:
            self.mtlTex = "../Assets/Magenta.png"
            print("Missing texture")

        #ex = dict(ex)
        if alpha is not None:
            ex["alpha"] = alpha
        if mip:
            ex["mip"] = mip

        if refl is not None: ex["reflect"] = refl
        if add is not None:
            if "useShaders" in ex: ex["useShaders"]["add"] = add
            else: ex["useShaders"] = {"add":add}
            if "mip" in ex: del ex["mip"]
        
        super().__init__(*args, texture=self.mtlTex,
                         **ex)
        
        self.animated = animated
        
        self.numWedges = 0
        self.filename = filename
        self.size = size
        self.estWedges = 0
        with open(filename) as f:
            for line in f:
                if line[0] == "f":
                    self.estWedges += len(line.split()) - 3

        self.mc = mc
        self.blender = blender

        try:
            if "plant" in self.mtlTex or "as12" in self.mtlTex:
                self.subDiv = 0; self.mip = None
        except: pass
        try:
            if "plant" in self.mtlTex or "as12" in self.mtlTex:
                del self.viewer.matShaders[self.texNum]["cull"]
        except: pass
    
    def create(self):        
        filename = self.filename
        self.hasTex = True
        
        global modelList
        if filename in modelList:
            if self.mtlTex in modelList[filename]:
                tmod = modelList[filename][self.mtlTex]
                self.wedgePoints = tmod["wp"]
                self.vertNorms = tmod["vn"]
                self.u = tmod["u"]
                self.v = tmod["v"]
                self.numWedges = tmod["nw"]
                self.bones = tmod["b"]
                return
        
        size = self.size

        self.points = []
        self.vts = []
        self.vns = []
        if self.animated:
            self.bones = []
        activeMat = False
        
        if "plant_01.png" in self.mtlTex or "as12" in self.mtlTex:
            self.subDiv = False
        
        if self.subDiv: aw = self.appendWedgeSafe
        else: aw = self.appendWedge
        if self.mc: activeMat = True
        
##        sl = []
        
        with open(filename) as f:
            line = f.readline()
            while not (line == ""):
                if line[0] == "#":
                    line = f.readline()
                elif (line == "\n"):
                    line = f.readline()
                else:
                    t = line.split()
                    if t[0] == "v":
                        a = [float(s) for s in t[1:4]]
                        a[2] = -a[2]
                        self.points.append(a)
                    elif t[0] == "f":
                        if activeMat:
                        #if len(t) == 4:
                            c = [self.points[int(s.split("/")[0]) - 1] for s in t[1:]]
                            try:
                                tx = [self.vts[int(s.split("/")[1]) - 1] for s in t[1:]]
                            except ValueError:
                                tx = [(0,0),(0,0),(0,0)]
                                self.hasTex = False
                            n = [self.vns[int(s.split("/")[2]) - 1] for s in t[1:]]
                            aw(numpy.array(c), -numpy.array(n), numpy.array(tx))
                            if self.animated:
                                self.bones.append([int(s.split("/")[3]) for s in t[1:]])
##                        elif len(t) == 5:
##                            c = [self.points[int(s.split("/")[0]) - 1] for s in t[1:4]]
##                            tx = [self.vts[int(s.split("/")[1]) - 1] for s in t[1:4]]
##                            n = [self.vns[int(s.split("/")[2]) - 1] for s in t[1:4]]
##                            aw(numpy.array(c), -numpy.array(n), numpy.array(tx))
##                            c2 = [self.points[int(s.split("/")[0]) - 1] for s in [t[1],t[3],t[4]]]
##                            tx2 = [self.vts[int(s.split("/")[1]) - 1] for s in [t[1],t[3],t[4]]]
##                            n2 = [self.vns[int(s.split("/")[2]) - 1] for s in [t[1],t[3],t[4]]]
##                            aw(numpy.array(c2), -numpy.array(n2), numpy.array(tx2))

##                            if "Lights" in self.texName:
##                                sl.append({"i":[2,2,2], "pos":np.average(c,axis=0),"vec":-np.array(n[0])})
                    elif t[0] == "vt":
                        # uv is actually vu
                        self.vts.append((float(t[2]), float(t[1])))
                    elif t[0] == "vn":
                        n = [float(s) for s in t[1:4]]
                        n[2] = -n[2]
                        self.vns.append(n)
                    elif t[0] == "usemtl":
                        if t[1] == self.mtlName:
                            activeMat = True
                        elif self.blender and self.texMap[t[1]] == self.mtlName:
                            activeMat = True
                        else:
                            activeMat = False
                    line = f.readline()
        
##        if "Lights" in self.texName:
##            self.viewer.atriumLights = sl
##            a = []
##            for b in sl:
##                try: b["pos"] = np.round(b["pos"], 2).tolist()
##                except: pass
##                try: b["vec"] = np.round(b["vec"], 2).tolist()
##                except: pass
##                a.append(b)
##            import json
##            with open("LightsCB.txt", "w") as x: x.write(json.dumps(a))

        if filename not in modelList:
            modelList[filename] = {}
        elif self.mtlTex not in modelList[filename]:
            tm = {"wp":self.wedgePoints, "vn":self.vertNorms,
                  "u":self.u, "v":self.v, "nw": self.numWedges, "b":self.bones}
            modelList[filename][self.mtlTex] = tm
        
        del self.vns, self.vts

    def rotateAll(self, rr):
        if self.nextMtl is not None:
            self.nextMtl.rotateAll(rr)
        self.rotate(rr)
    def translateAll(self, cc):
        if self.nextMtl is not None:
            self.nextMtl.translateAll(cc)
        self.coords = cc
    
    def transformAll(self, origin=False, early=False):
        if self.nextMtl is not None:
            self.nextMtl.transformAll(origin, early)
        self.transform(origin, early)

    def getTexNums(self, r=None):
        if r is None:
            r = [self.texNum]
        if self.nextMtl is not None:
            r.append(self.nextMtl.texNum)
            self.nextMtl.getTexNums(r)
        return r

def normalize(a):
    return a / np.linalg.norm(a)


class VertTerrain0:
    def __init__(self, coords, heights, scale=1,
                 vertScale=1, vertPow=1, vertMax=None):

        self.coords = np.array(coords)
        self.scale = scale
        
        assert type(heights) is str
        himg = Image.open(heights)
        if himg.size[0] != himg.size[1]:
            print("not square, cropping")
            sm = min(himg.size)
            himg = himg.crop((0,0,sm,sm))
        if himg.mode == "F":
            self.heights = numpy.array(himg)
        else:
            gr = himg.convert("L")
            hmap = numpy.array(gr)
            self.heights = hmap / 255
        self.size = numpy.array(himg.size) - 1

        self.heights *= vertScale
        if vertPow != 1:
            vertMax = vertMax * vertScale
            self.heights = self.heights**vertPow / vertMax**(vertPow-1)

    def getHeight(self, x, z):
        """World coords x,z -> world coord y"""
        landCoord = (numpy.array([x, 0, z]) - self.coords) / self.scale
        tex1 = int(landCoord[0] % (self.size[0]+1))
        tex2 = int(landCoord[2] % (self.size[1]+1))
        h = self.heights[tex1, tex2]

        try:
            if self.scale.shape[0] == 3:
                s = self.scale[1]
        except:
            s = self.scale
        return h * s + self.coords[1]
        

class VertTerrain(VertObject):
    def __init__(self, *args, size=(20,20), heights=None, uvspread=2,
                 vertScale=1, vertPow=1, vertMax=None, **ex):
        """heights -> array dims (size+1, size+1) OR filename"""
        super().__init__(*args, **ex)
        
        self.size = numpy.array(size)
        self.heights = heights

        if type(heights) is str: #Filename
            himg = Image.open(heights)
            if himg.size[0] != himg.size[1]:
                print("not square, cropping")
                sm = min(himg.size)
                himg = himg.crop((0,0,sm,sm))
            if himg.mode == "F":
                self.heights = numpy.array(himg)
            else:
                gr = himg.convert("L")
                hmap = numpy.array(gr)
                self.heights = hmap / 255
            self.size = numpy.array(himg.size) - 1
        elif heights is None:
            self.heights = numpy.zeros(self.size + 1)
        else:
            self.heights = heights
            self.size = numpy.array(heights.shape) - 1

        self.heights *= vertScale
        if vertPow != 1:
            vertMax = vertMax * vertScale
            self.heights = self.heights**vertPow / vertMax**(vertPow-1)
            
        self.estWedges = self.size[0] * self.size[1] * 2

        self.uvspread = uvspread
        self.texMode = "repeat"

    def create(self):
        self.heights = numpy.array(self.heights)
        
        self.pts = []
        for i in range(self.size[0] + 1):
            ri = numpy.repeat(i, self.size[1]+1)
            rj = numpy.arange(self.size[1]+1)
            row = numpy.stack((ri, self.heights[i], rj)).T
            self.pts.append(row)
        
        self.pts = numpy.array(self.pts)
        
        self.norms = numpy.empty((self.size[0] + 1, self.size[1] + 1, 3),
                                 dtype="float")
        self.norms[0,:] = [0, -1, 0]
        self.norms[-1,:] = [0, -1, 0]
        self.norms[:,0] = [0, -1, 0]
        self.norms[:,-1] = [0, -1, 0]
        oo = numpy.ones((self.size[0]-1,))
        zz = numpy.zeros((self.size[0]-1,))
        p = self.heights[1][1:-1]
        p1 = self.heights[0][1:-1]
        p3 = self.heights[2][1:-1]
        for i in range(1, self.size[0]):
            p1 = p
            p = p3
            p2 = self.heights[i][:-2]
            p3 = self.heights[i+1][1:-1]
            p4 = self.heights[i][2:]
            v1 = np.stack((oo, p-p1, zz))
            v2 = np.stack((zz, p-p2, oo))
            v3 = np.stack((-oo, p-p3, zz))
            v4 = np.stack((zz, p-p4, -oo))
            n1 = normalize(np.cross(v1, v2, axis=0))
            n2 = normalize(np.cross(v2, v3, axis=0))
            n3 = normalize(np.cross(v3, v4, axis=0))
            n4 = normalize(np.cross(v4, v1, axis=0))
            nn = np.stack((n1, n2, n3, n4))
            self.norms[i][1:-1] = np.average(nn, axis=0).T
            self.norms[i][0] = np.average(nn[:,:,0], axis=0)
            self.norms[i][0] += n2[:,0] - n2[:,1]
            self.norms[i][-1] = np.average(nn[:,:,-1], axis=0)
            self.norms[i][-1] += n4[:,-1] - n4[:,-2]
        self.norms[0] = self.norms[1]
        self.norms[-1] = self.norms[-2]

        sp = self.uvspread
        for i in range(self.size[0]):
            for j in range(self.size[1]):
                wc = numpy.array([self.pts[i][j], self.pts[i+1][j], self.pts[i][j+1]])
                n = numpy.array([self.norms[i][j], self.norms[i+1][j], self.norms[i][j+1]])
                tx = numpy.array([(i, j), (i+0.99, j), (i, j+0.99)])
                self.appendWedge(wc, n, tx/sp)

                wc = numpy.array([self.pts[i+1][j+1], self.pts[i][j+1], self.pts[i+1][j]])
                n = numpy.array([self.norms[i+1][j+1], self.norms[i][j+1], self.norms[i+1][j]])
                tx = numpy.array([(i+0.99, j+0.99), (i, j+0.99), (i+0.99, j)])
                self.appendWedge(wc, n, tx/sp)

    def getHeight(self, x, z):
        """World coords x,z -> world coord y"""
        landCoord = (numpy.array([x, 0, z]) - self.coords) / self.scale
        texr1 = landCoord[0] % (self.size[0]+1)
        tex1 = int(texr1)
        texr1 -= tex1
        texi1 = 1-texr1
        texr2 = landCoord[2] % (self.size[1]+1)
        tex2 = int(texr2)
        texr2 -= tex2
        texi2 = 1-texr2
        h0 = self.heights[tex1, tex2]
        h1 = self.heights[min(tex1+1, self.heights.shape[0]-1), tex2]
        h2 = self.heights[tex1, min(tex2+1,self.heights.shape[1]-1)]
        h3 = self.heights[min(tex1+1, self.heights.shape[0]-1),
                          min(tex2+1, self.heights.shape[1]-1)]
        h = h0*texi1*texi2 + h1*texr1*texi2 + h2*texi1*texr2 + h3*texr1*texr2
        try:
            if self.scale.shape[0] == 3:
                s = self.scale[1]
        except:
            s = self.scale
        return h * s + self.coords[1]
    
class VertPlane(VertObject):
    name="Plane"
    def __init__(self, *args, n=8, h1=[4, 0, 0], h2=[0, 8, 0],
                 norm=False, **ex):
        super().__init__(*args, **ex)
        self.estWedges = n**2 * 2
        self.h1 = numpy.array(h1, dtype="float64")
        self.h2 = numpy.array(h2, dtype="float64")
        if norm is False:
            normal = numpy.cross(self.h1, self.h2)
            normal /= numpy.linalg.norm(normal)
        else:
            normal = numpy.array(norm, dtype="float64")
        self.normal = -normal
        self.n = n

    def create(self):
        n = self.n
        m1 = self.h1/n
        m2 = self.h2/n
        norm = numpy.repeat([self.normal], 3, 0)
        for i in range(n):
            for j in range(n):
                c = m1*i + m2*j
                coords = numpy.array([c, c + m2, c + m1])
                uv = numpy.array([(i/n, j/n), (i/n, (j+1)/n), ((i+1)/n, j/n)])
                coords2 = numpy.array([c + m1 + m2, c + m1, c + m2])
                uv2 = numpy.array([((i+1)/n, (j+1)/n),
                                   ((i+1)/n, j/n), (i/n, (j+1)/n)])
                self.appendWedge(coords, norm, uv)
                self.appendWedge(coords2, norm, uv2)
