# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Visualizer.py) is part of AXI Visualizer and AXI Combat.
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

from tkinter import *
import numpy as np
import time

import threading
from queue import Empty, Full

import sys, os
import traceback

from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter, PngImagePlugin

from Menu import CombatMenu

import win32api
import win32con
import pywintypes

import pyautogui
def mouseMover(x, y):
    pyautogui.moveTo(x,y)

if getattr(sys, "frozen", False): PATH = os.path.dirname(sys.executable) + "/"
else: PATH = os.path.dirname(os.path.realpath(__file__)) + "/"
    
class ThreeDVisualizer(CombatMenu, Frame):
    def __init__(self, pipe, eq, infQ,
                 width, height,
                 mouseSensitivity=20,
                 downSample=1, record=False):

        self.P = pipe
        self.evtQ = eq
        self.infQ = infQ

        root = Tk()
        super().__init__(root)
        
        self.root = root
        self.root.title("AXI Combat")
        self.root.iconbitmap(PATH+"lib/AXI.ico")
        self.downSample = downSample
        self.W = width//downSample
        self.H = height//downSample
        self.W2 = self.W//2
        self.H2 = self.H//2
        
        self.panning = False
        self.rx, self.ry = 0, 0
        self.threads = []
        self.captureMouse = True
        self.rotSensitivity = mouseSensitivity / 20000
        self.panSensitivity = mouseSensitivity / 500

        self.empty = 0
        self.full = 0
        self.fs = False

        self.dirs = [False, False, False, False]
        
        self.timfps = np.zeros(6)
        self.numfps = 0

        self.xyselect = np.array((0,0))
        self._textImg = Image.new("RGB", (1,1))
        self.textSize = ImageDraw.Draw(self._textImg)
        self.drawUI = True
        self.drawControls = True
        try:
            f = open(PATH+"lib/Stat.txt")
            self.drawControls = False
        except: pass
        
        self.activeFS = True

        self.recVideo = False
        
        self.frameKeys = {}

        self.startMenu()

    def setWH(self, w, h):
        self.W = w
        self.H = h
        self.W2 = w//2
        self.H2 = h//2

    def startRender(self):
        self.d.bind("<Motion>", self.rotate)
        
        self.d.bind("<KeyPress-d>", self.moveR)
        self.d.bind("<KeyPress-a>", self.moveL)
        self.d.bind("<KeyPress-w>", self.moveU)
        self.d.bind("<KeyPress-s>", self.moveD)
        self.d.bind("<KeyRelease-d>", self.zeroH)
        self.d.bind("<KeyRelease-a>", self.zeroH)
        self.d.bind("<KeyRelease-w>", self.zeroV)
        self.d.bind("<KeyRelease-s>", self.zeroV)
        
        self.d.bind("q", self.tgMouseCap)
        self.d.bind("<F1>", self.tgCtrl)
        self.d.bind("<F2>", self.screenshot)
        self.d.bind("<F3>", self.tgUI)
        
        self.d.focus_set()

        self.finalRender = self.d.create_image((self.W/2, self.H/2))
        
        self.evtQ.put(["ready"])
        
        self.pipeLoop = self.d.after_idle(self.checkPipe)
        self.timeStart = time.time()
        self.totTime = 0
        self.frameNum = 0

        self.recVideo = bool(self.lSet["Record"])
        if self.recVideo:
            import cv2
            fout = PATH + "Test.avi"
            fc = cv2.VideoWriter_fourcc(*"MJPG")
            
            self.VIDOUT = cv2.VideoWriter(fout, fc, 24.0, (self.W, self.H))

    def runGame(self, *args):
        self.evtQ.put({"Run":args})
        
        self.title.grid_remove()

        self.createCoreWidgets()
        
        self.mtext = self.d.create_text((self.W2, self.H2 - 50),
                                        text="Loading...", fill="#FFF",
                                        font=("Times", 12))
        self.stext = self.d.create_text((self.W2, self.H2 + 50),
                                        text=self.loc[args[0]], fill="#FBF",
                                        font=("Times", 12))
        
        self.gtext = self.d.create_text((self.W2, self.H2 + 80),
                                        text=args[1], fill="#BFF",
                                        font=("Times", 10))
        
        bbox = (self.W2-30, self.H2-30, self.W2+30, self.H2+30)
        self.mbg = self.d.create_oval(bbox, fill="#444")
        self.meter = self.d.create_arc(bbox, fill="#08C", extent=1, outline="#08C")

        self.waitLoad()

    def waitLoad(self):
        self.ready = False
        try:
            p = self.evtQ.get(True, 0.05)
            if p == "Ready":
                self.ready = True
            else:
                self.d.itemconfig(self.meter, extent=min(359, p/100 * 360))
        except Empty: pass
        
        if self.ready:
            self.d.delete(self.mtext)
            self.d.delete(self.stext)
            self.d.delete(self.gtext)
            self.d.delete(self.mbg)
            self.d.delete(self.meter)
            self.startRender()
        else:
            self.waitLoop = self.after(20, self.waitLoad)

    def createCoreWidgets(self):
        #self.root.rowconfigure(0, weight=1)
        #self.root.columnconfigure(1, weight=1)
        #self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1, uniform="c")
        
        self.root.config(background="#000")
        self.root.bind("<Escape>", self.escapeMouse)
        self.root.bind("<F11>", self.tgFullScreen)

        self.d = Canvas(self, width=self.W, height=self.H,
                        highlightthickness=0, highlightbackground="black")
        self.d.grid(row=0, column=0, rowspan=10, sticky=N+E+S+W)
        self.d.config(cursor="none", background="#000")
        
    def getResolutions(self):
        i = 0
        res = []
        try:
            while True:
                m = win32api.EnumDisplaySettings(None, i)
                res.append((m.PelsWidth, m.PelsHeight))
                i += 1
        except: pass
        return set(res)
    def tgFullScreen(self, e=None):
        self.fs = not self.fs
        self.root.attributes("-fullscreen", self.fs)

        if not self.activeFS: return
        
        if self.fs:
            res = sorted(self.getResolutions())
            w = self.W
            h = self.H
            for x in res:
                if (x[0] >= w) and (x[1] >= h):
                    w, h = x
                    break
            dm = pywintypes.DEVMODEType()
            dm.PelsWidth = w
            dm.PelsHeight = h
            dm.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
            win32api.ChangeDisplaySettings(dm, 0)
        else:
            win32api.ChangeDisplaySettings(None, 0)
        
    
    def tgUI(self, e=None):
        self.drawUI = not self.drawUI
    def tgCtrl(self, e=None):
        self.drawControls = not self.drawControls
        
    def customAction(self, a, e):
        if a not in self.frameKeys:
            try: self.evtQ.put_nowait(a)
            except: pass
            self.frameKeys[a] = 1

    def checkPipe(self, cont=True):
        try: action = self.P.get(True, 0.02)
        except Empty: self.empty += 1
        else:
            try:
                if action is None:
                    cont = False
                    self.quit()
                elif action[0] == "render":
                    self.render(action[1])
                elif action[0] == "title":
                    self.root.title(action[1])
                elif action[0] == "bg":
                    self.d.config(background=action[1])
                elif action[0] == "key":
                    self.d.bind(action[1],
                                lambda x: self.customAction(action[1], x))
                elif action[0] == "screenshot":
                    self.screenshot()
            except Exception as e:
                logError(e, "checkPipe")
                cont = False
                self.quit()
        if cont:
            self.pipeLoop = self.d.after(4, self.checkPipe)
        self.frameNum += 1
        self.totTime += time.time() - self.timeStart
        self.timeStart = time.time()

    def setMouse(self, e):
        self.rx = e.x
        self.ry = e.y
    def escapeMouse(self, e):
        self.captureMouse = False
    def tgMouseCap(self, e):
        self.captureMouse = not self.captureMouse
        
    def attractMouse(self):
        mx = self.d.winfo_rootx() + self.W2
        my = self.d.winfo_rooty() + self.H2

        t = threading.Thread(target=mouseMover, args=(mx, my))
        t.start()
        self.threads.append(t)
        
    def rotate(self, e):
        if not self.captureMouse:
            return
        dx = (e.x - self.W2) * self.rotSensitivity
        dy = (e.y - self.H2) * self.rotSensitivity
        self.attractMouse()
        self.sendRot(dx, dy)

    def pan(self, e):
        dx = (e.x - self.rx) * self.panSensitivity
        dy = (e.y - self.ry) * self.panSensitivity
        self.rx = e.x
        self.ry = e.y
        self.sendPan((dx, dy))
        self.panning = True
        self.attractMouse()

    def moveU(self, e):
        if not self.dirs[0]:
            self.dirs[0] = True
            self.sendKey("u")
    def moveD(self, e):
        if not self.dirs[1]:
            self.dirs[1] = True
            self.sendKey("d")
    def moveR(self, e):
        if not self.dirs[2]:
            self.dirs[2] = True
            self.sendKey("r")
    def moveL(self, e):
        if not self.dirs[3]:
            self.dirs[3] = True
            self.sendKey("l")
    def zeroV(self, e):
        if self.dirs[0] or self.dirs[1]:
            self.dirs[0] = False
            self.dirs[1] = False
            self.sendKey("ZV")
    def zeroH(self, e):
        if self.dirs[2] or self.dirs[3]:
            self.dirs[2] = False
            self.dirs[3] = False
            self.sendKey("ZH")

    def screenshot(self, e=None):
        ts = time.strftime("%Y %b %d %H-%M-%S", time.gmtime())
        i = PngImagePlugin.PngInfo()
        i.add_text("pos", " ".join([str(round(x, 3)) for x in self.pos]))
        i.add_text("dir", " ".join([str(round(x, 3)) for x in self.vv]))
        #self.rawCFrame.save("Screenshots/Screenshot " + ts + ".png", pnginfo=i)
        self.cframe.save(PATH + "Screenshots/Screenshot " + ts + ".png", pnginfo=i)

    def sendKey(self, key):
        try: self.evtQ.put_nowait(("eventk", key))
        except Full: self.full += 1
    def sendRot(self, r1, r2):
        try: self.evtQ.put_nowait(("event", r1, r2))
        except Full: self.full += 1
    def sendPan(self, r):
        try: self.evtQ.put_nowait(("eventp", r))
        except Full: self.full += 1

    def render(self, data):
        self.frameKeys = {}

        rgb = data[0]
        ax = data[1]
        select = data[2]
        self.pos, self.vv = data[3]
        try: uInfo = data[4]
        except IndexError: uInfo = None
        
        fr = rgb
        
        # Postprocessing goes here
        
        #self.rawCFrame = Image.fromarray(fr.astype("uint8"), "RGB")
        
        if self.downSample > 1:
            c = fr
            for i in range(int(np.log2(self.downSample))):
                b = c[:-1:2] + c[1::2]
                b >>= 1
                c = b[:,:-1:2] + b[:,1::2]
                c >>= 1
            fr = c

        if self.drawUI:
            fr[self.H//2, self.W//2-4:self.W//2-1] = (255, 0, 255)
            fr[self.H//2, self.W//2+2:self.W//2+5] = (255, 0, 255)
            
            fr[self.H//2-4:self.H//2-1, self.W//2] = (255, 0, 255)
            fr[self.H//2+2:self.H//2+5, self.W//2] = (255, 0, 255)
        
        if (len(uInfo) > 0) and self.drawUI:
            y1, y2 = 10, 30
            
            x1, x2 = 10, self.W2 - 10
            fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * np.array([0.5, 0.4, 0.4])
            
            xf = x1 + int((self.W2 - 20) * uInfo["Health"])
            fr[y1:y2, x1:xf] += np.array([128, 0, 0], "uint16")

            x1, x2 = self.W2 + 10, self.W - 10
            fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * np.array([0.4, 0.5, 0.4])
            
            xf = x2 - int((self.W2 - 20) * uInfo["Energy"])
            fr[y1:y2, xf:x2] += np.array([0, 128, 0], "uint16")

            if "End" in uInfo:
                end = uInfo["End"]
                
                try: a = self.endTime
                except AttributeError: self.endTime = time.time()
                f = min(2, max(time.time() - self.endTime - 4, 0)) / 2
                
                endFont = ImageFont.truetype("arial.ttf", 48)

                self.drawText(fr, end[0], end[1], endFont, (0,0), f)

                if "Quit" in uInfo:
                    qt = uInfo["Quit"]
                    endFont = ImageFont.truetype("arial.ttf", 24)
                    self.drawText(fr, qt, (255,240,230,255), endFont, (48,0), f)

            if "nameTag" in uInfo:
                nt = uInfo["nameTag"]
                nFont = ImageFont.truetype("arialbd.ttf", 16)
                self.drawText(fr, nt, (255,240,230,255), nFont, (-20, 0), 1, 1)

        if self.drawControls:
            self.drawKey(fr, (self.H-60, 30), "A")
            self.drawKey(fr, (self.H-60, 60), "S")
            self.drawKey(fr, (self.H-60, 90), "D")
            self.drawKey(fr, (self.H-90, 60), "W")
            self.drawText(fr, "Move", (0,0,0), self.cFont,
                          (self.H2-60, -self.W2+125), blur=0)

            self.drawKey(fr, (self.H-30, 72), "")
            self.drawKey(fr, (self.H-30, 96), "")
            self.drawKey(fr, (self.H-30, 120), "")
            self.drawText(fr, "Jump", (0,0,0), self.cFont,
                          (self.H2-30, -self.W2+155), blur=0)
                        
            self.drawKey(fr, (self.H-105, 100), "E")
            self.drawText(fr, "Toggle Mouse Aim /\nFree Look", (0,0,0), self.cFont,
                          (self.H2-105, -self.W2+175), blur=0)
            
            self.drawKey(fr, (self.H-105, 20), "Q")
            self.drawText(fr, "Release/Capture\nMouse", (0,0,0), self.cFont,
                          (self.H2-135, -self.W2+55), blur=0)
            
            fi = "ZXCV"
            for i in range(4):
                self.drawKey(fr, (self.H-30, self.W2+30*(i-1)), fi[i])
            self.drawText(fr, "Fire", (0,0,0), self.cFont,
                          (self.H2-52, 0), blur=0)

            self.drawKey(fr, (60, 40), "F1")
            self.drawText(fr, "Show/hide controls", (0,0,0), self.cFont,
                          (-self.H2 + 80, -self.W2 + 70), blur=0)
            
            for i in range(1,5):
                self.drawKey(fr, (110, 30*i), str(i))
            self.drawText(fr, "Gesture", (0,0,0), self.cFont,
                          (-self.H2 + 130, -self.W2 + 70), blur=0)

            self.drawKey(fr, (self.H-60, self.W-90), "↑")
            self.drawKey(fr, (self.H-30, self.W-90), "↓")
            self.drawText(fr, "Zoom", (0,0,0), self.cFont,
                          (self.H2-45, self.W2-55), blur=0)

        if self.recVideo:
            self.VIDOUT.write(fr.astype("uint8")[:,:,::-1])
        
        self.cframe = Image.fromarray(fr.astype("uint8"), "RGB")

        self.cf = ImageTk.PhotoImage(self.cframe)

        self.d.tk.call((".!threedvisualizer.!canvas",
                        "itemconfigure", self.finalRender,
                        "-image", self.cf))

    def drawKey(self, fr, c, char, size=12, fill=255, opacity=0.6):
        """c => (x, y)"""
        y1, y2, x1, x2 = c[0]-size, c[0]+size, c[1]-size, c[1]+size
        fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * (1-opacity) + fill * opacity
        self.cFont = ImageFont.truetype("arialbd.ttf", size)
        s = self.textSize.textsize(char, font=self.cFont)
        a = Image.new("L", (size*2, size*2), color=(0,))
        d = ImageDraw.Draw(a)
        d.text((size-s[0]/2,size-s[1]/2), char, fill=(255,), font=self.cFont)
        b = np.array(a, "uint16")
        opacity = np.expand_dims(b, 2) / 255.
        fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * (1-opacity)

    def drawText(self, fr, dText, dFill, dFont, coords, fOpacity=1, blur=2, bFill=(0,0,0)):
        """coords => offset from center (y, x)"""
        pad = 4 + blur * 14
        
        s = self.textSize.textsize(dText, font=dFont)
        a = Image.new("RGBA", (2*(s[0]//2)+pad, 2*(s[1]//2)+pad),
                      color=(*bFill,0))
        
        for ix in range(blur):
            d = ImageDraw.Draw(a)
            d.text((pad//2,pad//2), dText, fill=(*bFill,255), font=dFont)
            a = a.filter(ImageFilter.BoxBlur(6))
        
        d = ImageDraw.Draw(a)
        d.text((pad//2,pad//2), dText, fill=dFill, font=dFont)

        b = np.array(a, "uint16")
        s = b.shape
        opacity = np.expand_dims(b[:,:,3], 2) / 255. * fOpacity
        
        y1, y2 = self.H2 - (s[0]//2) + coords[0], self.H2 + (s[0]//2) + coords[0]
        x1, x2 = self.W2 - (s[1]//2) + coords[1], self.W2 + (s[1]//2) + coords[1]

        fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * (1-opacity) + \
                           b[:,:,:3] * opacity

    def imgText(self, dText, dFill, dFont, blur=4, bFill=(0,0,0)):
        pad = 4 + blur * 14
        
        s = self.textSize.textsize(dText, font=dFont)
        a = Image.new("RGBA", (2*(s[0]//2)+pad, 2*(s[1]//2)+pad),
                      color=(*bFill,0))
        for ix in range(blur):
            d = ImageDraw.Draw(a)
            d.text((pad//2,pad//2), dText, fill=(*bFill,255), font=dFont, align="center")
            a = a.filter(ImageFilter.BoxBlur(6))
        d = ImageDraw.Draw(a)
        d.text((pad//2,pad//2), dText, fill=dFill, font=dFont, align="center")
        return a
    
    def drawSelect(self, e):
        self.xyselect = np.array((e.x, e.y))
        try: self.evtQ.put_nowait(("select", (0, self.xyselect)))
        except Full: pass

    def sendSelect(self, e):
        self.xyselect = np.array((e.x, e.y))
        try: self.evtQ.put_nowait(("select", (1, self.xyselect)))
        except Full: pass
    
    def finish(self):
        if self.recVideo:
            self.VIDOUT.release()
        try:
            while not self.P.empty():
                self.P.get(True, 0.5)
        except: pass
        for t in self.threads: t.join()
        try: self.root.destroy()
        except TclError: pass
        try:
            self.evtQ.put(None, True, 1)
        except (Full, BrokenPipeError):
            pass


def writeRes(a):
    try:
        with open(PATH+"Resolutions.txt", "w") as f:
            f.write("==== Active Fullscreen Resolutions ====\n")
            f.write("AXI Combat can render at any resolution that is a multiple of 16 on both dimensions.\n")
            f.write("These are the resolutions your monitor reports that it supports.\n")
            f.write("The Active Fullscreen feature will probably work best with these.\n")
            f.write("Some monitors might stretch the output image; in this case \
you probably want to disable Active Fullscreen.\n")
            f.write(str(sorted(a.getResolutions())))
    except: pass
    
def runGUI(P, *args): 
    try:
        app = ThreeDVisualizer(P, *args)
        writeRes(app)
        app.mainloop()
        win32api.ChangeDisplaySettings(None, 0)
        time.sleep(0.2)
        app.finish()
    except Exception as e:
        logError(e, "main")
        raise
    finally:
        print("UI closed")
        if hasattr(app, "selfServe"):
            app.selfServe.terminate()

def logError(e, message):
    if __name__ == "__main__": raise e
    else:
        with open(PATH+"Error.txt", "a") as f:
            f.write("\n" + traceback.format_exc())

if __name__ == "__main__":
    runGUI(None, None, None, 640, 400)
