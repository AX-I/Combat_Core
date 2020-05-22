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
from math import sin, cos, pi, asin, acos, log2
import numexpr as ne
import numpy as np

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
