# ======== ========
# Copyright (C) 2020 Louis Zhang
# Copyright (C) 2020 AgentX Industries
#
# This file (Sound.py) is part of AXI Combat.
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

# Sound manager
# PyAudio

import numpy as np
import pyaudio
import wave
import time
from queue import Empty

CHUNK = 2048

class SoundManager:
    def __init__(self, si):
        self.si = si
        self.p = pyaudio.PyAudio()
        print("Output device:", self.p.get_default_output_device_info()["name"])
        self.tracks = {}
        self.tcount = 0
        self.fade = -1
        self.globalVol = 1
        self.fadeTime = 2
    
    def run(self, w=2, r=22050, n=2):
        """w = 2 for int16"""
        self.channels = n
        self.rate = r
        self.width = w
        self.stream = self.p.open(format=self.p.get_format_from_width(w),
                             channels=n, rate=r,
                             output=True)
        
        running = True
        self.rcount = 0
        while running:
            try: cmd = self.si.get(True, 0.02)
            except Empty: pass
            else:
                if cmd is None:
                    running = False
                    break
                if "Play" in cmd:
                    self.playFile(*cmd["Play"])
                if "Fade" in cmd:
                    self.fade = self.rcount + cmd["Fade"]
                if "FadeTime" in cmd:
                    self.fadeTime = cmd["FadeTime"]
                if "Vol" in cmd:
                    if 1 in self.tracks:
                        self.tracks[1]["vol"] = np.array(cmd["Vol"])
                if "Cresc" in cmd:
                    self.globalVol *= cmd["Cresc"]

            self.output()
            self.rcount += 1

        self.stream.stop_stream()
        self.stream.close()

        while not self.si.empty():
            try: self.si.get(True, 0.1)
            except Empty: pass

    def output(self):
        frames = np.zeros((CHUNK,self.channels), "int16")
        
        for i in list(self.tracks.keys()):
            t = self.tracks[i]
            d = t["wave"].readframes(CHUNK)
            s = np.frombuffer(d, "int16").reshape((-1, self.channels))
            s = s * (t["vol"] * self.globalVol)
            if s.shape[0] == CHUNK:
                frames += s.astype("int16")
            else:
                frames[:s.shape[0]] += s.astype("int16")
            t["frame"] += CHUNK
            if t["frame"] > t["N"]:
                if t["loop"]:
                    t["frame"] = 0
                    t["wave"].rewind()
                else:
                    del self.tracks[i]
        
        if self.fade > 0 and self.rcount > self.fade:
            self.globalVol -= (1/self.fadeTime) * CHUNK / self.rate
            if self.globalVol < 0:
                self.globalVol = 1
                for i in list(self.tracks.keys()): del self.tracks[i]
                self.fade = -1
        
        self.stream.write(frames.tobytes())
        
    def playFile(self, f, volume=(0.5, 0.5), loop=False):
        a = wave.open(f, "rb")
        n = a.getnframes()
        r = a.getframerate()
        if r != self.rate: print("Non-matching framerate")

        w = a.getsampwidth()
        if w != self.width: raise ValueError("Non-matching width")
        
        track = {"wave":a, "frame":0, "N":n,
                 "vol":np.array(volume, "float"), "loop":loop}
        
        self.tcount += 1
        self.tracks[self.tcount] = track

    def close(self):
        self.p.terminate()

if __name__ == "__main__":
    import queue
    q = queue.Queue(8)
    q.put({"Play":["C:/AXI_Visualizer/Sound/Env_Desert.wav", (0.7, 0.7)]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/Pickup.wav", (0.2, 0.8), True]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/FireA.wav", (0.4, 0.2), True]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/FireD.wav", (0.7, 0.2), True]})
    q.put({"Fade":150})
    a = SoundManager(q)
    a.run(2, 22050, 2)
