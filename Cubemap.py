# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Cubemap.py) is part of AXI Visualizer and AXI Combat.
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

# Cubemap for Visualizer

from math import sqrt, sin, cos, pi
import numpy
from PIL import Image, ImageTk
from tkinter import PhotoImage
import json

class CubeMap:
    def __init__(self, tex, setup=1, delraw=True):
        if type(tex) is str:
            ti = Image.open(tex).convert("RGB")
            m = ti.size[1]
            if m*6 != ti.size[0]:
                raise ValueError("Image is not w:h = 6:1!")
            self.m = m
            self.rawtexture = numpy.array(ti).astype("float")
            ta = self.rawtexture
            lum = 0.2626 * ta[:,:,0] + 0.6152 * ta[:,:,1] + 0.1222 * ta[:,:,2]
            ta[lum > 253] *= 4
            ta = ta*ta*(numpy.expand_dims(lum, 2)**(1/4)) / (4*8)
            numpy.clip(ta, None, 256*256-1, ta)
            self.rawtexture = ta
            #self.rawtexture = self.rawtexture * self.rawtexture / 4
            
        elif type(tex) is numpy.ndarray:
            if tex.shape[1] == (6*tex.shape[0]):
                self.rawtexture = tex
                self.m = tex.shape[0]
            else:
                self.rawtexture = numpy.concatenate(tex, axis=1)
                self.m = self.rawtexture.shape[0]
        else:
            raise TypeError("tex is not filename or numpy array!")
        #print(self.rawtexture.shape)
        #Image.fromarray((self.rawtexture/8).astype("uint8")).show()
            
        self.texture = []
        if   setup == 1: self.setupTexture()
        elif setup == 2: self.setupTex2()
        else           : self.texture = self.rawtexture
        
        if delraw: del self.rawtexture
        
    def setupTexture(self):
        m = self.m
        for i in range(6):
            self.texture.append(self.rawtexture[:,m*i:m*(i+1)].transpose((1, 0, 2)))
        temp = self.texture[1]
        self.texture[1] = self.texture[4]
        self.texture[4] = self.texture[5]
        self.texture[5] = self.texture[2]
        self.texture[2] = self.texture[0]
        self.texture[0] = temp
        
        self.texture[5] = self.texture[5].transpose((1, 0, 2))
        self.texture[2] = self.texture[2].transpose((1, 0, 2))
        self.texture[1] = self.texture[1].transpose((1, 0, 2))
        self.texture[4] = self.texture[4].transpose((1, 0, 2))
        
        self.texture[0] = numpy.flip(self.texture[0], axis=(0, 1))
        self.texture[1] = numpy.flip(self.texture[1], axis=1)
        self.texture[2] = numpy.flip(self.texture[2], axis=0)
        self.texture[3] = numpy.flip(self.texture[3], axis=0)
        
        self.texture = numpy.array(self.texture)
    
    def setupTex2(self):
        m = self.m
        for i in range(6):
            self.texture.append(self.rawtexture[:,m*i:m*(i+1)])
        temp = numpy.array(self.texture[1])
        self.texture[1] = self.texture[4]
        self.texture[4] = self.texture[5]
        self.texture[5] = self.texture[2]
        self.texture[2] = self.texture[0]
        self.texture[0] = temp
        
        self.texture[5] = self.texture[5].transpose((1, 0, 2))
        self.texture[2] = self.texture[2].transpose((1, 0, 2))
        self.texture[1] = self.texture[1].transpose((1, 0, 2))
        self.texture[4] = self.texture[4].transpose((1, 0, 2))
        
        self.texture[0] = numpy.flip(self.texture[0], axis=(0, 1))
        self.texture[1] = numpy.flip(self.texture[1], axis=0)
        self.texture[2] = numpy.flip(self.texture[2], axis=1)
        self.texture[3] = numpy.flip(self.texture[3], axis=1)
        
        self.texture = numpy.concatenate(self.texture, axis=1)
