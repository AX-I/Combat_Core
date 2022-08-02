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

from tkinter import *

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

#import ImgUtils
import ImgUtilsCL as ImgUtils
from ImgUtilsCL import CLObject

import OpsConv
BLOCK_SIZE = 128

HELPTEXT = """AXI Combat v1.3
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

For more info see http://axi.x10.mx/Combat
Contact us at http://axi.x10.mx/Contact.html
"""

ABTTEXT = """AXI Combat v1.3
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
else:
    PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

SERVER = "https://axi.x10.mx/Combat/Serv.php"

if PLATFORM == "darwin":
    _TIMES = "Times New Roman.ttf"
    _TIMESBD = "Times New Roman Bold.ttf"
    _COURIERBD = "Courier New Bold.ttf"
elif PLATFORM == "linux":
    _TIMES = "LiberationSerif.ttf"
    _TIMESBD = "LiberationSerif-Bold.ttf"
    _COURIERBD = "LiberationSans-Bold.ttf"
elif "win" in PLATFORM:
    _TIMES = "times.ttf"
    _TIMESBD = "timesbd.ttf"
    _COURIERBD = "courbd.ttf"
e = ("Times", 18)
f = ("Times", 15)
g = ("Times", 12)
h = ("Courier", 10)
TO = {"timeout":1, "headers":{"User-Agent":"AXICombat/src"}}


import pyopencl as cl
mf = cl.mem_flags


class CombatMenu(Frame, ImgUtils.NPCanvas):
    def __init__(self, root=None):

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



    def openImageCover(self, fn):
        """opens filename and scales it to cover (self.W, self.H)"""
        i = Image.open(fn)
        fac = max(self.W / i.size[0], self.H / i.size[1])
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

        self.prog = cl.Program(self.ctx, open('Shaders/menu.py').read()).build()

        self.menuInit()

        self.menuLoop()


    def menuInit(self):
        self.W = np.int32(self.W)
        self.H = np.int32(self.H)

        self.tFont = ImageFont.truetype(_TIMESBD, int(72 * (self.H / 600)))
        self.bFont = ImageFont.truetype(_TIMESBD, int(48 * (self.H / 600)))
        self.cFont = ImageFont.truetype(_TIMES, int(24 * (self.H / 600)))
        self.eFont = ImageFont.truetype(_COURIERBD, int(18 * (self.H / 600)))

        i = self.openImageCover('../Assets/Forest.png')
        #i = self.openImageCover('../Assets/MenuTemple2a.png')

        i = i.filter(ImageFilter.BoxBlur(8))
        self.bg = np.array(i)
        self.bg = (self.bg / 255.)*self.bg

        self.bg = self.makeCL('Bg', self.bg)

        n = self.openImageCover('../Assets/Noise/Test5w.png')
        n = n.rotate(-90)
        nm = np.expand_dims(np.array(n), -1)
        nm = nm / 255.
        nm *= nm * 255.
        diff = n.size[1] - self.H
        nm = nm[diff//2:-diff//2]

##        self.nmask = np.clip(nm * 3, None, 1)
##        self.nmask2 = np.clip(nm * 3 - 1, 0, None) * 80.
##        self.nmask2 *= 1/np.max(self.nmask2)
        self.bgNoise = self.makeCL('BgNoise', nm)


        d = Image.open('../Assets/Noise/Test4.png')
        d = d.resize((self.H*4//5,self.H*4//5), Image.BILINEAR).convert('RGB')
        d = np.array(d) * 1.2
        d = d / 255. * d
        self.circle = d * (np.array([[[1, 0.74, 0.43]]])**2)
        self.circle = np.minimum(self.circle, 255)

        self.circle = self.makeCL('Circle', self.circle)


        self.cursor = np.array(Image.open('../Assets/Cursor.png'), 'float32')
        self.cursor[:,:,:3] = self.cursor[:,:,:3] / 255. * self.cursor[:,:,:3]

        self.cursor = self.makeCL('Cursor', self.cursor)


        imgs = ['MenuButton.png',
                'MenuOrnament.png',
                'MenuLights.png',
                'MenuBulb.png',
                'MenuBulb2.png',
                'MenuEntry.png']

        for f in imgs:
            b = Image.open('../Assets/' + f)
            b = np.array(b, 'float32')
            b[:,:,:3] = b[:,:,:3] / 255. * b[:,:,:3]
            b[:,:,3] = np.clip(b[:,:,3] * 1.2, None, 255)

            b = self.makeCL(f, b)


            aName = f.split('.')[0]
            aName = aName[0].lower() + aName[1:]
            self.__setattr__(aName, b)



        f = np.ones((33, 96, 4)) * np.array([[[80,160,240,30]]])
        f[:,:,3] *= np.sin(np.arange(96).reshape((1,96)) / 96. * 3.14)**2
        self.userHL = self.makeCL('User', f)

        f = np.ones((33, 96, 4)) * np.array([[[80,240,80,30]]])
        f[:,:,3] *= np.sin(np.arange(96).reshape((1,96)) / 96. * 3.14)**2
        self.servHL = self.makeCL('User', f)

        self.st = time.time()
        self.frameNum = 0


        #self.frameBuf = np.zeros((self.H, self.W, 3), dtype='uint8')
        f = np.zeros((self.H, self.W, 3), dtype='uint8')
        self.frameBuf = cl.Buffer(self.ctx, mf.READ_WRITE, size=f.nbytes)
        self.frameHost = f


    def makeCL(self, name: str, x: np.array) -> CLObject:
        """Converts np array into CLObject"""
        x = x.astype('uint8')
        buf = cl.Buffer(self.ctx, mf.READ_ONLY, size=x.nbytes)
        cl.enqueue_copy(self.cq, buf, x)
        return CLObject(name, buf, np.array(x.shape, 'float32'))


    def blendCursor(self, frame: np.array) -> None:
        """Blends cursor image onto frame"""
        mx = max(0, min(self.W, self.d.winfo_pointerx() - self.d.winfo_rootx()))
        my = max(0, min(self.H, self.d.winfo_pointery() - self.d.winfo_rooty()))
        self.blend(frame, self.cursor, (mx + 20, my + 20), 'alpha')


    def menuLoop(self):
        if self.frameNum == 0:
            self.tgFullScreen()

        frame = self.frameBuf

        xt = time.perf_counter()

        self.blend(frame, self.bg,
                   (self.W2, self.H2), 'replace')
        self.blend(frame, self.bgNoise,
                   (self.W2, self.H2), 'hard light')
        self.blend(frame, self.circle,
                   (self.W2, self.H2), 'add')


        bBlur = 1
        offset = (self.menuButton.shape[1] + self.menuOrnament.shape[1]) // 2

        self.blend(frame, self.menuButton,
                   (self.W//4, self.H2), 'alpha')
        self.drawText(frame, 'Start', (200,230,255), self.bFont,
                      (-6,-self.W//4), blur=bBlur, bFill=(70,130,255), method='gauss')

        self.blend(frame, self.menuOrnament,
                   (self.W//4 - offset, self.H2), 'alpha')


        self.blend(frame, self.menuButton,
                   (self.W2, self.H2), 'alpha')
        self.blend(frame, self.menuLights[6:9],
                   (self.W2, self.H2 - 50), 'alpha')
        self.blend(frame, self.menuLights[6:9],
                   (self.W2, self.H2 + 48), 'alpha')
        self.drawText(frame, 'Join', (200,255,200), self.bFont,
                      (-6,0), blur=bBlur, bFill=(60,210,60), method='gauss')


        self.blend(frame, self.menuButton,
                   (self.W*3//4, self.H2), 'alpha')
        self.blend(frame, self.menuLights[3:6],
                   (self.W*3//4, self.H2 - 50), 'alpha')
        self.blend(frame, self.menuLights[3:6],
                   (self.W*3//4, self.H2 + 48), 'alpha')
        self.drawText(frame, 'Settings', (255,230,200), self.bFont,
                      (-2,self.W//4), blur=bBlur, bFill=(255,130,70), method='gauss')


        self.blend(frame, self.menuOrnament[:,::-1],
                   (self.W*3//4 + offset, self.H2), 'alpha')
        self.blend(frame, self.menuBulb,
                   (self.W*3//4 + 115, self.H2 - 3), 'alpha')


        yc = self.H*0.7+32

        self.blend(frame, self.menuButton,
                   (self.W//4, yc), 'alpha')
        self.blend(frame, self.menuLights[0:3],
                   (self.W//4, yc - 50), 'alpha')
        self.blend(frame, self.menuLights[0:3],
                   (self.W//4, yc + 48), 'alpha')
        self.blend(frame, self.menuLights[0:3],
                   (self.W//4, yc), 'alpha')
        self.drawText(frame, 'About', (255,200,200), self.cFont,
                      (yc-self.H2-3 -24,-self.W//4), blur=bBlur, bFill=(255,70,70), method='gauss')
        self.drawText(frame, 'Controls', (255,200,200), self.cFont,
                      (yc-self.H2-3 +24,-self.W//4), blur=bBlur, bFill=(255,70,70), method='gauss')
        self.blend(frame, self.menuOrnament,
                   (self.W//4 - offset, yc), 'alpha')
        self.blend(frame, self.menuBulb2,
                   (self.W//4 - 114, yc - 3), 'alpha')

        offset2 = (self.menuEntry.shape[1] - self.menuButton.shape[1])/2
        self.blend(frame, self.menuEntry,
                   (self.W2 + offset2, self.H*0.7), 'alpha')
        self.blend(frame, self.menuEntry,
                   (self.W2 + offset2, self.H*0.7+65), 'alpha')

        yc = self.H*0.7+65
        self.blend(frame, self.menuLights[6:9],
                   (self.W2, yc -23), 'alpha')
        self.blend(frame, self.menuLights[6:9],
                   (self.W2 + 144, yc -23), 'alpha')
        self.blend(frame, self.menuLights[6:9],
                   (self.W2, yc +23), 'alpha')
        self.blend(frame, self.menuLights[6:9],
                   (self.W2 + 144, yc +23), 'alpha')

        self.blend(frame, self.userHL,
                   (self.W2 + offset2 + 120*sin(time.time() - self.st), self.H*0.7), 'alpha')

        self.blend(frame, self.servHL,
                   (self.W2 + offset2 - 120*sin(time.time() - self.st), self.H*0.7+65), 'alpha')


        self.drawText(frame, 'User999', (255,255,255), self.eFont,
                      (self.H*0.2 -2, offset2), blur=0)
        self.drawText(frame, 'https://axi.x10.mx/Combat', (255,255,255), self.eFont,
                      (yc-self.H2 -2, offset2), blur=0)


        self.blendCursor(frame)
        self.drawText(frame, "AXI Combat v1.4", (255,255,255), self.tFont,
                      (-self.H//3,0), blur=3, bFill=(180,180,180), method='gauss')

        self.gamma(frame)

        cl.enqueue_copy(self.cq, self.frameHost, frame)
        frame = self.frameHost

        et = time.perf_counter() - xt
        print('Blend', et)
        xt = time.perf_counter()

        self._render(frame)

        et = time.perf_counter() - xt
        print('Push', et)

        #Image.fromarray(frame.astype('uint8')).save('MenuTest.png')
        self.after(4, self.menuLoop)

        self.frameNum += 1
        return






        self.newG = Button(self, text="Start Game", fg="#008", bg="#bdf",
                           command=self.goStart, font=f)
        self.newG.grid(row=2, column=0, sticky=N+S+E+W, ipadx=4, ipady=2)
        self.curG = Button(self, text="Join Game", fg="#008", bg="#bfd",
                           command=self.goJoin, font=f)
        self.curG.grid(row=2, column=1, sticky=N+S+E+W, ipadx=4, ipady=2)
        self.gset = Button(self, text="Settings", fg="#808", bg="#fd0",
                           command=self.gSettings, font=f)
        self.gset.grid(row=2, column=2, sticky=N+S+E+W, ipadx=4, ipady=2)

        self.ahfr = Frame(self)
        self.ahfr.grid(row=3, column=0)
        self.abt = Button(self.ahfr, text="About", fg="#080",
                           command=self.about, font=g)
        self.abt.grid(row=0, column=0, sticky=N+S, pady=(15,0))
        self.help = Button(self.ahfr, text="Controls", fg="#800",
                           command=self.gethelp, font=g)
        self.help.grid(row=0, column=1, sticky=N+S, pady=(15,0))

        self.hostname = Entry(self, font=h, width=10, highlightthickness=2,
                              bg="#f4fff4", highlightbackground="#0A0")
        self.hostname.insert(0, SERVER)
        self.hostname.grid(row=3, column=1, sticky=N+S+E+W, pady=(15,0))

        self.uname = Entry(self, font=h, width=10, highlightthickness=2,
                           bg="#f2f2ff", highlightbackground="#00D")

        a = OpsConv.getSettings(False)
        if a["Uname"] is 0:
            un = "User" + str(random.randint(0, 1000))
        else: un = a["Uname"]
        self.lSet = a

        self.uname.insert(0, un)
        self.uname.grid(row=3, column=2, sticky=N+S+E+W, pady=(15,0))

        self.extras = Button(self, text="Credits", fg="#000", bg="#ddd",
                               command=self.showExtras, font=g)
        self.extras.grid(row=4, column=0, sticky=N+S+E+W, pady=(15,0))

        self.runMod = Button(self, text="Local Mode", fg="#a2a", bg="#ddd",
                               command=self.mkRouter, font=g)
        self.runMod.grid(row=4, column=1, sticky=N+S+E+W, pady=(15,0))


    def showExtras(self):
        try: self.credInfo.destroy()
        except (AttributeError, TclError): pass
        self.credInfo = Toplevel()
        self.credInfo.title("Credits")
        try: self.credInfo.iconbitmap(PATH+"lib/Combat.ico")
        except FileNotFoundError: pass
        ct = "Win a game in each of the 4 stages\nto unlock the credits."
        Label(self.credInfo, text=ct, font=f, padx=12, pady=12).pack()



    def nextCreds(self):
        for x in self.cScreen: self.d.delete(x)
        curScreen = self.creds[self.sc]
        self.sc += 1
        self.cScreen = []
        self.cY = self.H//5
        self.bgImg = None
        self.txts = []
        for c in curScreen["Contents"]:
            if "title" in c:
                self.cScreen.append(self.d.create_text((self.W2, self.cY),
                                        text=c["title"],
                                        justify="center", anchor="n",
                                        fill="#FFF", font=("Times", int(24*self.RS))))
                self.cY += int(45*self.RS)
            elif "text" in c:
                if self.bgImg is None:
                    self.cScreen.append(self.d.create_text((self.W2, self.cY),
                                        text=c["text"],
                                        justify="center", anchor="n",
                                        fill="#FFF", font=("Times", int(16*self.RS))))
                else:
                    font = ImageFont.truetype(_TIMESBD, int(24*self.RS))
                    ti = self.imgText(c["text"], (255,255,255), font)
                    self.txts.append(ImageTk.PhotoImage(ti))
                    self.cScreen.append(self.d.create_image(self.W2, self.H*3//4, image=self.txts[-1]))
                self.cY += int((20 * (len(c["text"].split("\n")) + 1) + 25) * self.RS)
            elif "bg" in c:
                d = max(self.W, self.H * 16/9)
                a = Image.open(PATH+c["bg"]).resize((int(d), int(d*9/16)), Image.BILINEAR)
                self.bgImg = ImageTk.PhotoImage(a)
                self.cScreen.append(self.d.create_image(self.W2, self.H2, image=self.bgImg))
            elif "img" in c:
                a = Image.open(PATH+c["img"])
                a = a.resize((int(a.size[0]*self.RS), int(a.size[1]*self.RS)))
                self.sImg = ImageTk.PhotoImage(a)
                self.cScreen.append(self.d.create_image(self.W2, self.cY, anchor="n", image=self.sImg))

        if curScreen["Transition"] == "Fade":
            self.startFade()
            self.d.after(4400, self.nextCreds)
        elif curScreen["Transition"] == "Scroll":
            self.startScroll()
        elif curScreen["Transition"] == "Fade2":
            self.startFade2()

    def startFade(self):
        self.fb = ImageTk.PhotoImage(Image.new("RGBA", (self.W, self.H), (0,0,0,255)))
        self.fstart = time.time()
        self.cScreen.append(self.d.create_image(self.W2, self.H2, image=self.fb))
        self.d.after_idle(self.fade1)
    def fade1(self):
        t = 2.1
        ftrans = (time.time() - self.fstart - t)**2 * (455/(t*t)) - 200
        self.fb = ImageTk.PhotoImage(Image.new("RGBA", (self.W, self.H),
                                               (0,0,0,max(0, int(ftrans)))))
        self.d.itemconfigure(self.cScreen[-1], image=self.fb)
        if ftrans < 256: self.d.after(20, self.fade1)
    def startFade2(self):
        self.fb = ImageTk.PhotoImage(Image.new("RGBA", (self.W, self.H), (0,0,0,255)))
        self.fstart = time.time()
        self.cScreen.append(self.d.create_image(self.W2, self.H2, image=self.fb))
        self.d.after_idle(self.fade2)
    def fade2(self):
        t = 1.8
        ftrans = (time.time() - self.fstart - t)**2 * (300/(t*t)) - 50
        self.fb = ImageTk.PhotoImage(Image.new("RGBA", (self.W, self.H), (0,0,0,max(0, int(ftrans)))))
        self.d.itemconfigure(self.cScreen[-1], image=self.fb)
        if time.time() - self.fstart - t < 0: self.d.after(20, self.fade2)

    def startScroll(self):
        self.fstart = time.time()
        for x in self.cScreen:
            c = self.d.coords(x)
            self.d.coords(x, (c[0], c[1] + self.H * 9/10))
        self.d.after_idle(self.scroll1)

    def scroll1(self):
        fy = time.time() - self.fstart
        for x in self.cScreen:
            c = self.d.coords(x)
            self.d.coords(x, (c[0], c[1] - (self.H/9.6)*fy))

        self.fstart = time.time()
        m = max([self.d.coords(x)[1] for x in self.cScreen])
        if m > -(self.H/6):
            self.d.after(20, self.scroll1)
        else:
            self.nextCreds()

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
            self.jg['bg'] = '#fcc'
            self.root.after(300, self.tgJV)

        self.hostname["bg"] = "#fcc"
        self.sh = True
        self.root.after(200, self.tgSV)
        self.root.after(400, self.tgSV)
        self.root.after(600, self.tgSV)
    def tgSV(self):
        hb = "#f4fff4" if self.sh else "#fcc"
        self.hostname["bg"] = hb
        self.sh = not self.sh
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
        self.activeFS = p["AutoRes"]
        OpsConv.writeSettings(p)

        self.logo.grid_remove()
        self.newG.grid_remove()
        self.curG.grid_remove()
        self.uname.grid_remove()
        self.hostname.grid_remove()
        self.ahfr.grid_remove()
        self.gset.grid_remove()
        self.extras.grid_remove()
        self.runMod.grid_remove()
        self.mkServer.grid_remove()

        return True

    def charMenu(self):
        self.title["text"] = "Select character"
        self.back.grid_remove()

        gd = self.gameConfig[1]

        if self.gameConfig[-1]:
            self.jg.grid_remove()
            self.avls.grid_remove()
        else:
            self.gameList = {gd:[]}
            for x in self.stb: x.grid_remove()
            for x in self.stp: x[0].grid_remove()

        self.charNames = ["Samus", "Zelda BotW",   "Link BotW",
                          "Louis", "Zelda TP",     "Link TP",
                          "Ahri",  "Stormtrooper", "Vader"]

        self.stb = []
        cmds = [lambda: self.selChar(0), lambda: self.selChar(1),
                lambda: self.selChar(2), lambda: self.selChar(3),
                lambda: self.selChar(4), lambda: self.selChar(5),
                lambda: self.selChar(6), lambda: self.selChar(7),
                lambda: self.selChar(8)]

        for i in range(len(self.charNames)):
            self.stb.append(Button(self, text=self.charNames[i],
                                   fg="#008", bg="#bdf",
                                   command=cmds[i], font=g))

            self.stb[-1].grid(row=2 + i//3, column=i%3, sticky=N+S+E+W,
                              ipadx=6, ipady=6)

        self.columnconfigure(0, uniform="x")
        self.columnconfigure(1, uniform="x")
        self.columnconfigure(2, uniform="x")

        if not self.gameConfig[4]:
            self.addAI = Button(self, text="Add AI", bg="#f94",
                                command=self.tgAI, font=g)
            self.addAI.grid(row=5, column=0, sticky=N+S+E+W, ipadx=6, ipady=6)

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

        self.title.grid_remove()
        if not self.gameConfig[4]:
            self.addAI.grid_remove()
        for x in self.stb: x.grid_remove()
        self.configure(bg='#111')
        self.columnconfigure(0, uniform=0)
        self.columnconfigure(1, uniform=1)
        self.columnconfigure(2, uniform=2)
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

        sl = ["Desert", "Atrium", "Taiga", "New Stage", "Forest", 'Strachan']

        self.title["text"] = "Select location"

        self.stb = []
        self.stp = []
        cmds = [lambda: self.goStart(0), lambda: self.goStart(1),
                lambda: self.goStart(2), lambda: self.goStart(3),
                lambda: self.goStart(4), lambda: self.goStart(5)]
        for i in range(len(self.loc)):
            self.stb.append(Button(self, text=self.loc[i], fg="#008", bg="#bdf",
                                   command=cmds[i], font=f))
            self.stb[-1].grid(row=2+i//2*2, column=i%2, sticky=N+S+E+W, ipadx=4, ipady=2)
            img = ImageTk.PhotoImage(Image.open(PATH+"../Assets/Preview_"+sl[i]+".png"))
            self.stp.append((Label(self, image=img), img))
            self.stp[-1][0].grid(row=3+i//2*2, column=i%2, sticky=N+S+E+W)

        self.back = Button(self, text="Back",
                           command=lambda: self.goBack(0), font=g)
        self.back.grid(row=2 + (len(sl)+1)//2 * 2, column=0, sticky=E+W, ipadx=4, ipady=2)

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

        self.title["text"] = "Join Game"

        self.avls = Listbox(self, width=20, height=10, font=h)
        self.avls.bind("<<ListboxSelect>>", self.setGD)
        for d in ag:
            et = d[0] + " " * (20 - len(d[0]))
            et += "(" + d[1] + ")" + " " * (10-len(d[1]))
            et += "/ " + d[2]
            self.avls.insert(END, et)
        if len(ag) > 0:
            self.avls.config(width=0)

        self.avls.grid(row=2, column=0, rowspan=2)

        self.jg = Button(self, text="Join", fg="#008", bg="#bfd",
                         command=self.joinGame, font=f)
        self.jg.grid(row=2, column=1, sticky=E+W, ipadx=4, ipady=4)

        self.back = Button(self, text="Back",
                           command=lambda: self.goBack(1), font=g)
        self.back.grid(row=3, column=1, sticky=E+W, ipadx=4, ipady=4)

        self.columnconfigure(1, weight=1, uniform="c")

    def goBack(self, e):
        if e == 0:
            for x in self.stb: x.grid_remove()
            for x in self.stp: x[0].grid_remove()
        elif e == 1:
            self.avls.grid_remove()
            self.jg.grid_remove()

        self.title["text"] = "AXI Combat v1.3"
        self.back.grid_remove()

        self.logo.grid()
        self.newG.grid()
        self.curG.grid()
        self.uname.grid()
        self.hostname.grid()
        self.ahfr.grid()
        self.gset.grid()
        self.extras.grid()
        self.runMod.grid()
        self.mkServer.grid()




    def joinGame(self):
        stage = self.loc.index(self.gd.split("(")[1].split(")")[0])
        host = self.gd.split(' ')[0]
        if "//" not in host: host = "http://" + host
        uname = self.uname.get()

        try:
            ag = requests.get(host + "/List", **TO)
        except:
            self.notConnected('join')
            return

        gi = json.loads(ag.text)
        gi = list(gi)[-1]

        self.gameList = {gi:[]}

        self.gameConfig = (stage, gi, host, uname, True)
        self.charMenu()

    def gSettings(self):
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
                             command=self.switchBackend)
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
