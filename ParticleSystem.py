# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (ParticleSystem.py) is part of AXI Visualizer and AXI Combat.
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

# Particle System for AXI Visualizer

import numpy as np
import numpy.random as nr
from Utils import viewVec
from math import sin, cos, pi
import numexpr as ne

def vVvert(a, b):
    b2 = b - pi/2
    v = np.array([sin(a) * cos(b2),
                  -sin(b2),
                  cos(a) * cos(b2)])
    return -v
def vVhorz(a, b):
    a2 = a + pi/2
    v = np.array([sin(a2), 0, cos(a2)])
    return -v

def rotMat2(a, b):
    rotX = np.array([[1, 0, 0],
                     [0, cos(b), -sin(b)],
                     [0, sin(b), cos(b)]])
    rotY = np.array([[cos(a), 0, sin(a)],
                     [0, 1, 0],
                     [-sin(a), 0, cos(a)]])
    return rotX @ rotY

class ParticleSystem:
    """Single emission"""
    def __init__(self, emitPos, emitDir, size=2,
                 opacity=0.6, color=(255, 255, 255),
                 vel=0.5, nParticles=1000,
                 randPos=0.5, randVel=0.2, randDir=0.1,
                 force=(0, 0, 0), drag=0.001,
                 lifespan=10, colorOverLife=None,
                 randColor=15, tex=None, shSize=2,
                 **ex):
        
        self.N = nParticles
        self.tex = tex
        self.shSize = shSize
        
        self.pc = []
        self.pv = []
        self.opacity = opacity
        self.c1 = np.array(color)
        self.c2 = np.array(color)
        if not (colorOverLife is None):
            self.c2 = np.array(colorOverLife)
        self.color = np.repeat(np.expand_dims(self.c1, 0), self.N, axis=0)
        self.randColor = randColor
        
        self.size = size
        
        self.pos = np.array(emitPos)
        self.emitDir = np.array(emitDir) + (0.5-nr.rand(2))*randDir
        self.vel = vel
        self.dv = viewVec(*emitDir) * vel
        self.force = np.array(force)
        self.drag = drag

        self.randPos = randPos
        self.randVel = randVel
        
        self.L = lifespan
        self.started = False
        
    def setup(self):
        self.ll = 0
        self.color = np.array(np.repeat(np.expand_dims(self.c1, 0), self.N, axis=0))
        self.color += (nr.randn(self.N, 3) * self.randColor).astype("int")
        self.color = np.clip(self.color, 0, 255)
        
        self.pc = (nr.randn(self.N, 3)) * self.randPos + self.pos
        self.pv = (nr.randn(self.N, 3)) * self.randVel + self.dv
        
        self.started = False
    
    def step(self):
        self.started = True
        
        if (self.dv > 0).any() or self.randVel > 0:
            self.pc += self.pv
            self.pv *= (1-self.drag)
        self.pv += self.force
        test = np.expand_dims(self.c1 * np.clip((self.L-self.ll)/self.L, 0, 1), 0)

        self.color = np.repeat(test, self.N, axis=0)
        self.color += np.repeat(np.expand_dims(self.c2 * np.clip(self.ll / self.L, 0, 1), 0), self.N, axis=0)
        
        self.ll += 1

        self.pos += self.dv

    def reset(self):
        del self.pc, self.pv, self.color
        self.setup()
        
class ContinuousParticleSystem(ParticleSystem):
    """Continous emission"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (self.N % self.L) > 0:
            raise ValueError("# must be divisible by lifespan!")

    def setup(self):
        super().setup()
        self.pl = np.arange(-self.L, 0, self.L/self.N)
        self.pe = [True] * (self.N // self.L)
        self.pe.extend([False] * (self.N - self.N // self.L))
        self.pe = np.array(self.pe)
        self.Rpc = np.array(self.pc)
        self.Rpv = np.array(self.pv)
        self.pc = self.Rpc[self.pe]
        self.pv = self.Rpv[self.pe]

        self.Rpcolor = np.full((self.N, 3), self.c1)
        self.started = False

    def step(self):
        self.started = True
        self.pl += 1
        self.Rpc[self.pe] += self.Rpv[self.pe]
        self.Rpv[self.pe] *= (1-self.drag)
        self.Rpv[self.pe] += self.force
        
        self.Rpcolor = self.c1 * np.expand_dims(
            np.clip((self.L-self.pl)/self.L, 0, 1), 1)
        self.Rpcolor += self.c2 * np.expand_dims(
            np.clip(self.pl / self.L, 0, 1), 1)

        self.ll += 1

        self.pc = self.Rpc[self.pe]
        self.pv = self.Rpv[self.pe]
        self.color = self.Rpcolor[self.pe]

        self.pe = (self.pl > 0) & (self.pl < self.L)

    def changeDir(self, newDir):
        self.dv = viewVec(newDir) * self.vel
        self.Rpv[self.pl < 0] = (0.5 - nr.randn(np.sum(self.pl < 0), 3)) * self.randVel + self.dv
    def changePos(self, newpos):
        self.Rpc[self.pl < 0] += newpos - self.pos
        self.pos[:] = newpos
    def reset(self):
        del self.pc, self.pv, self.color, self.pe, self.pl, self.Rpcolor
        self.setup()
