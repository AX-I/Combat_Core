# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (AVSL.py) is part of AXI Visualizer and AXI Combat.
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

# AXI Visualizer Shading Language
# v0.2

try:
    from .Templates import *
except ModuleNotFoundError:
    from Templates import *

import sys, os

if getattr(sys, "frozen", False):
    PATH = os.path.dirname(sys.executable) + "/"
else:
    filepath = os.path.dirname(os.path.realpath(__file__)).replace('\\', '/')
    PATH = "/".join(filepath.split("/")[:-1]) + "/"

# template_func, template_setup, template_draw, template_end

def compile_file(fn, fo):
    with open(fn) as j:
        with open(fo, "w") as k:
            k.write(compile_AVSL(j.readlines(), True))
            k.write("\n\n\n")
            j.seek(0)
            k.write(compile_AVSL(j.readlines(), False))

def compile_AVSL(s, tiled):
    global a
    a = {"h":"", "a":"", "t":"", "c":""}
    g = None
    cstart = 0
    for line in s:
        cstart += 1
        if not len(line): continue
        if line[0] == "#":
            a["h"] += line
        elif line == "!shader_args\n": g = "a"
        elif line == "!shader_setup\n": g = "t"
        elif line == "!shader_core\n": g = "c"
        elif line[0] == "!": g = None
        elif g is not None: a[g] += line

    c = "".join(s[cstart:])

    out = a["h"]
    shader = AVShader(tiled)
    shader.shader_args(a["a"])
    shader.shader_setup(a["t"])
    shader.shader_draw()
    shader.shader_core(a["c"])

    out += shader.ARG_OUT + shader.SET_OUT + shader.DRAW_OUT + shader.END
    
    return out

class AVShader:
    def __init__(self, tiled):
        """Compiles AXI Visualizer Shaders, tiled or direct rasterization"""
        self.tiled = tiled
        self.Vargs = {}
        self.ARG_OUT = ""
        self.SET_OUT = ""
        self.DRAW_OUT = ""
        self.END = ""
        self.depth_compare = False
        self.depth_test = False
        
    def shader_args(self, s):
        # Screen XY and Z are always provided
        
        for a in s.splitlines():
            if len(a) == 0: continue
            if a[0] == ":":
                b = a.split(" ")
                
                # :Vertex float2 UV
                if b[0] == ":Vertex":
                    self.Vargs[b[2]] = {"type":b[1], "id":"vert" + b[2]}
                    self.ARG_OUT += "__global " + b[1] + " *" + b[2] + ", \n" 

                # :Texture ushort TR TG TB lenT
                elif b[0] == ":Texture": 
                    self.tex = b[1:]
                    for t in self.tex[1:4]:
                        self.ARG_OUT += "__global " + self.tex[0] + " *" + t + ", "
                    self.ARG_OUT += "const int " + self.tex[4] + ",\n"
            else:
                self.ARG_OUT += a + "\n"

        temp_func = template_func if self.tiled else template_func_small
        
        self.ARG_OUT = temp_func.replace("[SHADER_ARGS]", self.ARG_OUT)

    def shader_setup(self, s):

        # float2 uv3 = UV[ci+2] * z3;
        retr = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            for i in range(3):
                retr += attr["type"] + " " + attr["id"] + str(i+1)
                retr += " = " + v + "[ci+" + str(i) + "]"
                if True: retr += " * z" + str(i+1)
                retr += "; \n"

        # float2 uvt;
        temp = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            temp += attr["type"] + " " + attr["id"] + "temp; \n"


        # ytemp = y1; xtemp = x1; uvt = uv1; zt = z1;
        # y1 = y2; x1 = x2; uv1 = uv2; z1 = z2;
        # y2 = ytemp; x2 = xtemp; uv2 = uvt; z2 = zt;
    
        y12 = "if (y1 > y2) { \n"
        y12 += "    ytemp = y1; xtemp = x1; zt = z1; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            y12 += attr["id"] + "temp = " + attr["id"] + "1; "
            
        y12 += "\n    y1 = y2; x1 = x2; z1 = z2; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            y12 += attr["id"] + "1 = " + attr["id"] + "2; "

        y12 += "\n    y2 = ytemp; x2 = xtemp; z2 = zt; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            y12 += attr["id"] + "2 = " + attr["id"] + "temp; "
        y12 += "}\n"

        sort = y12
        y23 = y12.replace("1", "9").replace("2", "3").replace("9", "2")
        sort += y23
        sort += y12

        # float uv4 = uv1 + ydiff1 * (uv3 - uv1);
        vert4 = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            vert4 += attr["type"] + " " + attr["id"] + "4 = " + attr["id"] + "1 + ydiff1 * ("
            vert4 += attr["id"] + "3 - " + attr["id"] + "1); \n"

        temp_setup = template_setup if self.tiled else template_setup_small
        
        out = temp_setup.replace("[SHADER_SETUP_RETRIEVE]", retr)
        out = out.replace("[SHADER_SETUP_TEMP]", temp)
        out = out.replace("[SHADER_SETUP_SORT]", sort)
        out = out.replace("[SHADER_SETUP_4TH]", vert4)

        out += s
        
        self.SET_OUT = out

    def shader_draw(self):
        
        # float2 slopeuv1 = (uv2-uv1) * ydiff1;        
        # float2 slopeuv2 = (uv4-uv1) * ydiff1;
        calc = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            calc += attr["type"] + " slope" + attr["id"] + "1 = ("
            calc += attr["id"] + "2 - " + attr["id"] + "1) * ydiff1; \n"
            calc += attr["type"] + " slope" + attr["id"] + "2 = ("
            calc += attr["id"] + "4 - " + attr["id"] + "1) * ydiff1; \n"

        # float2 cuv1 = uv1; float2 cuv2 = uv2;
        scan = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            scan += attr["type"] + " curr" + attr["id"] + "1 = " + attr["id"] + "1; "
            scan += attr["type"] + " curr" + attr["id"] + "2 = " + attr["id"] + "1; \n"

        # slopet = slope1; uvt = slopeuv1;
        # slope1 = slope2; slopeuv1 = slopeuv2;
        # slope2 = slopet; slopeuv2 = uvt;
        switch = "slopet = slope1; zt = slopez1; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            switch += attr["id"] + "temp = slope" + attr["id"] + "1; "
        switch += "\n slope1 = slope2; slopez1 = slopez2; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            switch += "slope" + attr["id"] + "1 = slope" + attr["id"] + "2; "
        switch += "\n slope2 = slopet; slopez2 = zt; "
        for v in self.Vargs:
            attr = self.Vargs[v]
            switch += "slope" + attr["id"] + "2 = " + attr["id"] + "temp; "

        # cuv1 = uv1 + (cy-y1) * slopeuv1;
        # cuv2 = uv1 + (cy-y1) * slopeuv2;
        clamp = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            ai = attr["id"] + "1 + (cy-y1) * slope" + attr["id"]
            clamp += "curr" + attr["id"] + "1 = " + ai + "1;\n"
            clamp += "curr" + attr["id"] + "2 = " + ai + "2;\n"

        # cuv1 += slopeuv1; cuv2 += slopeuv2;
        incr = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            incr += "curr" + attr["id"] + "1 += slope" + attr["id"] + "1; "
            incr += "curr" + attr["id"] + "2 += slope" + attr["id"] + "2; \n"

        temp_draw = template_draw if self.tiled else template_draw_small
        
        out = temp_draw.replace("[SHADER_DRAW_CALC_SLOPE]", calc)
        out = out.replace("[SHADER_DRAW_INIT_SCAN]", scan)
        out = out.replace("[SHADER_DRAW_SWITCH_SLOPE]", switch)
        out = out.replace("[SHADER_DRAW_CLAMP_TILE]", clamp)
        out = out.replace("[SHADER_DRAW_INC]", incr)

        calc1 = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            calc1 += " slope" + attr["id"] + "1 = ("
            calc1 += attr["id"] + "2 - " + attr["id"] + "1) * ydiff1; \n"
            calc1 += " slope" + attr["id"] + "2 = ("
            calc1 += attr["id"] + "4 - " + attr["id"] + "1) * ydiff1; \n"
        
        calc1 = calc1.replace(" = (", " = -(").replace("1)", "3)")

        scan1 = ""
        for v in self.Vargs:
            attr = self.Vargs[v]
            scan1 += "curr" + attr["id"] + "1 = " + attr["id"] + "3; "
            scan1 += "curr" + attr["id"] + "2 = " + attr["id"] + "3; \n"

        clamp1 = clamp.replace("1 + ", "3 + ").replace("-y1", "-y3")

        decr = incr.replace("+=", "-=")

        out = out.replace("[SHADER_DRAW_CALC_SLOPE 1]", calc1)
        out = out.replace("[SHADER_DRAW_INIT_SCAN 1]", scan1)
        out = out.replace("[SHADER_DRAW_CLAMP_TILE 1]", clamp1)
        out = out.replace("[SHADER_DRAW_DEC]", decr)

        self.DRAW_OUT = out

    def shader_core(self, s):
        c = s

        db = "ZBuf[localCoord]" if self.tiled else "F[wF * cy + ax]"
        c = c.replace(":IF_DEPTH_TEST", "if (" + db + " >= tz)")

        d = template_depth_compare if self.tiled else "\n"
        c = c.replace(":DEPTH_COMPARE", d)
            
        self.DRAW_OUT = self.DRAW_OUT.replace("[SHADER_CORE]", c)

        self.END = template_end if self.tiled else template_end_small

        
def compileAll(p="Shaders_src/", q="Shaders/"):
    with open(PATH + p + "Config.txt") as f:
        for line in f:
            if line == "\n": continue
            if line[0] != "#":
                n = line.replace("\n","").split(" ")
                compile_file(PATH + p + n[0], PATH + q + n[1])

#if __name__ == "__main__":
#    compileAll("", "../Shaders/")
