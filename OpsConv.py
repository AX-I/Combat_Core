# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
#
# This file (OpsConv.py) is part of AXI Combat.
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

# Convenience ops

import pyopencl as cl
import moderngl

import sys, os
if getattr(sys, "frozen", False): PATH = os.path.dirname(sys.executable) + "/"
else: PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

def genInfo(write=True):
    if getSettings(False)["Render"] == "GL":
        return genInfo_GL(write)
    else:
        return genInfo_CL(write)

def genInfo_CL(write=True):
    infotext = """Information about OpenCL devices on your computer.\n
If you are experiencing any problems or glitches running
AXI Combat, try changing render devices in Settings.
If only one device is available try updating its drivers.\n
"""

    pl = cl.get_platforms()
    if write:
        with open(PATH + "CLInfo.txt", "w") as f:
            f.write(infotext)
            for i in range(len(pl)):
                p = pl[i]
                f.write("Platform: " + p.name + "\n")
                dv = p.get_devices()
                for j in range(len(dv)):
                    f.write("  Device ["+str(i)+":"+str(j)+"] => " + dv[j].name + "\n")

    a = [p.name for p in pl]
    b = [[dv.name for dv in p.get_devices()] for p in pl]
    return (a, b)

def genInfo_GL(write=True):
    ctx = moderngl.create_standalone_context()
    a = [ctx.info["GL_VENDOR"]]
    b = [[ctx.info["GL_RENDERER"]]]
    return (a, b)


def getContext():
    if getSettings(False)["Render"] == "GL":
        return getContext_GL()
    else:
        return getContext_CL()

def getContext_CL():
    import os
    try:
        with open(PATH + "Settings.txt") as f:
            for line in f:
                if line[:2] == "CL":
                    os.environ["PYOPENCL_CTX"] = line[3:]
                    break
    except FileNotFoundError:
        with open(PATH + "Settings.txt", "w") as f:
            f.write("Settings for AXI Visualizer\n\nCL=0:0\n")
        os.environ["PYOPENCL_CTX"] = "0:0"
    except:
        os.environ["PYOPENCL_CTX"] = "0:0"

    try:
        ctx = cl.create_some_context()
    except cl._cl.RuntimeError:
        try:
            os.environ["PYOPENCL_CTX"] = os.environ["PYOPENCL_CTX"].split(":")[0]
            ctx = cl.create_some_context()
        except cl._cl.RuntimeError:
            raise
    return ctx

def getContext_GL():
    ctx = moderngl.create_standalone_context()
    return ctx


def getSettings(write=True):
    settings = {"Render":"GL",
                "CL":"0:0", "W":640, "H":400, "FOV":70, "SH":768,
                "FS":1, "FV":1, "BL":1, "SSR":0, "RTVL":1,
                "Uname":0, "Volume":0.2, "VolumeFX":0.3, "Record":0, "VR":0,
                "AutoRes":0, "Mouse":20}
    c = 0; newFile = False
    try:
        with open(PATH + "Settings.txt") as sf:
            for line in sf:
                if not "=" in line: continue
                k, v = line.replace("\n", "").split("=")
                if k in settings:
                    try: settings[k] = int(v)
                    except: settings[k] = v
                    c += 1
    except FileNotFoundError: newFile = True
    if c < len(settings): newFile = True
    if newFile and write:
        with open(PATH + "Settings.txt", "w") as f:
            z = zip(list(settings.keys()), [str(x) for x in settings.values()])
            f.write("Settings for AXI Visualizer\n\n")
            f.write("\n".join(["=".join(a) for a in z]))
    return settings

def writeSettings(settings):
    with open(PATH + "Settings.txt", "w") as f:
        z = zip(list(settings.keys()), [str(x) for x in settings.values()])
        f.write("Settings for AXI Visualizer\n\n")
        f.write("\n".join(["=".join(a) for a in z]))
