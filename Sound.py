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
import pyogg
import threading, queue

import time
from queue import Empty
from math import sqrt

CHUNK = 1024

def eucLen(a):
    return sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2])

def readAudio(f):
    if f.endswith('.flac'):
        vf = pyogg.FlacFile(f)
    if f.endswith('.ogg'):
        vf = pyogg.VorbisFile(f)
    if f.endswith('.wav'):
        w = wave.open(f, "rb")
        assert w.getframerate() == 22050
        vf = np.frombuffer(w.readframes(w.getnframes()), 'int16')
        vf = vf.reshape((-1, w.getnchannels()))
        return vf

    if vf.frequency == 44100:
        return np.ascontiguousarray(vf.as_array()[::2])
    elif vf.frequency == 22050:
        return vf.as_array()

    print('Only support 22.05kHz and 44.1kHz .ogg and .flac files')


def readAudioThread(f, q):
    q.put((f, readAudio(f)))


class arrayWave:
    def __init__(self, ar):
        """Wave interface for array"""
        self.ar = ar
        self.frame = 0
    def getnframes(self):
        return self.ar.shape[0]
    def readframes(self, n, chdelay=(0,0)):
        cL = self.ar[self.frame+chdelay[1]:self.frame+chdelay[1]+n,0]
        cR = self.ar[self.frame+chdelay[0]:self.frame+chdelay[0]+n,1]
        ms = min(cL.shape[0], cR.shape[0])
        out = np.stack((cL[:ms],cR[:ms]), -1)
        self.frame += n
        return out
    def rewind(self):
        self.frame = 0

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

        self.preloadTracks = {}
        self.preloadThreads = set()
        self.preloadQ = queue.Queue(16)

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
                if len(self.preloadThreads) > 0:
                    try: p = self.preloadQ.get_nowait()
                    except Empty: pass
                    else:
                        self.preloadTracks[p[0]] = p[1]
                        #print('Recieved preload', p[0])
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
                        elif type(cmd['Play'][2]) is dict:
                            self.playFile(cmd['Play'][0], cmd['Play'][1],
                                          **cmd['Play'][2])
                        else:
                            attn, chdelay = self.sndAttn(*cmd['Play'][2], usechdelay=True)
                            self.playFile(cmd["Play"][0],
                                          cmd['Play'][1] * attn,
                                          chdelay=chdelay)

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
                    elif "Preload" in cmd:
                        for f in cmd['Preload']:
                            self.preloadFile(f)
                num += 1
                if num > 7:
                    batchDone = True

            self.output()
            self.rcount += 1

        self.stream.stop_stream()
        self.stream.close()

        for t in self.preloadThreads:
            t.join()

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
            attn, chdelay = self.sndAttn(*p['params'], usechdelay=True)
            t = self.tracks[p['track']]
            t['vol'] *= 0.5
            t['vol'] += 0.5 * p['baseVol'] * attn
            tc = t['chdelay']
            t['chdelay'] = (int((tc[0] + chdelay[0])*0.5),
                            int((tc[1] + chdelay[1])*0.5))


        for i in list(self.tracks.keys()):
            t = self.tracks[i]
            d = t["wave"].readframes(CHUNK, chdelay=t['chdelay'])
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
                        s = t['wave'].readframes(CHUNK-written, chdelay=t['chdelay'])
                        s = np.frombuffer(s, 'int16').reshape((-1, self.channels))
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
        
    def playFile(self, f, volume=(0.5, 0.5), loop=False, chdelay=(0,0)):
        if f in self.preloadTracks:
            a = arrayWave(self.preloadTracks[f])
        else:
            a = arrayWave(readAudio(f))

        n = a.getnframes()

        track = {"wave":a, "frame":0, "N":n, 'filename': f,
                 "vol":np.array(volume, "float"), "loop":loop,
                 'chdelay':chdelay}
        
        self.tcount += 1
        self.tracks[self.tcount] = track

    def preloadFile(self, f):
        if f in self.preloadTracks:
            print('Already preloaded')
            return

        t = threading.Thread(target=readAudioThread,
                             args=(f, self.preloadQ))
        t.start()
        self.preloadThreads.add(t)

    def close(self):
        self.p.terminate()

    def sndAttn(self, src, mult=5, const=1.2, doWrap=0.2,
                minDist=None, maxDist=None,
                usechdelay=False):
        svec = (src - self.pos)
        dist = eucLen(svec)
        if minDist is None:
            attn = mult / (dist + const)
        else:
            attn = mult / (max(dist, minDist) + const)

        if maxDist is not None:
            attn *= max(0, min(1, (2 - dist/maxDist)))

        LR = (svec / dist) @ self.vvh
        left = (LR + 1) / 2
        right = -(LR - 1) / 2
        pan = np.array((left, right))
        if doWrap:
            wrap = max(0, 1 - dist / const)
            if type(doWrap) is float:
                wrap = max(wrap, doWrap)
            pan = 0.2 + 0.7 * (pan * (1-wrap) + 0.5 * wrap)

        if usechdelay:
            return attn * pan, (max(0,int(-LR * 22)), max(0,int(LR * 22)))

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
