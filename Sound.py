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
from math import sqrt

CHUNK = 1024

def eucLen(a):
    return sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2])

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
        self.fadeTracks = set()

        self.positionTracks = {}
        self.ptcount = 0

        self.pos = np.zeros(3, 'float')
        self.vvh = np.array([1.,0,0])

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
            batchDone = False
            num = 0
            while not batchDone:
                try: cmd = self.si.get(True, 0.01)
                except Empty: batchDone = True
                else:
                    if cmd is None:
                        running = False
                        break
                    if "Play" in cmd:
                        # Either {"Play": ('file', vol, loop)} or
                        #        {"Play": ('file', vol, loop, params)} or
                        #        {"Play": ('file', vol, params)
                        if len(cmd['Play']) < 3:
                            self.playFile(*cmd["Play"])
                        elif type(cmd['Play'][2]) is bool:
                            self.playFile(*cmd["Play"][:3])
                            if len(cmd['Play']) == 4:
                                self.positionTracks[self.ptcount] = \
                                    {'track':self.tcount,
                                     'baseVol':cmd['Play'][1],
                                     'params':cmd['Play'][3]}
                                self.ptcount += 1
                        else:
                            self.playFile(cmd["Play"][0],
                                      cmd['Play'][1] * self.sndAttn(*cmd['Play'][2]))

                    elif 'SetPos' in cmd:
                        self.pos = cmd['SetPos']['pos']
                        self.vvh = cmd['SetPos']['vvh']
                    elif "Fade" in cmd:
                        self.fade = self.rcount + cmd["Fade"]['Time']
                        self.fadeTracks = cmd['Fade']['Tracks']
                    elif "FadeTime" in cmd:
                        self.fadeTime = cmd["FadeTime"]
                    elif "Vol" in cmd:
                        if 1 in self.tracks:
                            self.tracks[1]["vol"] = np.array(cmd["Vol"])
                    elif "Cresc" in cmd:
                        self.globalVol *= cmd["Cresc"]
                    elif "Loop" in cmd:
                        for i in self.tracks:
                            if self.tracks[i]['filename'] == cmd['Loop']['Track']:
                                self.tracks[i]['loop'] = cmd['Loop']['loop']
                num += 1
                if num > 7:
                    batchDone = True

            self.output()
            self.rcount += 1

        self.stream.stop_stream()
        self.stream.close()

        while not self.si.empty():
            try: self.si.get(True, 0.1)
            except Empty: pass

    def output(self):
        frames = np.zeros((CHUNK,self.channels), "int16")

        for i in list(self.positionTracks.keys()):
            p = self.positionTracks[i]
            if p['track'] not in self.tracks:
                del self.positionTracks[i]
                continue
            self.tracks[p['track']]['vol'] *= 0.5
            self.tracks[p['track']]['vol'] += 0.5 * p['baseVol'] * self.sndAttn(*p['params'])


        for i in list(self.tracks.keys()):
            t = self.tracks[i]
            d = t["wave"].readframes(CHUNK)
            s = np.frombuffer(d, "int16").reshape((-1, self.channels))

            trackVol = self.globalVol
            if '*' not in self.fadeTracks \
               and t['filename'] not in self.fadeTracks:
                trackVol = 1
            s = s * (t["vol"] * trackVol)
            if s.shape[0] == CHUNK:
                frames += s.astype("int16")
                written = CHUNK
            else:
                frames[:s.shape[0]] += s.astype("int16")
                written = s.shape[0]
            t["frame"] += CHUNK
            if t["frame"] > t["N"]:
                if t["loop"]:
                    t["frame"] -= t['N']
                    t["wave"].rewind()
                    if written < CHUNK:
                        s = np.frombuffer(t['wave'].readframes(CHUNK-written),
                                          'int16').reshape((-1, self.channels))
                        s = s * (t["vol"] * trackVol)
                        frames[written:] += s.astype('int16')
                else:
                    del self.tracks[i]
        
        if self.fade > 0 and self.rcount > self.fade:
            self.globalVol -= (1/self.fadeTime) * CHUNK / self.rate
            if self.globalVol < 0:
                self.globalVol = 1
                for i in list(self.tracks.keys()):
                    if '*' in self.fadeTracks \
                       or self.tracks[i]['filename'] in self.fadeTracks:
                        del self.tracks[i]
                self.fade = -1
        
        self.stream.write(frames.tobytes())
        
    def playFile(self, f, volume=(0.5, 0.5), loop=False):
        a = wave.open(f, "rb")
        n = a.getnframes()
        r = a.getframerate()
        if r != self.rate: print("Non-matching framerate")

        w = a.getsampwidth()
        if w != self.width: print("Non-matching width")

        c = a.getnchannels()
        if c != self.channels: print('Non-matching channels')
        
        track = {"wave":a, "frame":0, "N":n, 'filename': f,
                 "vol":np.array(volume, "float"), "loop":loop}
        
        self.tcount += 1
        self.tracks[self.tcount] = track

    def close(self):
        self.p.terminate()

    def sndAttn(self, src, mult=5, const=1.2, doWrap=False, minDist=None):
        svec = (src - self.pos)
        dist = eucLen(svec)
        if minDist is None:
            attn = mult / (dist + const)
        else:
            attn = mult / (max(dist, minDist) + const)

        LR = (svec / dist) @ self.vvh
        left = (LR + 1) / 2
        right = -(LR - 1) / 2
        pan = np.array((left, right))
        if doWrap:
            wrap = max(0, 1 - dist / const)
            if type(doWrap) is float:
                wrap = max(wrap, doWrap)
            pan = 0.2 + 0.7 * (pan * (1-wrap) + 0.5 * wrap)
        return attn * pan

if __name__ == "__main__":
    import queue
    q = queue.Queue(8)
    q.put({"Play":["C:/AXI_Visualizer/Sound/Env_Desert.wav", (0.7, 0.7), False]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/Pickup.wav", (0.2, 0.8), True]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/FireA.wav", (0.4, 0.2), True]})
    q.put({"Play":["C:/AXI_Visualizer/Sound/FireD.wav", (0.7, 0.2), True]})
    q.put({"Fade":{'Time':150, 'Tracks':'*'}})
    a = SoundManager(q)
    a.run(2, 22050, 2)
