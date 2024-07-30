# ======== ========
# Copyright (C) 2020-2022 Louis Zhang
# Copyright (C) 2020-2022 AgentX Industries
#
# This file (Menu.py) is part of AXI Combat.
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

from tkinter import Frame, Tk, N, E, S, W
from tkinter import (
    TclError, Toplevel, Label, Text, Button, Listbox, Entry, Checkbutton,
    IntVar, Scale,
    WORD, X, Y, LEFT, BOTTOM, DISABLED, END, HORIZONTAL,
)

import os, sys

PLATFORM = sys.platform
if PLATFORM == "darwin":
    from tkmacosx import Button
    import base64, io
    #import _sysconfigdatam_darwin_darwin # for freezing

if PLATFORM == "win32":
    import win32gui
    from PIL.ImageWin import Dib, HWND

import requests
import random
import json
import time
import socket
import multiprocessing as mp
import numpy as np
from math import sin

from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter

USE_CL = True

if USE_CL:
    import ImgUtilsCL as ImgUtils
else:
    import ImgUtils

from ImgUtilsCL import CLObject
import pyopencl as cl
mf = cl.mem_flags

import OpsConv
BLOCK_SIZE = 128

HELPTEXT = """AXI Combat v1.4
======= ======= ======= =======
General Usage

Move mouse - rotate camera
Q - toggle mouse capture

ASDW - move
<space> - jump
E - toggle camera control mode
X - fire A
======= ======= ======= =======
<F1> - show/hide controls
<F2> - screenshot
<F3> - show/hide indicators
<F11> - toggle fullscreen

Indicators
## Red - Health
## Green - Energy
======= ======= ======= =======
Special Keys

Z - fire B
C - fire C
V - fire D
1234 - gesture
<Up> - zoom in
<Down> - zoom out
H - toggle SSAO
N - toggle AI navigation overlay

======= ======= ======= =======
Copyright AgentX Industries 2020-2022

For more info see https://axi.x10.mx/Combat
"""

ABTTEXT = """AXI Combat v1.4
Copyright © AgentX Industries 2020-2022
Copyright © Louis Zhang 2020-2022
https://axi.x10.mx
======= ======= ======= =======
The AXI Combat engine is licensed under the GNU General Public License v3 (GPLv3).
For full terms and conditions see
https://www.gnu.org/licenses/gpl-3.0.en.html

Music is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License\
 (CC BY-SA 4.0).
For full terms and conditions see
https://creativecommons.org/licenses/by-sa/4.0/

Character models have separate licenses.

See https://axi.x10.mx/Combat for details.
"""

if getattr(sys, "frozen", False):
    PATH = os.path.dirname(sys.executable) + "/"
    SERVER = "https://axi.x10.mx/Combat/Serv.php"
else:
    PATH = os.path.dirname(os.path.realpath(__file__)) + "/"
    SERVER = "127.0.0.1:4680"


if PLATFORM == "darwin":
    _TIMES = "Times New Roman.ttf"
    _TIMESBD = "Times New Roman Bold.ttf"
    _COURIERBD = "Courier New Bold.ttf"
elif PLATFORM == "linux":
    _TIMES = "LiberationSerif-Regular.ttf"
    _TIMESBD = "LiberationSerif-Bold.ttf"
    _COURIERBD = "LiberationSans-Bold.ttf"
elif PLATFORM == "win32":
    _TIMES = "times.ttf"
    _TIMESBD = "timesbd.ttf"
    _COURIERBD = "courbd.ttf"

e = ("Times", 18)
f = ("Times", 15)
g = ("Times", 12)
h = ("Courier", 10)
TO = {"timeout":1, "headers":{"User-Agent":"AXICombat/src"}}

MSCALE = -0.04


from MenuLayout import (
    mainMenuLayout, mainHandleMouse, mainMenuSetup,
    stageSelectLayout, stageSelectSetup, stageHandleMouse,
    joinSetup, joinLayout, joinHandleMouse,
    charLayout, charHandleMouse,
    smallScale
)

import string

from Sound import SoundManager

def playSound(si):
    a = SoundManager(si)
    a.run()

class CombatMenu(Frame, ImgUtils.NPCanvas):
    def __init__(self, root=None):
        self.profTime = time.time()

        if root is None: root = Tk()
        super().__init__(root)

        self.root = root
        self.root.title("AXI Combat")
        self.root.resizable(width=False, height=False)
        if "win" in PLATFORM:
            self.root.iconbitmap(PATH+"lib/AXI.ico")
        else:
            pass

        self.loc = ["Desert", "CB Atrium", "Taiga",
                    "New Stage", "Forest", 'Strachan']
        self.localIP = None



    def openImageCover(self, fn, blur=0):
        """opens filename and scales it to cover (self.W, self.H)"""
        i = Image.open(fn).convert('RGBA')
        fac = max(self.W / i.size[0], self.H / i.size[1])
        if blur: i = i.filter(ImageFilter.BoxBlur(blur/fac))
        i = i.resize((int(i.size[0] * fac), int(i.size[1] * fac)), Image.BILINEAR)
        return i

    def startMenu(self):
        self.grid(sticky=N+E+S+W)

        self.createCoreWidgets()

        self.finalRender = self.d.create_image((self.W/2, self.H/2))

        if PLATFORM == "win32":
            self.DC = win32gui.GetDC(0)

        self.ctx = OpsConv.getContext_CL()

        d = self.ctx.devices[0]
        print("Using", d.name)
        self.cq = cl.CommandQueue(self.ctx)

        resScale = self.H / 600
        shader = open('Shaders/menu.cl').read()
        shader = shader.replace('#define cropHeight 3.f',
                                '#define cropHeight {}f'.format(3*resScale))
        self.prog = cl.Program(self.ctx, shader).build()

        self.si = mp.Queue(64)
        self.SM = mp.Process(target=playSound, args=(self.si,), name="Sound")
        self.SM.start()
        
        kwargs = OpsConv.getSettings()
        volmFX = float(kwargs["VolumeFX"])
        self.volmFX = np.array((volmFX, volmFX))

        self.activeFS = kwargs["AutoRes"]

        self.menuInit()
        self.d.bind("<F2>", self.screenshot)
        self.d.bind("<Button-1>", self.handleClick)
        self.d.bind("<Key>", self.handleKey)
        self.d.bind("<BackSpace>", self.handleBackspace)

        self.MENUSCREEN = 'MAIN'

        self.d.focus_set()

        #self.tgFullScreen()

        print('Ready in', time.time() - self.profTime)

        self.menuLoop()

    def menuInit(self):
        self.W = np.int32(self.W)
        self.H = np.int32(self.H)

        resScale = self.H / 600

        perf = time.perf_counter()

        self.tFont = ImageFont.truetype(_TIMESBD, int(84 * resScale))
        self.aFont = ImageFont.truetype(_TIMESBD, int(64 * resScale))
        self.bFont = ImageFont.truetype(_TIMESBD, int(48 * resScale))
        self.c2Font = ImageFont.truetype(_TIMES, int(36 * resScale))
        self.cFont  = ImageFont.truetype(_TIMES, int(24 * resScale))
        self.eFont = ImageFont.truetype(_COURIERBD, int(17 * resScale * smallScale))


        n = self.openImageCover('../Assets/Noise5wa.png')
        nm = np.array(n.rotate(-90))
        a = nm[:,:,3]
        a = a * (320/256) - 64
        nm[:,:,3] = np.maximum(a, 0)
        diff = max(1, n.size[1] - self.H)
        nm = nm[diff//2:-diff//2]

        self.bgNoise = self.makeCL('BgNoise', nm)

        ci = Image.open('../Assets/Cursor.png')
        ci = ci.resize((int(ci.size[0] * resScale * 1.15 / 2),
                        int(ci.size[1] * resScale * 1.15 / 2)), Image.BILINEAR)
        self.cursor = np.array(ci, 'float32')
        self.cursor[:,:,:3] = self.cursor[:,:,:3] / 255. * self.cursor[:,:,:3]

        self.cursor = self.makeCL('Cursor', self.cursor)


        fc = smallScale
        imgs = ['MenuButton.png', fc,
                'MenuOrnament.png', fc,
                'MenuLights.png', fc,
                'MenuBulb.png', 1,
                'MenuBulb2.png', 1,
                'MenuEntry.png', fc,
                'MenuHighlight.png', fc,
                'MenuRingsW.png', fc,
                'MenuEntryHighlight.png', fc,
                'MenuFrame.png', 1,
                'MenuEntryHighlightRed.png', fc,
                'MenuOrnamentLine.png', fc,
                'MenuButtonHighlight.png', fc,
                'MenuEntryOutline.png', fc,
                'MenuTitle.png', 1,
                ]

        for i in range(len(imgs)//2):
            f = imgs[2*i]
            b = Image.open('../Assets/' + f)

            fac = imgs[2*i+1]
            sw = int(b.size[0] * resScale * fac)
            sh = int(b.size[1] * resScale * fac)

            if 'Ornament' in f:
                sw = int(78 * resScale * fac)
                sh = int(112 * resScale * fac)
            b = b.resize((sw,sh), Image.BILINEAR)
            b = np.array(b, 'float32')

            if f == 'MenuHighlight.png':
                b = b * np.array([[[1., 0.8, 0.6, 1.]]])
            if f == 'MenuEntryHighlight.png':
                b = b * 0.8 * np.array([[[1., 0.8, 0.6, 1.]]])
            if f == 'MenuEntryHighlightRed.png':
                b = b * 0.8 * np.array([[[1., 0.4, 0.3, 1.]]])
                

            b[:,:,:3] = b[:,:,:3] / 255. * b[:,:,:3]
            if f == 'MenuRingsW.png':
                b[:,:,3] = b[:,:,3] * 0.2
            else:
                b[:,:,3] = np.clip(b[:,:,3] * 1.2, None, 255)

            b = self.makeCL(f, b)


            aName = f.split('.')[0]
            aName = aName[0].lower() + aName[1:]
            self.__setattr__(aName, b)


        blueBG = [80,160,240,30]
        greenBG = [80,240,80,30]
        yellowBG = (255,130,70,30.)
        f = np.ones((int(33*resScale), 96, 4)) * np.array([[blueBG]])
        f[:,:,3] *= np.sin(np.arange(96).reshape((1,96)) / 96. * 3.14)**2
        self.entryHL = self.makeCL('User', f)


        self.st = time.time()
        self.frameNum = 0


        f = np.zeros((self.H, self.W, 3), dtype='uint16')
        if USE_CL:
            self.frameBuf = cl.Buffer(self.ctx, mf.READ_WRITE, size=f.nbytes)
        else:
            self.frameBuf = f
        self.frameHost = f

        self.buttonSelect = False



        # Username
        self.uname = Entry(self, font=h, width=10, highlightthickness=2,
                           bg="#f2f2ff", highlightbackground="#00D")

        a = OpsConv.getSettings(False)
        if a["Uname"] is 0:
            un = "User" + str(random.randint(0, 1000))
        else: un = a["Uname"]
        self.lSet = a

        self.uname.insert(0, un)

        self.unameDisplay = self.uname.get()

        # Hostname
        self.hostname = Entry(self, font=h, width=10, highlightthickness=2,
                              bg="#f4fff4", highlightbackground="#0A0")
        self.hostname.insert(0, SERVER)
        self.servDisplay = SERVER

        self.runMod = Button(self, text="Local Mode", fg="#a2a", bg="#ddd",
                             command=self.mkRouter)


        print("menuInit", time.perf_counter() - perf)

        self.parx = 0.
        self.pary = 0.
        self.parxy = np.array([0.,0.])

        mainMenuSetup(self)


    def makeCL(self, name: str, x: np.array) -> CLObject:
        """Converts np array into CLObject"""
        if not USE_CL: return x
        return CLObject(self.ctx, self.cq, name, x)


    def blendCursor(self, frame: np.array) -> None:
        """Blends cursor image onto frame"""
        mx = max(0, min(self.W, self.d.winfo_pointerx() - self.d.winfo_rootx()))
        my = max(0, min(self.H, self.d.winfo_pointery() - self.d.winfo_rooty()))
        self.blend(frame, self.cursor, (mx + 20, my + 20), 'alpha')


    def menuLoop(self):        
##        if self.frameNum == 0:
##            self.tgFullScreen()

        
        xt = time.perf_counter()

        self.mx = max(0, min(self.W, self.d.winfo_pointerx() - self.d.winfo_rootx())) - self.W2
        self.my = max(0, min(self.H, self.d.winfo_pointery() - self.d.winfo_rooty())) - self.H2
        self.parx = 0.8 * self.parx + 0.2 * self.mx*MSCALE
        self.pary = 0.8 * self.pary + 0.2 * self.my*MSCALE
        self.parxy = np.array([self.parx, self.pary])

        if self.MENUSCREEN == 'MAIN':
            mainMenuLayout(self)
        elif self.MENUSCREEN == 'STAGE':
            stageSelectLayout(self)
        elif self.MENUSCREEN == 'JOIN':
            joinLayout(self)
        elif self.MENUSCREEN == 'CHAR':
            charLayout(self)


        frame = self.frameBuf

        if USE_CL:
            self.gamma(frame)

            cl.enqueue_copy(self.cq, self.frameHost, frame)
            frame = self.frameHost
        else:
            frame = np.sqrt(frame) * 16

        et = time.perf_counter() - xt
        #print('Blend', et)
        xt = time.perf_counter()

        self._render(frame)

        et = time.perf_counter() - xt
        #print('Push', et)

        if self.MENUSCREEN != '':
            self.after(4, self.menuLoop)

            self.frameNum += 1

        return



##        self.extras = Button(self, text="Credits", fg="#000", bg="#ddd",
##                               command=self.showExtras, font=g)
##        self.extras.grid(row=4, column=0, sticky=N+S+E+W, pady=(15,0))


    def handleKey(self, e=None):
        if self.MENUSCREEN != 'MAIN':
            return

        extra = ""
        if self.textEntry == 'User':
            entry = self.uname
            display = 'unameDisplay'
        elif self.textEntry == 'Serv':
            entry = self.hostname
            display = 'servDisplay'
            extra = ":/."

        if e.char in (string.ascii_letters + string.digits + extra):
            entry.insert(999, e.char)
            self.__setattr__(display, entry.get())
        else:
            # pass
            print('Key', e.char)

    def handleBackspace(self, e=None):
        if self.MENUSCREEN == 'MAIN':

            if self.textEntry == 'User':
                entry = self.uname
                display = 'unameDisplay'
            elif self.textEntry == 'Serv':
                entry = self.hostname
                display = 'servDisplay'
            
            u = entry.get()[:-1]
            entry.delete(0,999)
            entry.insert(0,u)
            self.__setattr__(display, u)

    def handleClick(self, e=None):
        if self.MENUSCREEN == 'MAIN':
            mainHandleMouse(self, None, True)
        elif self.MENUSCREEN == 'STAGE':
            stageHandleMouse(self, None, True)
        elif self.MENUSCREEN == 'JOIN':
            joinHandleMouse(self, None, True)
        elif self.MENUSCREEN == 'CHAR':
            charHandleMouse(self, None, True)


    def showExtras(self):
        try: self.credInfo.destroy()
        except (AttributeError, TclError): pass
        self.credInfo = Toplevel()
        self.credInfo.title("Credits")
        try: self.credInfo.iconbitmap(PATH+"lib/Combat.ico")
        except FileNotFoundError: pass
        ct = "Win a game in each of the 4 stages\nto unlock the credits."
        Label(self.credInfo, text=ct, font=f, padx=12, pady=12).pack()


    def getIP(self):
        try: return socket.gethostbyname(socket.getfqdn())
        except: pass
        try: return socket.gethostbyname(socket.gethostname())
        except: return ''

    def mkServ(self, showWin=True, ip=""):
        if ip == "":
            ip = self.getIP()
        addr = (ip, 2980)

        try: self.servwin.destroy()
        except (AttributeError, TclError): pass
        if showWin:
            self.servwin = Toplevel()
            self.servwin.title("Combat Server")
            try: self.servwin.iconbitmap(PATH+"lib/Combat.ico")
            except FileNotFoundError: pass

            st = "A server is now hosting on {}:{}".format(addr[0], addr[1])
            st += "\nIt should stop when the main window is closed."
            Label(self.servwin, text=st, font=g, padx=8, pady=8).pack()

        import NetServer
        self.selfServe = mp.Process(target=NetServer.run, args=(addr,))
        self.selfServe.start()

        return addr[0] + ':' + str(addr[1])

    def mkRouter(self, mkProc=True):
        self.runMod['state'] = 'disabled'
        ip = self.getIP()
        addr = (ip, 4680)
        if mkProc:
            import NetRouting
            self.selfRoute = mp.Process(target=NetRouting.run, args=(addr,))
            self.selfRoute.start()
        self.hostname.delete(0, END)
        self.hostname.insert(0, addr[0] + ':' + str(addr[1]))

    def runGame(self, *args):
        raise NotImplementedError

    def tgUN(self):
        hb = "#f2f2ff" if self.uh else "#fcc"
        self.uname["bg"] = hb
        self.uh = not self.uh

    def notConnected(self, config=None):
        if config == 'join':
            pass
##            self.jg['bg'] = '#fcc'
##            self.root.after(300, self.tgJV)

        self.hostname["bg"] = "#fcc"
        self.sh = True
        for i in range(1,5):
            self.root.after(200*i, self.tgSV)

    def tgSV(self):
        self.notConnectedTG = 1 - self.notConnectedTG
##        hb = "#f4fff4" if self.sh else "#fcc"
##        self.hostname["bg"] = hb
##        self.sh = not self.sh
    def tgJV(self):
        self.jg['bg'] = '#bfd'

    def removeMain(self, checkUser=True):
        p = OpsConv.getSettings(False)
        p["Uname"] = self.uname.get()
        p["Uname"] = p["Uname"].replace("#", "").replace("|", "")

        host = self.hostname.get()
        if "//" not in host: host = "http://" + host

        if checkUser:
            try:
                u = requests.post(host + "/User", data={"Uname":p["Uname"]}, **TO)
                if u.status_code == 403:
                    self.uname["bg"] = "#fcc"
                    self.uh = True
                    self.root.after(200, self.tgUN)
                    self.root.after(400, self.tgUN)
                    self.root.after(600, self.tgUN)
                    return False
            except:
                self.notConnected()
                return False

        self.setWH(p["W"], p["H"])
        self.rotSensitivity = p["Mouse"] / 20000
        OpsConv.writeSettings(p)

##        self.logo.grid_remove()
##        self.newG.grid_remove()
##        self.curG.grid_remove()
##        self.uname.grid_remove()
##        self.hostname.grid_remove()
##        self.ahfr.grid_remove()
##        self.gset.grid_remove()
##        self.extras.grid_remove()
##        self.runMod.grid_remove()
##        self.mkServer.grid_remove()

        return True

    def charMenu(self):
        #self.title["text"] = "Select character"
        #self.back.grid_remove()
        self.MENUSCREEN = 'CHAR'

        gd = self.gameConfig[1]

        if self.gameConfig[-1]:
            pass
##            self.jg.grid_remove()
##            self.avls.grid_remove()
        else:
            self.gameList = {gd:[]}

        self.NSPECIAL = 1
        self.charNames = ["Autumn",
                          "Samus", "Zelda BotW",   "Link BotW",
                          "Louis", "Zelda TP",     "Link TP",
                          "Ahri",  "Stormtrooper", "Vader"]

        self.stb = []
        cmds = [lambda: self.selChar(0), lambda: self.selChar(1),
                lambda: self.selChar(2), lambda: self.selChar(3),
                lambda: self.selChar(4), lambda: self.selChar(5),
                lambda: self.selChar(6), lambda: self.selChar(7),
                lambda: self.selChar(8), lambda: self.selChar(9)]

        for i in range(len(self.charNames)):
            self.stb.append(Button(self, text=self.charNames[i],
                                   fg="#008", bg="#bdf",
                                   command=cmds[i], font=g))

##            self.stb[-1].grid(row=2 + i//3, column=i%3, sticky=N+S+E+W,
##                              ipadx=6, ipady=6)

##        self.columnconfigure(0, uniform="x")
##        self.columnconfigure(1, uniform="x")
##        self.columnconfigure(2, uniform="x")

        if not self.gameConfig[4]:
            self.addAI = Button(self, text="Add AI", bg="#f94",
                                command=self.tgAI, font=g)
##            self.addAI.grid(row=5, column=0, sticky=N+S+E+W, ipadx=6, ipady=6)

        self.aiNums = []
        self.chooseAI = False

        for i in range(len(self.charNames)):
            if str(i) in self.gameList[gd]:
                self.stb[i]["state"] = "disabled"
                self.stb[i]["bg"] = "#ddd"
                if self.gameList[gd][str(i)].startswith("CPU "):
                    self.stb[i]["bg"] = "#ec8"

    def tgAI(self):
        self.chooseAI = True
        for x in self.stb:
            x["fg"] = "#e62"
        self.addAI["command"] = self.exitAI
        self.addAI["text"] = "Cancel"
    def exitAI(self):
        self.chooseAI = False
        for x in self.stb:
            x["fg"] = "#008"
        self.addAI["command"] = self.tgAI
        self.addAI["text"] = "Add AI"

    def selChar(self, i):
        host = self.gameConfig[2]
        p = {"gd":self.gameConfig[1], "pname":self.gameConfig[3], "char":i}
        if self.chooseAI:
            p["pname"] = "CPU " + str(i)
        try:
            gd = requests.post(host + "/SelChar", data=p, **TO)
            if gd.status_code == 403:
                self.stb[i]["state"] = "disabled"
                self.stb[i]["bg"] = "#ddd"
                if gd.text == "CPU":
                    self.stb[i]["bg"] = "#ec8"
                return
        except: raise

        if self.chooseAI:
            self.aiNums.append(i)
            self.stb[i]["state"] = "disabled"
            self.stb[i]["bg"] = "#ec8"
            self.stb[i]["fg"] = "#444"
            self.exitAI()
            return

        #self.title.grid_remove()
        if not self.gameConfig[4]:
            self.addAI.grid_remove()
        for x in self.stb: x.grid_remove()
        self.configure(bg='#111')
        self.columnconfigure(0, uniform=0)
        self.columnconfigure(1, uniform=1)
        self.columnconfigure(2, uniform=2)

        self.MENUSCREEN = ''
        self.d.delete(self.finalRender)
        self.runGame(*self.gameConfig, i, self.aiNums)

    def goStart(self, stage=None):
        if stage is not None:
            host = self.hostname.get()
            if "//" not in host: host = "http://" + host
            hname = self.uname.get()

            p = {'local':self.localIP, "stage":self.loc[stage], "hname":hname}
            try:
                gd = requests.post(host, data=p, **TO)
            except:
                self.notConnected()
                return

            host = self.localIP
            if "//" not in host: host = "http://" + host

            p = {"stage":self.loc[stage], "hname":hname}
            try:
                gd = requests.get(host + "/NewGame", params=p, **TO)
            except:
                self.notConnected()
                return
            print(gd.text)
            self.gameConfig = (stage, gd.text.split(":")[1], host, hname, False)
            self.charMenu()
            return

        if not self.removeMain(): return

        if self.localIP is None:
            self.localIP = self.mkServ(False)


        self.MENUSCREEN = 'STAGE'
        stageSelectSetup(self)

    def setGD(self, e):
        try: self.gd = self.avls.get(self.avls.curselection())
        except TclError: pass

    def goJoin(self):
        if not self.removeMain(): return

        host = self.hostname.get()
        if "//" not in host: host = "http://" + host

        uname = self.uname.get()
        try:
            ag = requests.get(host, **TO)
        except:
            self.notConnected()
            return

        ag = ag.text.split('\n')[:-1]
        ag = [x.split('+') for x in ag] # IP, stage, username

        #self.title["text"] = "Join Game"
        self.MENUSCREEN = 'JOIN'

        self.avls = Listbox(self, width=20, height=10, font=h)
        self.avls.bind("<<ListboxSelect>>", self.setGD)
        for d in ag:
            stage = ' '.join(d[1:-1])
            et = d[0] + " " * (20 - len(d[0]))
            et += "(" + stage + ")" + " " * 2*(12-len(stage))
            et += "/ " + d[-1]
            self.avls.insert(END, et)

        self.columnconfigure(1, weight=1, uniform="c")

    def goBack(self, e):
        self.MENUSCREEN = 'MAIN'
        return



    def joinGame(self):
        stage = self.loc.index(self.gd.split("(")[1].split(")")[0])

        self.selectedStage = stage

        host = self.gd.split(' ')[0]
        if "//" not in host: host = "http://" + host
        uname = self.uname.get()

        try:
            ag = requests.get(host + "/List", **TO)
        except:
            self.notConnected('join')
            return

        gi = json.loads(ag.text)
        try:
            gi = list(gi)[-1]
        except IndexError:
            # Games list is stale
            self.goBack()
            return

        self.gameList = {gi:[]}

        self.gameConfig = (stage, gi, host, uname, True)
        self.charMenu()

    def gSettings(self):
        if self.fs:
            self.tgFullScreen()

        try: self.prefwin.destroy()
        except (AttributeError, TclError): pass
        self.prefwin = Toplevel()
        self.prefwin.title("Settings")
        try: self.prefwin.iconbitmap(PATH+"lib/Combat.ico")
        except FileNotFoundError: pass

        Label(self.prefwin, text="AXI Combat Settings", font=f, pady=8).pack()

        Frame(self.prefwin, height=2, bd=2, bg="#000").pack(fill=X, pady=4)

        self.applyFr = Frame(self.prefwin); self.applyFr.pack(side=BOTTOM, fill=X)

        a = OpsConv.getSettings(False)
        self.lSet = a

        b = OpsConv.genInfo(False)

        self.genFr = Frame(self.prefwin); self.genFr.pack(side=LEFT, padx=10)

        Label(self.genFr, text="Render backend:", font=g).pack(anchor=W)
        self.backFr = Frame(self.genFr); self.backFr.pack()
        self.backCL = Button(self.backFr, text="OpenCL", font=g,
                             command=self.switchBackend, state='disabled')
        self.backCL.pack(side=LEFT)
        self.backGL = Button(self.backFr, text="OpenGL", font=g,
                             command=self.switchBackend)
        self.backGL.pack(side=LEFT)

        if self.lSet["Render"] == "GL":
            self.backGL["bg"] = "#dfd"
            self.backGL["fg"] = "#040"
        else:
            self.backCL["bg"] = "#dfd"
            self.backCL["fg"] = "#040"

        Label(self.genFr, text="Render device:", font=g).pack(anchor=W)

        self.devls = Listbox(self.genFr, width=20, height=4)
        self.devls.bind("<<ListboxSelect>>", self.setCL)
        self.availdevs = {}
        for i in range(len(b[1])):
            for j in range(len(b[1][i])):
                self.availdevs[b[1][i][j]] = str(i) + ":" + str(j)
        for d in self.availdevs:
            self.devls.insert(END, d)
        cdev = sum([len(x) for x in b[1][:int(a["CL"].split(":")[0])]]) + \
               int(a["CL"].split(":")[1])
        self.devls.config(width=0)
        self.devls.activate(cdev)
        self.devls.select_set(cdev)
        self.devls.pack()

        self.rFrame = Frame(self.genFr); self.rFrame.pack()
        Label(self.rFrame, text="Resolution:", font=g).pack(side=LEFT)
        self.resW = Entry(self.rFrame, font=h, width=4)
        self.resW.insert(0, a["W"]); self.resW.pack(side=LEFT)
        Label(self.rFrame, text="x", font=g).pack(side=LEFT)
        self.resH = Entry(self.rFrame, font=h, width=4)
        self.resH.insert(0, a["H"]); self.resH.pack(side=LEFT)

        self.actFS = Checkbutton(self.genFr, font=g, text="Active Fullscreen")
        self.doAFS = IntVar(); self.actFS["variable"] = self.doAFS
        self.actFS.pack();
        if a["AutoRes"]: self.actFS.select()

        self.msFrame = Frame(self.genFr); self.msFrame.pack()
        Label(self.msFrame, text="Mouse Sensitivity:", font=g).pack(side=LEFT)
        self.mSens = Entry(self.msFrame, font=h, width=3)
        self.mSens.insert(0, a["Mouse"]); self.mSens.pack(side=LEFT)

        Label(self.genFr, font=g, anchor=W, justify=LEFT,
              text="Music Volume").pack(fill=X)
        self.vFrame = Frame(self.genFr); self.vFrame.pack(fill=X)
        self.volA = Scale(self.vFrame, from_=0, to=1, orient=HORIZONTAL,
                          resolution=0.05,
                          showvalue=0, command=self.showVol)
        self.volA.pack(side=LEFT); self.volA.set(a["Volume"])
        self.volB = Label(self.vFrame, font=h, text="Volume")
        self.volB.pack(side=LEFT); self.showVol()

        Label(self.genFr, font=g, anchor=W, justify=LEFT,
              text="Effects Volume").pack(fill=X)
        self.vFrame2 = Frame(self.genFr); self.vFrame2.pack(fill=X)
        self.volC = Scale(self.vFrame2, from_=0, to=1, orient=HORIZONTAL,
                          resolution=0.05,
                          showvalue=0, command=self.showVol2)
        self.volC.pack(side=LEFT); self.volC.set(a["VolumeFX"])
        self.volD = Label(self.vFrame2, font=h, text="Volume")
        self.volD.pack(side=LEFT); self.showVol2()

        Frame(self.prefwin, width=2, bd=2, bg="#000").pack(side=LEFT, fill=Y, padx=4)


        self.genFr2 = Frame(self.prefwin); self.genFr2.pack(side=LEFT, padx=10)

        self.fshadow = Checkbutton(self.genFr2, font=g, text="Dynamic shadows")
        self.doFSH = IntVar(); self.fshadow["variable"] = self.doFSH
        self.fshadow.pack();
        if a["FS"]: self.fshadow.select()
        self.sFrame = Frame(self.genFr2); self.sFrame.pack()
        Label(self.sFrame, text="Shadow resolution:", font=g).pack(side=LEFT)
        self.shr = Entry(self.sFrame, font=h, width=4)
        self.shr.insert(0, a["SH"]); self.shr.pack(side=LEFT)

        self.fvertl = Checkbutton(self.genFr2, font=g, text="Dynamic lighting")
        self.doFV = IntVar(); self.fvertl["variable"] = self.doFV
        self.fvertl.pack();
        if a["FV"]: self.fvertl.select()

        self.fbloom = Checkbutton(self.genFr2, font=g, text="Bloom")
        self.doBL = IntVar(); self.fbloom["variable"] = self.doBL
        self.fbloom.pack();
        if a["BL"]: self.fbloom.select()

        Label(self.genFr2, font=g, anchor=W, justify=LEFT,
              text="Screen-space Raytraced\nReflections").pack(fill=X)
        self.sFrame = Frame(self.genFr2); self.sFrame.pack(fill=X)
        self.ssrA = Scale(self.sFrame, from_=0, to=3, orient=HORIZONTAL,
                          showvalue=0, command=self.showSSR)
        self.ssrA.pack(side=LEFT); self.ssrA.set(a["SSR"])
        self.ssrB = Label(self.sFrame, font=h, text="SSR")
        self.ssrB.pack(side=LEFT); self.showSSR()

        Label(self.genFr2, font=g, anchor=W, justify=LEFT,
              text="Raytraced Volumetric Lighting").pack(fill=X)
        self.rFrame = Frame(self.genFr2); self.rFrame.pack(fill=X)
        self.rtvA = Scale(self.rFrame, from_=0, to=3, orient=HORIZONTAL,
                          showvalue=0, command=self.showRTVL)
        self.rtvA.pack(side=LEFT); self.rtvA.set(a["RTVL"])
        self.rtvB = Label(self.rFrame, font=h, text="RTV")
        self.rtvB.pack(side=LEFT); self.showRTVL()

        self.fVR = Checkbutton(self.genFr2, font=g, text="VR Mode")
        self.doVR = IntVar(); self.fVR["variable"] = self.doVR
        self.fVR.pack();
##        if a["VR"]: self.fVR.select()
        self.fVR["state"] = DISABLED


        Frame(self.applyFr, height=2, bd=2, bg="#000").pack(fill=X, pady=4)
        self.apply = Button(self.applyFr, text="Apply", font=g, padx=10)
        self.apply["bg"] = "#dff"
        self.apply["fg"] = "#00f"
        self.apply["command"] = self.applyPrefs
        self.apply.pack(pady=4)

    def showSSR(self, e=None):
        s = "Off Low Medium High".split(" ")
        self.ssrB["text"] = s[self.ssrA.get()]
    def showRTVL(self, e=None):
        s = "Off Low Medium High".split(" ")
        self.rtvB["text"] = s[self.rtvA.get()]
    def showVol(self, e=None):
        self.volB["text"] = str(self.volA.get())
        try: self.evtQ.put_nowait({"Vol":self.volA.get()})
        except: pass
    def showVol2(self, e=None):
        self.volD["text"] = str(self.volC.get())

    def setCL(self, e):
        try: self.lSet["CL"] = self.availdevs[self.devls.get(self.devls.curselection())]
        except TclError: pass

    def switchBackend(self, e=None):
        return
        for _ in range(self.devls.size()):
            self.devls.delete(0)

        a = self.lSet

        if self.lSet["Render"] == "GL":
            self.lSet["Render"] = "CL"
            b = OpsConv.genInfo_CL(False)
            active, disable = self.backCL, self.backGL
        else:
            self.lSet["Render"] = "GL"
            b = OpsConv.genInfo_GL(False)
            active, disable = self.backGL, self.backCL

        active["bg"] = "#dfd"
        active["fg"] = "#040"
        disable["bg"] = "#eee"
        disable["fg"] = "#000"

        self.availdevs = {}
        for i in range(len(b[1])):
            for j in range(len(b[1][i])):
                self.availdevs[b[1][i][j]] = str(i) + ":" + str(j)
        for d in self.availdevs:
            self.devls.insert(END, d)
        cdev = sum([len(x) for x in b[1][:int(a["CL"].split(":")[0])]]) + \
               int(a["CL"].split(":")[1])
        self.devls.activate(cdev)
        self.devls.select_set(cdev)

    def applyPrefs(self):
        import math
        p = self.lSet
        p["FS"] = self.doFSH.get()
        p["SH"] = self.shr.get()
        p["FV"] = self.doFV.get()
        p["BL"] = self.doBL.get()
        p["VR"] = self.doVR.get()
        p["W"] = 16*math.ceil(int(self.resW.get()) / 16)
        p["H"] = 16*math.ceil(int(self.resH.get()) / 16)
        p["SSR"] = self.ssrA.get()
        p["RTVL"] = self.rtvA.get()
        p["Volume"] = self.volA.get()
        p["VolumeFX"] = self.volC.get()
        p["AutoRes"] = self.doAFS.get()
        p["Mouse"] = self.mSens.get()
        OpsConv.writeSettings(p)
        self.prefwin.destroy()

    def about(self):
        if self.fs:
            self.tgFullScreen()

        try:
            self.abtwin.destroy()
        except (AttributeError, TclError):
            pass
        self.abtwin = Toplevel()
        self.abtwin.title("About")
        try:
            self.abtwin.iconbitmap(PATH+"lib/Combat.ico")
        except FileNotFoundError: pass
        disptext = ABTTEXT
        self.alabel = Text(self.abtwin, wrap=WORD, font=g, width=36, height=20)
        self.alabel.insert(1.0, disptext)
        self.alabel["state"] = DISABLED
        self.alabel.pack()

    def gethelp(self):
        try:
            self.helpwin.destroy()
        except (AttributeError, TclError):
            pass
        self.helpwin = Toplevel()
        self.helpwin.title("Help")
        try:
            self.helpwin.iconbitmap(PATH+"lib/Combat.ico")
        except FileNotFoundError: pass
        disptext = HELPTEXT
        self.hscroll = Scrollbar(self.helpwin)
        self.hscroll.pack(side=RIGHT, fill=Y)
        self.hlabel = Text(self.helpwin, wrap=WORD, font=g, width=36, height=20)
        self.hlabel.insert(1.0, disptext)
        self.hlabel["state"] = DISABLED
        self.hlabel.pack()
        self.hlabel.config(yscrollcommand=self.hscroll.set)
        self.hscroll.config(command=self.hlabel.yview)

if __name__ == "__main__":
    OpsConv.genInfo()

    f = CombatMenu()
    f.startMenu()
    f.mainloop()
