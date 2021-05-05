# ======== ========
# Copyright (C) 2020-2021 Louis Zhang
# Copyright (C) 2020-2021 AgentX Industries
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
    import _sysconfigdatam_darwin_darwin # for freezing

import requests
import random
import json
import time

from PIL import Image, ImageTk, ImageFont

import OpsConv

HELPTEXT = """AXI Combat v1.2
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
Copyright AgentX Industries 2020-2021

For more info see http://axi.x10.mx/Combat
Contact us at http://axi.x10.mx/Contact.html
"""

ABTTEXT = """AXI Combat v1.2
Copyright © AgentX Industries 2020-2021
Copyright © Louis Zhang 2020-2021
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

SERVER = "127.0.0.1:2980"

if PLATFORM == "darwin":
    _TIMESBD = "Times New Roman Bold.ttf"
elif PLATFORM == "linux":
    _TIMESBD = "LiberationSerif-Bold.ttf"
elif "win" in PLATFORM:
    _TIMESBD = "timesbd.ttf"
e = ("Times", 18)
f = ("Times", 15)
g = ("Times", 12)
h = ("Courier", 10)
TO = {"timeout":1, "headers":{"User-Agent":"AXICombat/src"}}

class CombatMenu(Frame):
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

        self.loc = ["Desert", "CB Atrium", "Taiga", "New Stage"]

    def startMenu(self):
        self.grid(sticky=N+E+S+W)

        self.title = Label(self, text="Welcome to AXI Combat v1.2 !", font=e)
        self.title.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        i = Image.open(PATH+"lib/Combat.png")

        self.logoImg = ImageTk.PhotoImage(i.resize((192,170), Image.BILINEAR))
        self.logo = Label(self, image=self.logoImg)
        self.logo.grid(row=1, column=0, columnspan=3, padx=10, pady=(0,10))

        self.columnconfigure(0, weight=1, uniform="b")
        self.columnconfigure(1, weight=1, uniform="b")

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

        self.runMod = Button(self, text="Run Module", fg="#888", bg="#ddd",
                               command=lambda: 0, font=g)
        self.runMod.grid(row=4, column=1, sticky=N+S+E+W, pady=(15,0))

        self.mkServer = Button(self, text="Start Server", fg="#a2a", bg="#ddd",
                               command=self.mkServ, font=g)
        self.mkServer.grid(row=4, column=2, sticky=N+S+E+W, pady=(15,0))

    def showExtras(self):
        state = 0
        try:
            with open(PATH+"lib/Stat.txt") as sf:
                state = int(sf.read())
        except: pass
        if state != 15:
            try: self.credInfo.destroy()
            except (AttributeError, TclError): pass
            self.credInfo = Toplevel()
            self.credInfo.title("Credits")
            try: self.credInfo.iconbitmap(PATH+"lib/Combat.ico")
            except FileNotFoundError: pass
            ct = "Win a game in each of the 4 stages\nto unlock the credits."
            Label(self.credInfo, text=ct, font=f, padx=12, pady=12).pack()
            return

        self.removeMain(False)

        if self.H < 270:
            self.W = int(self.W / self.H * 270)
            self.H = 270
            self.setWH(self.W, self.H)

        self.createCoreWidgets()

        self.evtQ.put({"Fade":0, "FadeTime":0.5})

        self.creds = json.loads(open(PATH+"lib/Credits.dat").read())
        self.d.after_idle(self.startCreds)
        self.credI = 0
        self.dt1 = time.time()
        self.d.after(800, self.playCredMusic)

    def playCredMusic(self):
        volm = float(OpsConv.getSettings(False)["Volume"])
        self.evtQ.put({"Play":(PATH + "../Sound/Credits.wav", 1.66*volm, False)})
        self.d.after(20000, self.decrVol)
        self.vCount = 0

    def decrVol(self):
        self.evtQ.put({"Cresc":0.98})
        self.vCount += 1
        if self.vCount < 25:
            self.d.after(500, self.decrVol)

    def startCreds(self):
        self.RS = self.H/440
        self.sc = 0
        self.cScreen = []
        self.d.after(10, self.nextCreds)

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

    def mkServ(self, showWin=True, ip=""):
        import socket
        if ip == "":
            try: ip = socket.gethostbyname(socket.getfqdn())
            except:
                try: ip = socket.gethostbyname(socket.gethostname())
                except: pass
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
        import multiprocessing as mp
        self.selfServe = mp.Process(target=NetServer.run, args=(addr,))
        self.selfServe.start()

    def runGame(self, *args):
        raise NotImplementedError

    def tgUN(self):
        hb = "#f2f2ff" if self.uh else "#fcc"
        self.uname["bg"] = hb
        self.uh = not self.uh

    def notConnected(self):
        self.hostname["bg"] = "#fcc"
        self.sh = True
        self.root.after(200, self.tgSV)
        self.root.after(400, self.tgSV)
        self.root.after(600, self.tgSV)
    def tgSV(self):
        hb = "#f4fff4" if self.sh else "#fcc"
        self.hostname["bg"] = hb
        self.sh = not self.sh

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
        for x in self.stb: x.grid_remove()
        self.columnconfigure(0, uniform=0)
        self.columnconfigure(1, uniform=1)
        self.columnconfigure(2, uniform=2)
        self.runGame(*self.gameConfig, i, self.aiNums)

    def goStart(self, stage=None):
        if stage is not None:
            host = self.hostname.get()
            if "//" not in host: host = "http://" + host

            hname = self.uname.get()
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
        sl = ["Desert", "Atrium", "Taiga", "New Stage"]

        self.title["text"] = "Select location"

        self.stb = []
        self.stp = []
        cmds = [lambda: self.goStart(0), lambda: self.goStart(1),
                lambda: self.goStart(2), lambda: self.goStart(3)]
        for i in range(len(self.loc)):
            self.stb.append(Button(self, text=self.loc[i], fg="#008", bg="#bdf",
                                   command=cmds[i], font=f))
            self.stb[-1].grid(row=2+i//2*2, column=i%2, sticky=N+S+E+W, ipadx=4, ipady=2)
            img = ImageTk.PhotoImage(Image.open(PATH+"../Assets/Preview_"+sl[i]+".png"))
            self.stp.append((Label(self, image=img), img))
            self.stp[-1][0].grid(row=3+i//2*2, column=i%2, sticky=N+S+E+W)

        self.back = Button(self, text="Back",
                           command=lambda: self.goBack(0), font=g)
        self.back.grid(row=6, column=0, sticky=E+W, ipadx=4, ipady=2)

    def setGD(self, e):
        try: self.gd = self.avls.get(self.avls.curselection())
        except TclError: pass

    def goJoin(self):
        if not self.removeMain(): return

        host = self.hostname.get()
        if "//" not in host: host = "http://" + host

        uname = self.uname.get()
        try:
            ag = requests.get(host + "/List", **TO)
        except:
            self.notConnected()
            return
        ag = json.loads(ag.text.replace("+", " "))
        self.gameList = ag

        self.title["text"] = "Join Game"

        self.avls = Listbox(self, width=20, height=10, font=h)
        self.avls.bind("<<ListboxSelect>>", self.setGD)
        for d in ag:
            et = d + " " * (20 - len(d))
            et += "(" + ag[d]["Stage"] + ")" + " " * (10-len(ag[d]["Stage"]))
            et += "/ " + ag[d]["Host"]
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

        self.title["text"] = "AXI Combat v1.2"
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

    def scramble(self, t):
        a = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
        return "".join([a[(a.index(x)+17) % len(a)] for x in t])
    def descramble(self, t):
        a = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
        return "".join([a[(a.index(x)-17) % len(a)] for x in t])

    def joinGame(self):
        gi = " ".join(self.gd.split(" ")[:2])
        stage = self.loc.index(self.gd.split("(")[1].split(")")[0])
        host = self.hostname.get()
        if "//" not in host: host = "http://" + host
        uname = self.uname.get()

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
