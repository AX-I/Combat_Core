import json
import numpy as np
from math import pi

def interpAttr(t: float, kf: list):
    """kf: list of (time, attr)"""
    r = None
    if t < kf[0][0]:
        return kf[0][1]
    for i in range(len(kf)):
        if t < kf[i][0]:
            r = t - kf[i-1][0]
            r /= kf[i][0] - kf[i-1][0]
            break
    if r is None:
        return kf[i][1]

    return kf[i-1][1] * (1-r) + kf[i][1] * r


def loadAnim(fn, timeScale=1):
    """Returns (time, angles, root offset, angle array)"""
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
                ar = flattenPose(cp)
                keyFrames.append((ct, cp, np.array(co, 'float'), ar))
                co = [0,0,0]
    return keyFrames

def flattenPose(p):
    """For basic humanoid rig"""
    ch = 'children'
    ag = 'angle'
    bod = p[ch][0]
    armr, arml = bod[ch][0], bod[ch][1]
    legr, legl = p[ch][1], p[ch][2]
    f = [p[ag], bod[ag],
         armr[ag], armr[ch][0][ag], armr[ch][0][ch][0][ag],
         arml[ag], arml[ch][0][ag], arml[ch][0][ch][0][ag],
         bod[ch][2][ag],
         legr[ag], legr[ch][0][ag], legr[ch][0][ch][0][ag],
         legl[ag], legl[ch][0][ag], legl[ch][0][ch][0][ag]]
    return np.array(f)

def cubicInterp(t: float, *args):
    """Takes target x and four (x, y) coords"""
    y = np.array([[a[1] for a in args]], 'float32').T
    M = np.array([[a[0]**i for i in range(3,-1,-1)] for a in args], 'float32')
    curve = np.linalg.inv(M) @ y
    sol = np.array([t**i for i in range(3,-1,-1)]) @ curve
    return sol[0]

def cubicInterpLoop(kf, k, p, timer='poset'):
    """kf: keyframes (time, pose, offset), k: current keyframe, p: player"""
    k_prev = k-1 if k > 0 else k-2
    k_next = k+2 if k < len(kf)-2 else (k+3)%len(kf)
    kfn = (kf[k_prev], kf[k], kf[k+1], kf[k_next])

    yc0 = [x[2][0] for x in kfn]
    yc1 = [x[2][1] for x in kfn]
    yc2 = [x[2][2] for x in kfn]
    xc = [x[0] for x in kfn]
    for i in range(len(xc) - 1):
        if xc[i] > xc[i+1]:
            if k > 0:
                xc[i+1] += kf[-1][0] - kf[0][0]
            else:
                xc[i] -= kf[-1][0] - kf[0][0]
    off = np.array([cubicInterp(p[timer], *zip(xc, yc0)),
                    cubicInterp(p[timer], *zip(xc, yc1)),
                    cubicInterp(p[timer], *zip(xc, yc2))])
    return off


class AnimManager:

    def fmtAng(self, a):
        """Returns in (-pi, pi]"""
        a = a % (2*pi)
        if a > pi: a -= 2*pi
        return a

    def stepPoseLoop(self, p, vobj, keyFrames, st=1,
                     loop=True, bone=None, timer='poset',
                     offsetMult=1, isFlat=False):
        p[timer] += p['pstep'] * st
        if p[timer] > keyFrames[-1][0]:
            if not loop: return
            p[timer] -= keyFrames[-1][0] - keyFrames[0][0]
        if p[timer] < keyFrames[0][0]:
            p[timer] += keyFrames[-1][0] - keyFrames[0][0]

        if len(self.keyFrames) < 2: return
        k = None
        for i in range(len(keyFrames)):
            if p[timer] < keyFrames[i][0]:
                k = max(0, min(len(keyFrames)-2, i-1))
                r = p[timer] - keyFrames[k][0]
                r /= keyFrames[k+1][0] - keyFrames[k][0]
                break
        if k is not None:
            sign = 1 if st > 0 else -1

            if p['jump'] < 0 and bone is None:
                # Linear interp
                # off = (keyFrames[k][2] @ p['b1'].rotMat) * (1-r)
                # off += (keyFrames[k+1][2] @ p['b1'].rotMat) * r

                off = cubicInterpLoop(keyFrames, k, p, timer) @ p['b1'].rotMat
                if st < 0: off[1] = -0.4 * off[1] - 0.08

                off *= offsetMult

                p['b1'].offset[:3] += off - p['b1'].lastOffset
                p['b1'].lastOffset = off
                p['animOffset'] = off

            if bone is None:
                ang = p['b1'].angles
                diff = np.array(keyFrames[k][1]['angle'], 'float32') * (1-r)
                diff += np.array(keyFrames[k+1][1]['angle'], 'float32') * r
                diff[2] *= sign
                p['b1'].rotate(ang + diff)

            if isFlat:
                pose = p['rig'].interpFlat(keyFrames[k][3], keyFrames[k+1][3], r)
                p['rig'].importPoseFlat(pose, updateRoot=False)
            else:
                pose = p['rig'].interpTree(keyFrames[k][1], keyFrames[k+1][1], r)
                if bone is None:
                    bone = p['rig']
                    bone.importPose(pose, updateRoot=False)
                else:
                    bone.importPose(pose, updateRoot=True)
