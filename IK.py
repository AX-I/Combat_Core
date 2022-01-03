# IK stuff

from math import pi, acos, atan, sqrt, atan2
import numpy as np

from Phys import eucLen

def doArmIK(armU, target):
    armD = armU.children[0]
    hand = armD.children[0]

    pos = armU.TM[3,:3]
    rot = armU.TM[:3,:3] # is object->world rotation

    targY = eucLen(target - pos)
    d1 = eucLen(armD.offset)
    d2 = eucLen(hand.offset)

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
    P = -atan(targLocal[1] / sqrt(targLocal[0]**2 + targLocal[2]**2)) # pitch
    R = pi - atan2(targLocal[0], targLocal[2])  # yaw

    if (pi < R < pi*5/3): R = -pi/3  # behind
    if (pi*2/3 < R < pi): R = pi*2/3 # other side
    #R = max(-pi/3, min(pi*2/3, R))

    # +X down, -X up
    # +Y forward
    # +Z tilt forward
    # Elbow is entirely +Y
    armU.rotate((P,U + R,0))
    armD.rotate((0,L,0))
    armD.children[0].rotate((0,0,-pi/2))


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

    # Note: not correct because pitch will
    # affect endpoint

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

