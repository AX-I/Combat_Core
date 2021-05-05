# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
#
# This file (NetServer.py) is part of AXI Combat.
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

# HTTP host

from http.server import *
import socket
import time, random, json
import sys

import numpy.random as nr
from urllib.parse import unquote
import socketserver
import ssl

gRand1 = "Red Turquoise Stanford Northern Swift Joyful Golden Dreamy Musical".split(" ")
gRand2 = "Bunny Wolf Laser Tree Fox Link Cactus Violin Tornado Orchid".split(" ")
gRandX = nr.permutation(len(gRand1) * len(gRand2))
gCount = 0

class CombatServer(socketserver.ThreadingMixIn,
                   HTTPServer):
    def __init__(self, https, *args):
        super().__init__(*args)
        self.users = {}
        self.games = {}
        self.gamePlayers = {}

        if https:
            self.socket = ssl.wrap_socket(self.socket,
                                          keyfile="combatlocal.pem",
                                          certfile="server.pem",
                                          server_side=True)

def parseArg(s):
    data = {}
    for i in s.split("&"):
        data[i.split("=")[0]] = i.split("=")[1]
    return data

class CombatRequestHandler(BaseHTTPRequestHandler):
    version_string = lambda x: "AXICombatServer/1.0"

    def send_response(self, code, message=None):
        self.send_response_only(code, message)
        self.send_header('Server', self.version_string())

    def do_GET(self):
        if "AXICombat" not in self.headers.get("User-Agent"):
            self.send_response(200, "Hello!")
            self.end_headers()
            return

        if "NewGame" in self.path:
            self.newGame()
        elif "List" in self.path:
            self.listGames()

    def do_POST(self):
        if "AXICombat" not in self.headers.get("User-Agent"):
            self.send_response(200, "Hello!")
            self.end_headers()
            return

        if "GameDat" in self.path:
            self.updateGame()
        elif "SelChar" in self.path:
            self.updateChar()
        elif "User" in self.path:
            self.checkUser()

    def checkUser(self):
        n = int(self.headers.get("Content-Length"))

        raw = self.rfile.read(n).decode("utf-8")
        data = parseArg(raw)
        un = data["Uname"].replace("+", " ")
        try:
            if un.startswith("CPU"):
                self.send_response(403, "Username taken")
                self.end_headers()
                return
        except: pass

        if un in self.server.users:
            if self.client_address[0] != self.server.users[un]:
                self.send_response(403, "Username taken")
                self.end_headers()
        else:
            self.server.users[un] = self.client_address[0]

        self.send_response(200, "Hello!")
        self.end_headers()


    def newGame(self):
        global gRand1, gRand2, gRandX, gCount

        data = parseArg(self.path.split("?")[1])
        stage = data["stage"]
        hname = data["hname"]

        r = gRandX[gCount % len(gRandX)]
        reqId = gRand1[r // len(gRand2)] + " " + gRand2[r % len(gRand2)]
        gCount += 1

        self.server.games[reqId] = {"Stage":stage, "Host":hname, "Time":time.time()}
        self.server.gamePlayers[reqId] = {}
        print("New game:", reqId)

        self.send_response(200, "Hello!")
        self.end_headers()

        s = "New:" + str(reqId)

        self.wfile.write(bytes(s, "utf-8"))

    def listGames(self):
        self.send_response(200, "Hello!")
        self.end_headers()

        gt = list(self.server.games)
        for g in gt:
            if (time.time() - self.server.games[g]["Time"]) > 60*5:
                print("Deleted:", g)
                del self.server.games[g]
                del self.server.gamePlayers[g]

        s = json.dumps(self.server.games)

        self.wfile.write(bytes(s, "utf-8"))

    def updateChar(self):
        n = int(self.headers.get("Content-Length"))
        raw = self.rfile.read(n).decode("utf-8")
        data = parseArg(raw)

        if not all([x in data for x in ("gd", "pname")]):
            self.send_response(400, "Missing parameters")
            self.end_headers()
            self.wfile.write(b"Missing parameters.")
            return

        gd = data["gd"].replace("+", " ")

        if "char" in data:
            if data["char"] in self.server.games[gd]:
                self.send_response(403, "Taken")
                self.end_headers()
                if self.server.games[gd][data["char"]].startswith("CPU "):
                    self.wfile.write(b"CPU")
                return

            self.server.games[gd][data["char"]] = data["pname"]

        self.send_response(200, "Hello!")
        self.end_headers()

    def updateGame(self):
        n = int(self.headers.get("Content-Length"))
        raw = self.rfile.read(n).decode("utf-8")
        data = parseArg(raw)

        if not all([x in data for x in ("gd", "pname")]):
            self.send_response(400, "Missing parameters")
            self.end_headers()
            self.wfile.write(b"Missing parameters.")
            return

        gd = data["gd"].replace("+", " ")

        cgame = self.server.gamePlayers[gd]
        if data["pname"] not in cgame:
            cgame[data["pname"]] = {"addr":self.client_address[0], "data":""}
        elif cgame[data["pname"]]["addr"] != self.client_address[0]:
            self.send_response(200, "Hello!")
            self.end_headers()
            return

        if "data" in data:
            self.server.games[gd]["Time"] = time.time()
            cgame[data["pname"]]["data"] = data["data"]

        self.send_response(200, "Hello!")
        self.end_headers()

        out = ""
        if "getAll" in data:
            for i in cgame:
                if i != self.server.games[gd]["Host"]:
                    out += i + "|" + cgame[i]["data"] + "#"

            self.wfile.write(bytes(out, "utf-8"))
            return

        hname = self.server.games[gd]["Host"]
        out = hname + "|" + self.server.gamePlayers[gd][hname]["data"]

        self.wfile.write(bytes(out, "utf-8"))

def run(addr=None):
    global httpd
    if addr is None:
        ip = ""
        try: ip = socket.gethostbyname(socket.getfqdn())
        except:
            try: ip = socket.gethostbyname(socket.gethostname())
            except: pass
        addr = (ip, 80)
    print("Hosting on", addr)
    httpd = CombatServer(False, addr, CombatRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
