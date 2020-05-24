# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
#
# This file (Network.py) is part of AXI Combat.
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

# HTTP client

import requests
from requests.exceptions import Timeout, ReadTimeout, ConnectionError
import threading
import time
import random
import json
from queue import Empty, Full
from urllib.parse import unquote
import os, sys

if getattr(sys, "frozen", False): PATH = os.path.dirname(sys.executable) + "/"
else: PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

class TCPServer:
    def __init__(self, pi, po, isclient, name, host="http://127.0.0.1",
                 stage="", gameId=None):
        
        self.HOST = host
        
        self.pi = pi
        self.po = po

        self.isclient = isclient

        self.TO = {"timeout":0.2, "headers":{"User-Agent":"AXICombat/src"}}
        self.maxFPS = 15
        
        if isclient:
            a = requests.get(host + "/List", **self.TO)
            if gameId in json.loads(a.text):
                print("Connected to server")
            else:
                raise KeyError("Game ID not found!")

        self.gameId = gameId
        self.name = name

    def processData(self, data):
        d = unquote(data.text).replace("+", " ").split("#")
        for x in d:
            if len(x) == 0: continue
            try: self.po.put((x.split("|")[0], x.split("|")[1]), True, 0.1)
            except Full: pass
            except:
                print(x, d)
                raise
        
    def run(self):
        ready = False
        while not ready:
            try:
                ready = self.pi.get(True, 0.2)
            except Empty: pass
                
        running = True
        
        while running:
            self.startTime = time.time()
            
            p = {"gd":self.gameId, "pname":self.name}
            try:
                p["data"] = self.pi.get(True, 0.1)
                if p["data"] is None: running = False
            except Empty: pass

            try:
                if self.isclient:
                    data = requests.post(self.HOST + "/GameDat", data=p, **self.TO)
                else:
                    p["getAll"] = 1
                    data = requests.post(self.HOST + "/GameDat", data=p, **self.TO)
                self.processData(data)
            except (Timeout, ReadTimeout, ConnectionError): pass

            dt = time.time() - self.startTime
            if dt < (1/self.maxFPS):
                time.sleep((1/self.maxFPS) - dt)
        
        while not self.pi.empty():
            try: self.pi.get(True, 0.2)
            except: pass
        
