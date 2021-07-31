# IK stuff

from math import pi, acos, atan
import numpy as np

from Phys import eucLen

def doFullLegIK(legU, target, root, footSize=0.2, interp=None):
    legD = legU.children[0]
    foot = legD.children[0]

    pos = legU.TM[3,:3]
    rot = legU.TM[:3,:3] # is object->world rotation

    targY = eucLen(target - pos)
    d1 = eucLen(legD.offset)
    d2 = eucLen(foot.offset) + footSize

    # Possible float precision issues
    if d1 + d2 < targY or d1 + targY < d2 or d2 + targY < d1:
        U = 0
        L = 0
    else:
        try:
            U = -acos((d1**2 + targY**2 - d2**2) / (2*d1*targY))
            L = pi - acos((d1**2 + d2**2 - targY**2) / (2*d1*d2))
        except ValueError:
            U = 0
            L = 0

    targLocal = (target - pos) @ np.transpose(rot)

    P = -atan(targLocal[0] / -targLocal[1]) # pitch
    R = atan(targLocal[2] / -targLocal[1])  # roll

    #print('R {:.3f} P {:.3f} U {:.3f}'.format(R, P, U))

    # -Z is UP, +Z is DOWN
    if interp is None:
        legU.rotate((R, 0, U + P))
        legD.rotate((0, 0, L))
        foot.rotate((-R, 0, -U-L - P))
        return

    pose = {'angle':(R, 0, U + P), 'children':[
            {'angle':(0,0,L), 'children':[
             {'angle':(-R, 0, -U-L - P)}
            ]}
           ]}
    temp = legU.exportPose()
    i = root['rig'].interpTree(temp, pose, interp)
    legU.importPose(i)

