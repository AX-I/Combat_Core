# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
#
# This file (Phys.py) is part of AXI Combat.
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

import numpy as np
import math

D = 3
G = 9.8

def eucDist(a, b):
    c = (a[0] - b[0]) ** 2 + \
        (a[1] - b[1]) ** 2 + \
        (a[2] - b[2]) ** 2
    return math.sqrt(c)
def eucLen(a):
    return math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2])

def planeDist(a, n, p):
    return abs((a - p) @ n)

class Collider:
    def __init__(self):
        self.prop = None
        self.rb = None
        self.disabled = False
    def pointIn(self, p):
        raise NotImplementedError
    def isCollide(self, obj):
        raise NotImplementedError
    def collisionImpulse(self, obj):
        raise NotImplementedError
    def onCollide(self, obj):
        return True
    def update(self):
        if self.rb is not None:
            self.pos = self.rb.pos
            self.disabled = self.rb.disabled

class CircleCollider(Collider):
    t = "Circle"
    def __init__(self, radius, center, rb=None):
        super().__init__()
        self.r = radius
        self.dim = radius
        self.offset = np.array([0.,0,0])
        
        if rb != None:
            self.rb = rb
            self.offset = np.array(center)
            self.pos = rb.pos + self.offset
        else:
            self.pos = np.array(center)

    def update(self):
        if self.rb is not None:
            self.pos = self.rb.pos + self.offset
            self.disabled = self.rb.disabled

    def pointIn(self, p):
        if (eucDist(self.pos, p) < self.r):
            return True
        return False

    def onHit(self):
        self.isHit(self.num)

    def isCollide(self, obj):
        if obj.t == "Circle":
            if (eucDist(self.pos, obj.pos) < (self.r + obj.r)):
                return True
            return False

        if obj.t == "Terrain":
            return obj.isCollide(self)
        
        raise NotImplementedError

    def collisionImpulse(self, obj):
        if obj.t == "Circle":
            if eucDist(obj.pos, self.pos) == 0:
                self.pos[1] += 0.01

            cdir = (obj.pos - self.pos) / eucDist(obj.pos, self.pos)

            Vsit = self.rb.v @ cdir
            Voit = obj.rb.v @ cdir
            
            Vsc = self.rb.v - Vsit * cdir
            Voc = obj.rb.v - Voit * cdir
            
            Vst, Vot = collision(self.rb.M, obj.rb.M, Vsit, Voit,
                                 self.rb.el, obj.rb.el)
            
            Vsf = cdir * Vst + Vsc
            Vof = cdir * Vot + Voc
            
            self.rb.v = Vsf
            obj.rb.v = Vof

            offset = self.r + obj.r - eucDist(obj.pos, self.pos)

            tmass = self.rb.M + obj.rb.M
            self.rb.pos -= cdir * offset * self.rb.M / tmass * 1.01
            obj.rb.pos += cdir * offset * obj.rb.M / tmass * 1.01

        elif obj.t == "Terrain":
            obj.collisionImpulse(self)

class BulletCollider(CircleCollider):
    def __init__(self, radius, center, rb, damage=1, explode=False,
                 hl=2, blackHole=False):
        super().__init__(radius, center, rb)
        self.hc = 0
        self.dmg = damage
        self.explode = explode
        self.hl = 0 if self.explode else hl
        self.blackHole = blackHole
        
    def onCollide(self, obj):
        if obj.t == "Terrain":
            if self.hc >= self.hl:
                if self.explode: obj.onHit(self.rb.pos)
                self.disabled = True
                self.rb.disabled = True
                self.rb.pos[:] = 0.
                self.rb.forces = []
                self.hc = 0
                return False
            else:
                self.hc += 1
                return True
        try:
            if obj.prop == "player":
                obj.hc += self.dmg
                obj.onHit()

                if self.explode: obj.onExplode(self.rb.pos)
                
                self.disabled = True
                self.rb.disabled = True
                self.rb.pos[:] = 0.
                self.rb.forces = []
                return False
        except AttributeError: pass
        try:
            if obj.blackHole:
                if self.explode: obj.onHit(self.rb.pos)
                self.disabled = True
                self.rb.disabled = True
                self.rb.pos[:] = 0.
                self.rb.forces = []
                return False
        except AttributeError: pass
        return True

class TerrainCollider(Collider):
    t = "Terrain"
    def __init__(self, pos, dim, heights, scale=1):
        """dim -> D-1 nums (+heights)"""
        super().__init__()
        self.pos = np.array(pos)
        self.dim = np.array(dim)
        self.h = np.array(heights)
        self.S = scale
        
        self.pts = []
        for i in range(self.dim + 1):
            ri = np.repeat(i, self.dim+1)
            rj = np.arange(self.dim+1)
            row = np.stack((ri, self.h[i], rj)).T
            self.pts.append(row)
        
        self.pts = np.array(self.pts) * self.S + self.pos

    def isCollide(self, obj):
        self.colDist = None
        
        d1 = np.floor((obj.pos - obj.dim - self.pos) / self.S).astype("int")
        d2 = np.ceil((obj.pos + obj.dim - self.pos) / self.S).astype("int")
        
        selpts = self.pts[d1[0]:d2[0], d1[2]:d2[2]]

        hc = (obj.pos - obj.dim)[1]
        hm = (obj.pos + obj.dim)[1]
        for i in range(selpts.shape[0] - 1):
            for j in range(selpts.shape[1] - 1):
                if hm <= np.min(selpts[i:i+2,j:j+2,1]):
                    n = np.cross(selpts[i,j] - selpts[i,j+1], selpts[i,j+1] - selpts[i+1,j+1])
                    n /= eucLen(n)
                    pd = planeDist(obj.pos, n, selpts[i,j])
                    self.colNorm = n
                    self.colDist = obj.dim - pd
                    return True
                if hc <= np.max(selpts[i:i+2,j:j+2,1]):
                    n = np.cross(selpts[i,j] - selpts[i,j+1], selpts[i,j+1] - selpts[i+1,j+1])
                    n /= eucLen(n)
                    pd = planeDist(obj.pos, n, selpts[i,j])
                    if pd < obj.dim:
                        self.colNorm = n
                        self.colDist = obj.dim - pd
                        return True
                    n = np.cross(selpts[i,j] - selpts[i+1,j+1], selpts[i+1,j+1] - selpts[i+1,j])
                    n /= eucLen(n)
                    pd = planeDist(obj.pos, n, selpts[i+1,j+1])
                    if pd < obj.dim:
                        self.colNorm = n
                        self.colDist = obj.dim - pd
                        return True
        return False
    
    def collisionImpulse(self, obj):
        pd = self.colDist
        n = self.colNorm
        
        obj.rb.v = (obj.rb.v - (2 * obj.rb.v @ n) * n) * obj.rb.el
        if obj.t == "Circle":
            obj.rb.pos += (pd + 0.001) * n

def boundingBox(obj):
    if obj.t == "Rect":
        print("Why?")
        return BoxCollider(obj.pos, obj.dim)
    if obj.t == "Circle":
        return BoxCollider(obj.pos - obj.r, np.repeat(obj.r * 2, D))
    if obj.t == "Terrain":
        return BoxCollider(obj.pos + np.array([0, min(obj.h), 0]),
                                 [*obj.dim.tolist(), max(obj.h) - min(obj,h)])

class RigidBody:
    def __init__(self, mass, xyz, vel=None, rotvel=None, forces=None,
                 drag=0, usegravity=True, elasticity=1, noforces=False):
        """forces -> python list of vectors"""
        self.colliders = []
        self.wIndex = False
        self.M = np.float(mass)
        self.drag = drag
        self.pos = np.array(xyz, dtype="float")
        self.rot = np.array([0, 0, 0])
        self.disabled = False
        self.noforces = noforces
        if vel is None: self.v = np.zeros(D, dtype="float")
        else:           self.v = np.array(vel, dtype="float")
        
        if rotvel is None:  self.rotv = np.zeros(3, dtype="float")
        else:               self.rotv = np.array(rotvel, dtype="float")
        
        self.el = elasticity
            
        self.forces = [[0, (-G * int(usegravity)), 0]]
        if forces != None:
            self.forces.extend(forces)

    def addCollider(self, collObj):
        collObj.rb = self
        self.colliders.append(collObj)

    def update(self, dt, attractors=[]):
        if self.disabled: return
        self.forces = []
        if not self.noforces:
            for a in attractors:
                i = attractors[a]
                diff = (i["pos"] - self.pos)
                self.forces.append(diff * i["m"] * self.M / np.sum(diff*diff))
        self.v += np.sum(np.array(self.forces), axis=0) / self.M * dt
        
        self.pos += self.v * dt

def collision(ma, mb, va, vb, ea, eb):
    """1-dimensional -> (vaf, vbf)"""
    ee = (ea + eb) / 2
    vaf = (ee*mb*(vb-va) + ma*va + mb*vb) / (ma+mb)
    vbf = (ee*ma*(va-vb) + ma*va + mb*vb) / (ma+mb)
    return (vaf, vbf)

def elasticBounce(va):
    return -va

class World:
    def __init__(self):
        self.objs = []
        self.coLs = []
        self.attractors = {}

    def addRB(self, rb):
        self.objs.append(rb)
        rb.wIndex = len(self.objs) - 1
        if len(rb.colliders) > 0:
            self.coLs.extend(rb.colliders)

    def addCollider(self, coL):
        self.coLs.append(coL)
    def setAttractor(self, i, pos, mass):
        self.attractors[i] = {"pos":pos, "m":mass}
    def delAttractor(self, i):
        try: del self.attractors[i]
        except KeyError: pass

    def start(self):
        pass

    def checkColls(self):
        for i in self.coLs:
            i.update()
        
        for i in range(len(self.coLs)):
            if self.coLs[i].disabled: continue
            for j in range(i+1, len(self.coLs)):
                if self.coLs[j].disabled: continue
                
                if self.coLs[i].isCollide(self.coLs[j]):
                    if self.coLs[i].onCollide(self.coLs[j]) and \
                       self.coLs[j].onCollide(self.coLs[i]):
                        self.coLs[i].collisionImpulse(self.coLs[j])

    def stepWorld(self, dt=1, checkColl=True):
        """return # of collisions"""
        for o in self.objs:
            o.update(dt, attractors=self.attractors)
        
        if checkColl:
            self.checkColls()

if __name__ == "__main__":
    w = World()
    a = RigidBody(1, [1, 1, 1], usegravity=False, drag=0.001, vel=[0, 0, 1])
    w.addRB(a)
    b = RigidBody(1, [1, 2, 1], usegravity=False, drag=0.001, vel=[0, 0.5, 0.5])
    w.addRB(b)
    w.start()
    w.stepWorld()
