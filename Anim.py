import json
import numpy as np

def loadAnim(fn, timeScale=1):
    keyFrames = []
    co = [0,0,0]
    with open(fn) as f:
        for line in f:
            if line[:2] == "T ":
                ct = float(line[2:-1]) * timeScale
            elif line[:2] == 'P ':
                co = json.loads(line[2:-1])
            elif line[:2] == "A ":
                cp = json.loads(line[2:-1])
                keyFrames.append((ct, cp, np.array(co, 'float')))
                co = [0,0,0]
    return keyFrames


class AnimManager:
    def stepPoseLoop(self, p, vobj, st=1):
        p['poset'] += p['pstep'] * st
        if p['poset'] > self.keyFrames[-1][0]:
            p['poset'] -= self.keyFrames[-1][0] - self.keyFrames[0][0]
        if p['poset'] < self.keyFrames[0][0]:
            p['poset'] += self.keyFrames[-1][0] - self.keyFrames[0][0]

        if len(self.keyFrames) < 2: return
        k = None
        for i in range(len(self.keyFrames)):
            if p['poset'] < self.keyFrames[i][0]:
                k = max(0, min(len(self.keyFrames)-2, i-1))
                r = p['poset'] - self.keyFrames[k][0]
                r /= self.keyFrames[k+1][0] - self.keyFrames[k][0]
                break
        if k is not None:
            sign = 1 if st > 0 else -1

            try: _ = p['b1'].lastOffset
            except: p['b1'].lastOffset = np.array((0,0,0), 'float32')

            off = (self.keyFrames[k][2] @ p['b1'].rotMat) * (1-r)
            off += (self.keyFrames[k+1][2] @ p['b1'].rotMat) * r

            if p['jump'] < 0:
                p['b1'].offset[:3] += off - p['b1'].lastOffset
                p['b1'].lastOffset = off
                p['animOffset'] = off

            ang = p['b1'].angles
            ang += np.array(self.keyFrames[k][1]['angle'], 'float32') * (1-r) * sign
            ang += np.array(self.keyFrames[k+1][1]['angle'], 'float32') * r * sign
            p['b1'].rotate(ang)

            p["rig"].interpPose(self.keyFrames[k][1], self.keyFrames[k+1][1], r)
