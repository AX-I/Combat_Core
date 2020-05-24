# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
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

LOGO = b'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'

HELPTEXT = """AXI Combat
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
<F5> - long exposure screenshot + DoF
<Up> - zoom in
<Down> - zoom out
======= ======= ======= =======
Copyright AgentX Industries 2020

For more info see http://axi.x10.mx/Combat
Contact us at http://axi.x10.mx/Contact.html
"""

ABTTEXT = """AXI Combat
Copyright © AgentX Industries 2020
Copyright © Louis Zhang 2020
http://axi.x10.mx
======= ======= ======= =======
The AXI Combat engine is licensed under the GNU General Public License v3 (GPLv3).
For full terms and conditions see
https://www.gnu.org/licenses/gpl-3.0.en.html

Music is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License\
 (CC BY-SA 4.0).
For full terms and conditions see
https://creativecommons.org/licenses/by-sa/4.0/

Character models have separate licenses.

See http://axi.x10.mx/Combat for details.
"""

if getattr(sys, "frozen", False):
    PATH = os.path.dirname(sys.executable) + "/"
else:
    PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

SERVER = "127.0.0.1"

_TIMESBD = "Times New Roman Bold.ttf" if PLATFORM == "darwin" else "timesbd.ttf"
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
        self.root.iconbitmap(PATH+"lib/AXI.ico")
        
        self.loc = ["Desert", "CB Atrium", "Taiga"]
        
    def startMenu(self):
        self.grid(sticky=N+E+S+W)
        
        self.title = Label(self, text="Welcome to AXI Combat !", font=e)
        self.title.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        self.logoImg = PhotoImage(data=LOGO)
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
        if state != 7:
            try: self.credInfo.destroy()
            except (AttributeError, TclError): pass
            self.credInfo = Toplevel()
            self.credInfo.title("Credits")
            try: self.credInfo.iconbitmap(PATH+"lib/AXI.ico")
            except FileNotFoundError: pass
            ct = "Win a game in each of the 3 stages\nto unlock the credits."
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
        
    def mkServ(self):
        import socket
        ip = ""
        try: ip = socket.gethostbyname(socket.getfqdn())
        except:
            try: ip = socket.gethostbyname(socket.gethostname())
            except: pass
        addr = (ip, 80)

        try: self.servwin.destroy()
        except (AttributeError, TclError): pass
        self.servwin = Toplevel()
        self.servwin.title("Combat Server")
        try: self.servwin.iconbitmap(PATH+"lib/AXI.ico")
        except FileNotFoundError: pass

        st = "A server is now hosting on " + addr[0]
        st += "\nIt should stop when the main window is closed."
        tm = "Activity Monitor" if PLATFORM == "darwin" else "Task Manager"
        st += "\nIf in doubt, refer to {}.".format(tm)
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

        for i in range(len(self.charNames)):
            if str(i) in self.gameList[gd]:
                self.stb[i]["state"] = "disabled"
                self.stb[i]["bg"] = "#ddd"

    def selChar(self, i):
        host = self.gameConfig[2]
        p = {"gd":self.gameConfig[1], "pname":self.gameConfig[3], "char":i}
        try:
            gd = requests.post(host + "/SelChar", data=p, **TO)
            if gd.status_code == 403:
                self.stb[i]["state"] = "disabled"
                self.stb[i]["bg"] = "#ddd"
                return
        except: raise
        
        self.title.grid_remove()
        for x in self.stb: x.grid_remove()
        self.columnconfigure(0, uniform=0)
        self.columnconfigure(1, uniform=1)
        self.columnconfigure(2, uniform=2)
        self.runGame(*self.gameConfig, i)

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
        sl = ["Desert", "Atrium", "Taiga"]
        
        self.title["text"] = "Select location"
        
        self.stb = []
        self.stp = []
        cmds = [lambda: self.goStart(0), lambda: self.goStart(1),
                lambda: self.goStart(2)]
        for i in range(len(self.loc)):
            self.stb.append(Button(self, text=self.loc[i], fg="#008", bg="#bdf",
                                   command=cmds[i], font=f))
            self.stb[-1].grid(row=2, column=i, sticky=N+S+E+W, ipadx=4, ipady=2)
            img = ImageTk.PhotoImage(Image.open(PATH+"../Assets/Preview_"+sl[i]+".png"))
            self.stp.append((Label(self, image=img), img))
            self.stp[-1][0].grid(row=3, column=i, sticky=N+S+E+W)

        self.back = Button(self, text="Back",
                           command=lambda: self.goBack(0), font=g)
        self.back.grid(row=4, column=0, sticky=E+W, ipadx=4, ipady=2)
        
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
        
        self.title["text"] = "AXI Combat"
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
        try: self.prefwin.iconbitmap(PATH+"lib/AXI.ico")
        except FileNotFoundError: pass
        
        Label(self.prefwin, text="AXI Combat Settings", font=f, pady=8).pack()

        a = OpsConv.getSettings(False)
        self.lSet = a

        b = OpsConv.genInfo(False)

        Label(self.prefwin, text="Render device:", font=g).pack(anchor=W)
        
        self.devls = Listbox(self.prefwin, width=20, height=4)
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

        self.rFrame = Frame(self.prefwin); self.rFrame.pack()
        Label(self.rFrame, text="Resolution:", font=g).pack(side=LEFT)
        self.resW = Entry(self.rFrame, font=h, width=4)
        self.resW.insert(0, a["W"]); self.resW.pack(side=LEFT)
        Label(self.rFrame, text="x", font=g).pack(side=LEFT)
        self.resH = Entry(self.rFrame, font=h, width=4)
        self.resH.insert(0, a["H"]); self.resH.pack(side=LEFT)

        self.fshadow = Checkbutton(self.prefwin, font=g, text="Dynamic shadows")
        self.doFSH = IntVar(); self.fshadow["variable"] = self.doFSH
        self.fshadow.pack();
        if a["FS"]: self.fshadow.select()
        self.sFrame = Frame(self.prefwin); self.sFrame.pack()
        Label(self.sFrame, text="Shadow resolution:", font=g).pack(side=LEFT)
        self.shr = Entry(self.sFrame, font=h, width=4)
        self.shr.insert(0, a["SH"]); self.shr.pack(side=LEFT)

        self.fvertl = Checkbutton(self.prefwin, font=g, text="Dynamic lighting")
        self.doFV = IntVar(); self.fvertl["variable"] = self.doFV
        self.fvertl.pack();
        if a["FV"]: self.fvertl.select()
        
        self.fbloom = Checkbutton(self.prefwin, font=g, text="Bloom")
        self.doBL = IntVar(); self.fbloom["variable"] = self.doBL
        self.fbloom.pack();
        if a["BL"]: self.fbloom.select()

        Frame(self.prefwin, height=2, bd=2, bg="#000").pack(fill=X, pady=2)
        
        Label(self.prefwin, font=g, anchor=W, justify=LEFT,
              text="Screen-space Raytraced\nReflections").pack(fill=X)
        self.sFrame = Frame(self.prefwin); self.sFrame.pack(fill=X)
        self.ssrA = Scale(self.sFrame, from_=0, to=3, orient=HORIZONTAL,
                          showvalue=0, command=self.showSSR)
        self.ssrA.pack(side=LEFT); self.ssrA.set(a["SSR"])
        self.ssrB = Label(self.sFrame, font=h, text="SSR")
        self.ssrB.pack(side=LEFT); self.showSSR()
        
        Label(self.prefwin, font=g, anchor=W, justify=LEFT,
              text="Raytraced Volumetric Lighting").pack(fill=X)
        self.rFrame = Frame(self.prefwin); self.rFrame.pack(fill=X)
        self.rtvA = Scale(self.rFrame, from_=0, to=3, orient=HORIZONTAL,
                          showvalue=0, command=self.showRTVL)
        self.rtvA.pack(side=LEFT); self.rtvA.set(a["RTVL"])
        self.rtvB = Label(self.rFrame, font=h, text="RTV")
        self.rtvB.pack(side=LEFT); self.showRTVL()
        
        Frame(self.prefwin, height=2, bd=2, bg="#000").pack(fill=X, pady=2)

        self.actFS = Checkbutton(self.prefwin, font=g, text="Active Fullscreen")
        self.doAFS = IntVar(); self.actFS["variable"] = self.doAFS
        self.actFS.pack();
        if a["AutoRes"]: self.actFS.select()
        
        self.msFrame = Frame(self.prefwin); self.msFrame.pack()
        Label(self.msFrame, text="Mouse Sensitivity:", font=g).pack(side=LEFT)
        self.mSens = Entry(self.msFrame, font=h, width=3)
        self.mSens.insert(0, a["Mouse"]); self.mSens.pack(side=LEFT)

        Label(self.prefwin, font=g, anchor=W, justify=LEFT,
              text="Audio Volume").pack(fill=X)
        self.vFrame = Frame(self.prefwin); self.vFrame.pack(fill=X)
        self.volA = Scale(self.vFrame, from_=0, to=1, orient=HORIZONTAL,
                          resolution=0.05,
                          showvalue=0, command=self.showVol)
        self.volA.pack(side=LEFT); self.volA.set(a["Volume"])
        self.volB = Label(self.vFrame, font=h, text="Volume")
        self.volB.pack(side=LEFT); self.showVol()

        self.apply = Button(self.prefwin, text="Apply", font=g)
        self.apply["bg"] = "#dff"
        self.apply["fg"] = "#00f"
        self.apply["command"] = self.applyPrefs
        self.apply.pack()

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

    def setCL(self, e):
        try: self.lSet["CL"] = self.availdevs[self.devls.get(self.devls.curselection())]
        except TclError: pass
        
    def applyPrefs(self):
        import math
        p = self.lSet
        p["FS"] = self.doFSH.get()
        p["SH"] = self.shr.get()
        p["FV"] = self.doFV.get()
        p["BL"] = self.doBL.get()
        p["W"] = 16*math.ceil(int(self.resW.get()) / 16)
        p["H"] = 16*math.ceil(int(self.resH.get()) / 16)
        p["SSR"] = self.ssrA.get()
        p["RTVL"] = self.rtvA.get()
        p["Volume"] = self.volA.get()
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
            self.abtwin.iconbitmap(PATH+"lib/AXI.ico")
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
            self.helpwin.iconbitmap(PATH+"lib/AXI.ico")
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
