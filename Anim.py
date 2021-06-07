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

def cubicInterp(t: float, *args):
    """Takes target x and four (x, y) coords"""
    y = np.array([[a[1] for a in args]], 'float32').T
    M = np.array([[a[0]**i for i in range(3,-1,-1)] for a in args], 'float32')
    curve = np.linalg.inv(M) @ y
    sol = np.array([t**i for i in range(3,-1,-1)]) @ curve
    return sol[0]

def cubicInterpLoop(kf, k, p):
    """kf: keyframes (time, pose, offset), k: current keyframe, p: player"""
    k_prev = k-1 if k > 0 else k-2
    k_next = k+2 if k < len(kf)-2 else (k+3)%len(kf)
    kfn = (kf[k_prev], kf[k], kf[k+1], kf[k_next])

    yc0 = [(x[2] @ p['b1'].rotMat)[0] for x in kfn]
    yc1 = [(x[2] @ p['b1'].rotMat)[1] for x in kfn]
    yc2 = [(x[2] @ p['b1'].rotMat)[2] for x in kfn]
    xc = [x[0] for x in kfn]
    for i in range(len(xc) - 1):
        if xc[i] > xc[i+1]:
            if k > 0:
                xc[i+1] += kf[-1][0] - kf[0][0]
            else:
                xc[i] -= kf[-1][0] - kf[0][0]
    off = np.array([cubicInterp(p['poset'], *zip(xc, yc0)),
                    cubicInterp(p['poset'], *zip(xc, yc1)),
                    cubicInterp(p['poset'], *zip(xc, yc2))])
    return off


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

            # Linear interp
            # off = (self.keyFrames[k][2] @ p['b1'].rotMat) * (1-r)
            # off += (self.keyFrames[k+1][2] @ p['b1'].rotMat) * r

            if p['jump'] < 0:
                off = cubicInterpLoop(self.keyFrames, k, p)

                p['b1'].offset[:3] += off - p['b1'].lastOffset
                p['b1'].lastOffset = off
                p['animOffset'] = off

            ang = p['b1'].angles
            ang += np.array(self.keyFrames[k][1]['angle'], 'float32') * (1-r) * sign
            ang += np.array(self.keyFrames[k+1][1]['angle'], 'float32') * r * sign
            p['b1'].rotate(ang)

            p["rig"].interpPose(self.keyFrames[k][1], self.keyFrames[k+1][1], r)
