# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Utils.py) is part of AXI Visualizer and AXI Combat.
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

# Random utilities for 3D

from numpy import sqrt, ones_like, array
from math import sin, cos, pi, asin, acos, log2, ceil
import numpy as np

import multiprocessing as mp
from PIL import Image

def raySphereIntersect(p, v, c, r):
    m = (c-p) @ v
    d = (c-p) - m * v
    return (m > 0) & (np.linalg.norm(d) <= r)
    
def viewVec(a, b):
    v = np.array([sin(a) * cos(b),
                  -sin(b),
                  cos(a) * cos(b)])
    return v

def viewMat(a, b):
    a2 = a + pi/2
    b2 = b - pi/2
    v = np.array([[sin(a)*cos(b),   -sin(b),  cos(a)*cos(b)],
                  [-sin(a2),         0,        -cos(a2)],
                  [-sin(a)*cos(b2),  sin(b2),  -cos(a)*cos(b2)]])
    return v

def createMip(a):
    b = a[:-1:2] + a[1::2]
    c = b[:,:-1:2] + b[:,1::2]
    return c >> 2

def createMips(ar):
    """d -> debug / display images"""
    a = np.array(ar).astype("int")
    m = [a]
    for i in range(int(log2(ar.shape[0]))):
        a = createMip(a)
        m.append(a)
    m.reverse()
    dim = a.shape[-1]
    return np.concatenate([x.reshape(-1,dim) for x in m], axis=0)

def anglesToCoords(ab):
    x = cos(ab[0]) * cos(ab[1])
    y = sin(ab[1])
    z = sin(ab[0]) * cos(ab[1])
    return array((x, y, z))

def fmtTime(t):
    color = '\033[90m' if t<0.001 \
            else '\033[0m' if t<0.01 \
            else '\033[93m' if t<0.02 \
            else '\033[91m'
    return f'{color}{t:.4f}\033[0m'



def _loader(q_in, q_out, func):
    # q_in has elements (name, args)
    while True:
        a = q_in.get()
        if a is None: break
        r = func(*a[1])
        q_out.put((a[0], r))

class TexLoadManager:
    def __init__(self, func: callable, n_proc: int):
        self.P = n_proc

        self.dat = {}
        self.proc = []
        self.njobs = 0
        self.qi = mp.Queue()
        self.qo = mp.Queue()
        for i in range(self.P):
            p = mp.Process(target=_loader, args=(self.qi,self.qo,func))
            p.start()
            self.proc.append(p)

    def loadTex(self, tn, *args):
        self.qi.put((tn, args))
        self.njobs += 1
        return self.njobs - 1

    def collectTex(self, texlist):
        for i in range(self.njobs):
            r = self.qo.get()
            texlist[r[0]] = r[1]

    def cleanup(self):
        for p in self.proc: self.qi.put(None)
        for p in self.proc: p.join()
