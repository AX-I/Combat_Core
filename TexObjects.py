# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (TexObjects.py) is part of AXI Visualizer and AXI Combat.
#
# AXI Combat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# AXI Combat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AXI Combat. If not, see <https://www.gnu.org/licenses/>.
# ======== ========

# Textured Objects for AXI Visualizer

from math import sin, cos, pi
import numpy
import numpy as np
import numexpr as ne
from PIL import Image
from Utils import anglesToCoords
import json
import zlib

def imreadHDR(f):
    with open(f, "rb") as fp:
        dims = [int(i) for i in str(fp.readline(), "ascii").split(" ")]
        n = np.frombuffer(zlib.decompress(fp.read()), "float32")
        m = np.array(n).reshape(dims)
        return m

class TexSkyBox:
    def __init__(self, v, N, tex, rot=(0,0,0), hdrScale=32):

        self.pts = []
        self.wedgePoints = []
        self.vertNorms = []
        self.wedgePos = []
        self.u = []
        self.v = []
        self.viewer = v
        
        if tex.split(".")[-1] == "ahdr":
            i = imreadHDR(tex)
            ti = Image.fromarray(np.zeros_like(i, dtype="uint8"))
        else:
            ti = Image.open(tex).convert("RGB")
        m = ti.size[1]
        if m*6 == ti.size[0]:
            self.bottom = 1
        elif m*5 == ti.size[0]:
            self.bottom = 0
        else:
            raise ValueError("Image is not w:h = 6:1 or 5:1!")

        self.numWedges = 6 * m**2 * 2
        self.N = N + 1

        if tex.split(".")[-1] == "ahdr":
            ti = i #cv2.resize(i, (m, m*6))
            avg = np.average(ti)
            ne.evaluate("ti / avg * 256 * hdrScale", out=ti)
            ta = numpy.array(ti)[:,:,::-1]
        else:
            ti = Image.open(tex).convert("RGB")
            ta = numpy.array(ti).astype("float")
            ta *= 32*1.5

        numpy.clip(ta, None, 256*256-1, out=ta)

        a = ta.shape
        self.viewer.skyTex = ta.astype("uint16")
        

        self.viewer.vtextures.append(ta.astype("uint16"))
        self.viewer.vtNames[tex] = len(self.viewer.vtextures) - 1
        self.texNum = self.viewer.vtNames[tex]

        self.viewer.vertpoints.append([])
        self.viewer.vertnorms.append([])
        self.viewer.vertu.append([])
        self.viewer.vertv.append([])
        self.viewer.vertBones.append([])

        self.viewer.matShaders[self.texNum] = {"sky":1}

        rr = rot
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


    def created(self):
        N = self.N
        bb = 5 + self.bottom

        for i in range(N):
            a = i/(N-1) - 0.5
            for j in range(N):
                b = j/(N-1) - 0.5
                c = (a, b, 0.5)
                self.pts.append(c)
        self.pts = numpy.array(self.pts)
        
        t1 = self.pts[:,[2,1,0]]
        t2 = self.pts[:,[1,2,0]]
        r1 = numpy.array((1, -1, -1))
        r2 = numpy.array((1, -1, 1))
        r3 = numpy.array((1, 1, -1))
        r4 = numpy.array((-1, -1, 1))
        self.pts = numpy.array([r2*self.pts, r1*t1, -1*self.pts, r4*t1,
                                r3*t2, -1*t2]).reshape((bb, N, N, 3))

        self.pts = self.pts.reshape((-1,3))
        self.pts = self.pts @ self.rotMat
        self.pts = self.pts.reshape((bb, N, N, 3))

        M = N - 1
        for x in range(bb):
            for j in range(N-1):
                for i in range(N-1):
                    wc = numpy.array([self.pts[x][i][j],
                                      self.pts[x][i+1][j],
                                      self.pts[x][i][j+1]])
                    cc = numpy.array([((x + i/M)    , j/M),
                                      ((x + (i+1)/M), j/M),
                                      ((x + i/M)    , (j+1)/M)])
                    self.appendWedge(wc, cc)
                
                    w2 = numpy.array([self.pts[x][i+1][j+1],
                                      self.pts[x][i][j+1],
                                      self.pts[x][i+1][j]])
                    c2 = numpy.array([((x + (i+1)/M), (j+1)/M),
                                      ((x + i/M)    , (j+1)/M),
                                      ((x + (i+1)/M), j/M)])
                    self.appendWedge(w2, c2)
        
        self.wedgePoints = numpy.array(self.wedgePoints) @ self.rotMat

        tn = self.texNum
        self.viewer.vertpoints[tn] = self.wedgePoints * 1000
        self.viewer.vertnorms[tn] = ((1,0,0),)
        self.viewer.vertu[tn] = np.array(self.u) / 6
        self.viewer.vertv[tn] = np.array(self.v)
        
    def appendWedge(self, coords, uv):
        self.wedgePoints.append(coords)
        self.u.append(uv[:,0])
        self.v.append(uv[:,1])
