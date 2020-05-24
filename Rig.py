# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Rig.py) is part of AXI Visualizer and AXI Combat.
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

# Skeletal animation

from math import sin, cos, pi
import numpy as np

class Rig:
    def __init__(self, r, scale=1, numOffset=0):
        b = {}
        self.numOffset = numOffset
        self.recurseRig(b, r, scale)
        self.rigChildren(b, r)
        self.allBones = list(b[x] for x in sorted(b))
        self.b0 = self.allBones[0]

    def recurseRig(self, b, r, s):
        if "N" in r:
            b[r["boneNum"]] = Bone(s*np.array(r["origin"]), numBones=r["N"],
                                   bn=r["boneNum"], nO=self.numOffset)
        else:
            b[r["boneNum"]] = Bone(s*np.array(r["origin"]),
                                   bn=r["boneNum"], nO=self.numOffset)
        for i in range(len(r["children"])):
            self.recurseRig(b, r["children"][i], s)

    def rigChildren(self, b, r):
        for i in range(len(r["children"])):
            b[r["boneNum"]].addChild(b[r["children"][i]["boneNum"]])
            self.rigChildren(b, r["children"][i])

    def importPose(self, p, updateRoot=True):
        self.b0.importPose(p, updateRoot=updateRoot)
    def exportPose(self, p):
        return self.b0.exportPose(p)
    def getTransform(self):
        return self.b0.getTransform()

    def interpPose(self, p0, p1, t):
        self.importPose(self.interpTree(p0, p1, t), updateRoot=False)
    def interpTree(self, p0, p1, t, r=0):
        a0 = np.array(p0["angle"]) % (2*pi)
        a1 = np.array(p1["angle"]) % (2*pi)
        for n in range(3):
            n0 = a0[n]
            n1 = a1[n]
            if abs(n1 - n0) > pi:
                if n1 > n0:
                    a0[n] += 2*pi
                else:
                    a1[n] += 2*pi
        
        ang = a0 * (1-t) + a1 * t
        
        if "children" not in p0 or "children" not in p1:
            return {"angle":ang}
        p = []
        for i in range(len(p0["children"])):
            p.append(self.interpTree(p0["children"][i], p1["children"][i], t, r=1))
        return {"angle":ang, "children":p}
        
class Bone:
    def __init__(self, offset=(0,0,0), origin=None, rot=(0,0,0),
                 bn=None, numBones=None, nO=0):

        self.boneNum = bn + nO
        self.numOffset = nO
        self.N = numBones
        
        self.children = []
        self.parent = None
        
        if origin is None: self.origin = np.array(offset, dtype="float")
        else: self.origin = np.array(origin, dtype="float")
        self.offset = np.array((*offset, 1), dtype="float")

        self.rotate(rot)

    def exportRig(self, r=0):
        p = [c.exportRig(r+1) for c in self.children]

        o = self.origin
        if self.parent is not None:
            o -= self.parent.origin
        d = {"origin":list([round(x,6) for x in o]),
             "boneNum":self.boneNum, "children":p}
        if r == 0:
            d["N"] = self.N
        return d

    def exportPose(self):
        if len(self.children) == 0:
            return {"angle":[round(x, 6) for x in self.angles.tolist()]}
        
        p = [c.exportPose() for c in self.children]
        return {"angle":[round(x, 6) for x in self.angles.tolist()], "children":p}

    def importPose(self, p, r=0, updateRoot=True):
        self.angles = p["angle"]
        if updateRoot:
            self.rotate()
        if "children" not in p:
            p["children"] = []
        for i in range(min(len(self.children), len(p["children"]))):
            self.children[i].importPose(p["children"][i], r+1)

    def addChild(self, child):
        self.children.append(child)
        child.parent = self
        child.origin += self.origin

    def getPoints(self, p):
        """For drawing axes"""
        t = self.TM
        p = p @ t[:3,:3] + t[3,:3]
        return p

    def getTransform(self):
        b = np.empty((4*self.N,4), dtype="float")
        self.trans(b)
        return b

    def trans(self, bt):
        self.TM = self.transMat
        if self.parent is not None:
            self.TM = self.TM @ self.parent.TM
        sn = self.boneNum - self.numOffset
        bt[4*sn:4*sn+4] = self.TM
        
        for c in self.children:
            c.trans(bt)

    def rotate(self, rr=None):
        if rr is None: rr = self.angles
        else: self.angles = rr
        self.angles = np.array(self.angles)
        rotX = np.array([[1, 0, 0],
                         [0, cos(rr[0]), -sin(rr[0])],
                         [0, sin(rr[0]), cos(rr[0])]])
        rotY = np.array([[cos(rr[1]), 0, sin(rr[1])],
                         [0, 1, 0],
                         [-sin(rr[1]), 0, cos(rr[1])]])
        rotZ = np.array([[cos(rr[2]), -sin(rr[2]), 0],
                         [sin(rr[2]), cos(rr[2]), 0],
                         [0, 0, 1]])
        self.rotMat = rotX @ rotZ @ rotY
        self.updateTM()

    def updateTM(self):
        self.transMat = np.zeros((4,4))
        self.transMat[:3,:3] = self.rotMat
        self.transMat[3] = self.offset
