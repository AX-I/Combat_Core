# ======== ========
# Copyright (C) 2022 Louis Zhang
# Copyright (C) 2022 AgentX Industries
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

# HTTP routing

from http.server import *
import socket
import time, random, json
import sys

import numpy.random as nr
from urllib.parse import unquote
import socketserver
import ssl


class RoutingServer(socketserver.ThreadingMixIn,
                    HTTPServer):
    def __init__(self, https, *args):
        super().__init__(*args)
        self.games = []

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

        self.listGames()

    def do_POST(self):
        if "AXICombat" not in self.headers.get("User-Agent"):
            self.send_response(200, "Hello!")
            self.end_headers()
            return

        self.newGame()

    def newGame(self):
        n = int(self.headers.get("Content-Length"))

        raw = self.rfile.read(n).decode("utf-8")
        data = parseArg(raw)

        if 'local' not in data:
            self.send_response(200, "Hello!")
            self.end_headers()
            return

        ip = data['local'].replace('%3A', ':')
        stage = data["stage"]
        hname = data["hname"]
        self.server.games.append((ip, stage, hname, time.time()))

        print("New game")

        self.send_response(200, "Hello!")
        self.end_headers()

        s = "Ok"
        self.wfile.write(bytes(s, "utf-8"))

    def listGames(self):
        self.send_response(200, "Hello!")
        self.end_headers()

        gt = self.server.games
        for g in gt:
            if (time.time() - g[3]) < 60*5:
                self.wfile.write(bytes('+'.join(g[:-1]) + '\n', "utf-8"))


def run(addr=None):
    global httpd
    if addr is None:
        ip = ""
        try: ip = socket.gethostbyname(socket.getfqdn())
        except:
            try: ip = socket.gethostbyname(socket.gethostname())
            except: pass
        addr = (ip, 4680)
    print("Routing on", addr)
    httpd = RoutingServer(False, addr, CombatRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
