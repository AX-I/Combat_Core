# Basic behaviors
# Multiple agents

# Todo:
# x ignore jumping for prediction
# x shoot to deflect incoming projectiles
# x sidestep to avoid incoming projectiles
# x async navigation
# > not shoot explosive if friend is in the way or too close impact

import numpy as np
from math import atan2, pi, sin, cos
import time
import random

def normalize(v):
    return v / np.linalg.norm(v)

def sample(distr):
    """list of weights => index"""
    tot = sum(distr)
    r = random.random() * tot
    s = 0
    for i in range(len(distr)):
        x = distr[i]
        if (r > s) and (r <= s+x):
            return i
        s += x
    
def follow(target, current, radius, tolerance, isMoving):
    """target, current as (x,y,z) => move, direction"""
    r = atan2(*(target[2::-2] - current[2::-2]))

    dist = np.linalg.norm(target - current)

    p = (target[1] - current[1]) / dist

    m = False
    if not isMoving:
        m = dist > (radius + tolerance)
    else:
        m = dist > (radius - tolerance)

    return (m, r, p)

def sightLine(target, current, navMap, clear=False, relax=0):
    hm = navMap["map"]
    if hm is None: return True
    tpos = (target - navMap["origin"])[::2] / navMap["scale"]
    tpos = np.round(tpos)
    cpos = (current - navMap["origin"])[::2] / navMap["scale"]
    cpos = np.round(cpos)

    diffy = tpos[0] - cpos[0]
    diffx = tpos[1] - cpos[1]
    diff = int(max(abs(diffy), abs(diffx)))
    slopey = diffy / diff
    slopex = diffx / diff
    visible = True
    for i in range(diff-relax):
        cy = cpos[0] + i*slopey
        cx = cpos[1] + i*slopex
        if not navMap["map"][int(cy), int(cx)]:
            visible = False
            break

        if clear:
            rvec = np.array((diffx, diffy))
            rvec /= np.linalg.norm(rvec)
            cy += rvec[0]; cx += rvec[1]
            if not navMap["map"][int(cy), int(cx)]:
                visible = False; break
            cy -= 2*rvec[0]; cx -= 2*rvec[1]
            if not navMap["map"][int(cy), int(cx)]:
                visible = False; break

    return visible

def dijkstra(tpos, cpos, nmap):
    """tpos, cpos => (y, x)  |  nmap => np.array(dtype=bool)"""
    nm = np.array(nmap)
    dm = np.empty(nm.shape, dtype="int")
    dm[:] = -1
    dm[tuple(cpos)] = 0
    prev = np.empty((*nm.shape, 2), dtype="int")
    prev[:] = -1

    iy, ix = cpos
    while True:
        dist = dm[iy, ix]
        td = dist + 1
        if nm[iy+1, ix]:
            cd = dm[iy+1, ix]
            if (td < cd) or (cd == -1):
                dm[iy+1, ix] = td
                prev[iy+1, ix] = (iy, ix)
        if nm[iy-1, ix]:
            cd = dm[iy-1, ix]
            if (td < cd) or (cd == -1):
                dm[iy-1, ix] = td
                prev[iy-1, ix] = (iy, ix)
        if nm[iy, ix+1]:
            cd = dm[iy, ix+1]
            if (td < cd) or (cd == -1):
                dm[iy, ix+1] = td
                prev[iy, ix+1] = (iy, ix)
        if nm[iy, ix-1]:
            cd = dm[iy, ix-1]
            if (td < cd) or (cd == -1):
                dm[iy, ix-1] = td
                prev[iy, ix-1] = (iy, ix)
        
        nm[iy, ix] = False

        if (nm == False).all(): break

        zc = dm[(dm > 0) & nm]
        if zc.shape[0] == 0: break
        
        w = np.where((dm == np.min(zc)) & nm)
        
        iy, ix = w[0][0], w[1][0]

    return dm, prev

def navProcess(q_in, q_out):
    # q_in has elements (aiNum, args)
    while True:
        try:
            a = q_in.get(True, 0.2)
            if a is None: break
            r = dijkstra(*a[1])
            q_out.put((a[0], r), True, 0.2)
        except (Full, Empty):
            pass

class AIAgent:
    def __init__(self, num, name):
        self.AInum = num
        self.name = name

        self.behavior = {"none":0.05, "follow":0.5, "navigate":0,
                         "pathfind":0, "retreat":0}
        self.stuck = 0
        self.lostTrack = 0

        self.aggressiveness = 0.

        self.lastPos = np.zeros(4)

        self.navTarget = None
        self.targPred = np.zeros((4,))
        self.targetInterest = 4
        self.dirCC = 0
        
        self.navPath = None
        self.pathLen = None
        
class AIManager:
    def setupAI(self, nums):
        self.agents = {}

        for x in nums:
            n = "CPU " + str(x)
            a = AIAgent(x, n)
            self.activePlayers[n] = x
            self.players[x]["fCam"] = True

            self.agents[x] = a
        
        self.qI = mp.Queue(12)
        self.qO = mp.Queue(12)
        self.navProcess = mp.Process(target=navProcess,
                                     args=(self.qI, self.qO))
        self.navProcess.start()
        self.navResults = {}
        
    def updateAI(self):
        # Could do some aggressiveness scale
        # which is sum of health, energy, target's health etc
        # and decided by random sample
        # and could be biased in settings
        
        # Behaviors: follow, navigate, retreat, etc
        # Strafe to avoid shots
        playerIndex = {int(v):k for k, v in self.activePlayers.items()}
        
        for pn in self.agents:
            agent = self.agents[pn]
            a = self.players[pn]

            closestDist = 1000
            closestPlayer = None
            
            closestDistTarget = 1000
            closestTarget = None
            
            for p in self.actPlayers:
                if (p == pn) or ("deathTime" in self.players[p]): continue
                
                d = np.sum((a["b1"].offset - self.players[p]["b1"].offset)**2)

                if (d < closestDist):
                    closestPlayer = p
                    closestDist = d
                            
                if p in playerIndex:
                    if "CPU " in playerIndex[p]: continue

                if (d < closestDist):
                    closestTarget = p
                    closestDistTarget = d

            if closestPlayer is None:
                try:
                    if time.time() - self.endTime > (3 + random.random()*2):
                        if a["gestId"] != "gg":
                            gi = 2
                            if self.uInfo["End"][0] == "DRAW":
                                gi = (0,2,3)[random.randint(0,2)]
                            self.gesture(pn, gi, "gg")
                except AttributeError:
                    pass
                closestPlayer = self.selchar
            if closestTarget is None:
                closestTarget = self.selchar

            # Change this to retreat if closestTarget otherwise
            # sidestep if following and closestPlayer
            if closestDist < 3:
                if not "deathTime" in a:
                    agent.behavior["retreat"] = 0.5
                    agent.navTarget = self.players[closestPlayer]
            
            if agent.behavior["retreat"] > 0:
                if closestDist > 5:
                    agent.behavior["retreat"] = 0
                    agent.navTarget = self.players[closestTarget]
            
            if agent.navTarget is None:
                agent.navTarget = self.players[closestTarget]
            
            if closestTarget != agent.navTarget["id"]:
                if "deathTime" in agent.navTarget:
                    agent.targetInterest = 0
                agent.targetInterest -= 2*self.frameTime

            if agent.targetInterest < 0:
                agent.navTarget = self.players[closestTarget]
                agent.targetInterest = 4

            diff = a["b1"].offset - agent.lastPos

            if np.sum(diff[::2]) != 0:
                agent.stuck = 0

            a["cv"] = 0

            choice = list(agent.behavior)[sample(list(agent.behavior.values()))]
            
            if choice == "follow":
                self._follow(pn)
            if choice == "navigate":
                self._navigate(pn)
            if choice == "pathfind":
                self._pathfind(pn)
            if choice == "retreat":
                self._retreat(pn)
            if choice == "none":
                pass

            # Avoid / deflect incoming projectiles
            #for r in self.srbs:
            for i in range(len(self.spheres)):
                if "deathTime" in a: continue
                rb = self.srbs[i]
                if rb.disabled: continue
                
                d = a["b1"].offset[:3] - rb.pos
                sp = agent.navTarget["b1"].offset[:3] - rb.pos
                if normalize(d) @ normalize(rb.v) > 0.9:
                    if normalize(sp) @ normalize(rb.v) < -0.9:
                        avoid = True
##                        if a["Energy"] > 0.2:
##                            comp = 0#np.linalg.norm(d) / self.bulletSpeed
##                            fol = follow(rb.pos + comp * rb.v, a["b1"].offset[:3],
##                                     1, 0, True)
##                            a["cr"] = fol[1]
##                            vh = fol[2]
##                            avoid = not self.fire("red", pn, vh)
                        if avoid:
                            vvh = np.array((sin(a["cr"]), 0, -cos(a["cr"])))
                            x = vvh @ (normalize(d) - normalize(rb.v))
                            a["cv"] = 3 * -normalize(x)
                            a["moving"] = -1

            try:
                x = not "CPU " in playerIndex[agent.navTarget["id"]]
            except KeyError:
                x = True
            if x:
                self._fire(pn)

            if self.frameNum == 20:
                self.gesture(pn, 2, "ss")

            if "deathTime" in a:
                if (self.frameNum - a["deathTime"])*self.frameTime >= 2:
                    if a["gestId"] != "aa":
                        gi = 1
                        if "End" in self.uInfo:
                            if self.uInfo["End"][0] == "DRAW":
                                gi = (0,2,3)[random.randint(0,2)]
                        self.gesture(pn, gi, "aa")

            agent.lastPos = np.array(a["b1"].offset)
            agent.targPred = np.array(agent.navTarget["b1"].offset)

    def _retreat(self, pn):
        agent = self.agents[pn]
        a = self.players[pn]

        fol = follow(agent.navTarget["b1"].offset, a["b1"].offset,
                         1, 0, a["moving"])
        a["cr"] = fol[1]
        a["moving"] = -1
        a["cv"] = 6 * random.randint(0,1) - 3
        
    def _fire(self, pn):
        agent = self.agents[pn]
        a = self.players[pn]
        
        fire = self.getHealth(pn) < 1
        fire = fire and (a["Energy"] > 0.3)
        fire = fire and ("deathTime" not in agent.navTarget)
        if fire:
            visible = sightLine(agent.navTarget["b1"].offset[:3],
                                a["b1"].offset[:3], self.atriumNav,
                                relax=1)
            visible = visible or (not follow(agent.navTarget["b1"].offset, a["b1"].offset,
                         3, 0, a["moving"])[0])
            isHit = ("isHit" in a) and (self.frameNum - a["isHit"]) < 5
            fire = fire and (visible or isHit)
        
        choice = "blank"
        choice2 = "red"
        if self.getHealth(pn) < 0.3:
            choice = "red"
            choice2 = "blank"

        if np.sum((a["b1"].offset - agent.navTarget["b1"].offset)**2) > 16:
            if a["Energy"] > 0.5:
                choice = "orange"
                choice2 = "red"
        
        if fire:
            pred = (agent.navTarget["b1"].offset - agent.targPred)
            pred[1] = 0
            dist = np.sqrt(np.sum((a["b1"].offset - agent.navTarget["b1"].offset)**2))
            fol = follow(agent.navTarget["b1"].offset + dist * pred, a["b1"].offset,
                         1, 0, a["moving"])
            a["cr"] = fol[1]
            vh = fol[2]
            if not self.fire(choice, pn, vh):
                self.fire(choice2, pn, vh)

    def _follow(self, pn):
        agent = self.agents[pn]
        a = self.players[pn]
        diff = a["b1"].offset - agent.lastPos

        if not sightLine(agent.navTarget["b1"].offset[:3], a["b1"].offset[:3],
                         self.atriumNav):
            agent.lostTrack += 1
        if agent.lostTrack > 5:
            agent.behavior["navigate"] += 0.2
            agent.lostTrack = 0
        
        if a["moving"] and (np.sum(diff) == 0):
            agent.stuck += 1
            if agent.stuck > 3:
                agent.behavior["navigate"] = 10
                agent.stuck = 0
            
            self.jump(pn)

        if random.random() < 0.1:
            a["cv"] = 4 * random.randint(0, 1) - 2
        
        fol = follow(agent.navTarget["b1"].offset, a["b1"].offset,
                        6, 1, a["moving"])
        a["moving"] = fol[0]
        a["cr"] = fol[1]

    def _navigate(self, pn):
        agent = self.agents[pn]
        a = self.players[pn]

        navMap = self.atriumNav
        hm = navMap["map"]
        tpos = (agent.navTarget["b1"].offset[:3] - navMap["origin"])[::2] / navMap["scale"]
        tpos = np.round(tpos).astype("int")
        cpos = (a["b1"].offset[:3] - navMap["origin"])[::2] / navMap["scale"]
        cpos = np.round(cpos).astype("int")

        if hm[tuple(cpos)] == False:
            agent.behavior["follow"] += 0.1
            
        nav = False
        try:
            p = self.navResults[pn]
            nav = self.navResults[pn] is None
        except KeyError:
            nav = True

        if nav:
            try: self.qI.put_nowait((pn, (tpos, cpos, hm)))
            except Full: pass
            return
        
        self.navResults[pn] = None
        
        path = []
        s = p[1][tuple(tpos)]
        if (s == -1).all(): s = p[1][(tpos[0]+1, tpos[1])]
        if (s == -1).all(): s = p[1][(tpos[0]-1, tpos[1])]
        if (s == -1).all(): s = p[1][(tpos[0], tpos[1]+1)]
        if (s == -1).all(): s = p[1][(tpos[0], tpos[1]-1)]
        
        while True:
            cy, cx = tuple(s)
            ny, nx = tuple(s)
            if not hm[cy+1, cx]: ny -= 1
            if not hm[cy-1, cx]: ny += 1
            if not hm[cy, cx+1]: nx -= 1
            if not hm[cy, cx-1]: nx += 1

            path.append((ny, nx))
            s = p[1][tuple(s)]
            if (s == -1).all(): break
        
        agent.navPath = path[2:]
        
        agent.pathLen = 0

        agent.behavior["pathfind"] = 1
        agent.behavior["navigate"] = 0

    def _pathfind(self, pn):
        agent = self.agents[pn]
        a = self.players[pn]
        diff = a["b1"].offset - agent.lastPos

        navMap = self.atriumNav

        if len(agent.navPath) == 0:
            agent.behavior["follow"] = 1
            agent.behavior["pathfind"] = 0
            return

        pathTarg = np.array([agent.navPath[-1][0], 0, agent.navPath[-1][1]])
        pathTarg = pathTarg * navMap["scale"] + navMap["origin"]

        if self.frameNum & 7 == 0:
            pathDest = np.array([agent.navPath[0][0], 0, agent.navPath[0][1]])
            pathDest = pathDest * navMap["scale"] + navMap["origin"]
            if np.sum((pathDest - agent.navTarget["b1"].offset[:3])**2) > 16:
                # Recalculate path
                agent.behavior["navigate"] = 10

        #print("Target", pathTarg)
        #print("Current", a["b1"].offset[:3])
        if np.sum((pathTarg[::2] - a["b1"].offset[:3:2])**2) < 4:
            agent.navPath.pop()
            if len(agent.navPath) == 0:
                agent.behavior["pathfind"] = 0
                a["moving"] = False
                return
            
            pathTarg = np.array([agent.navPath[-1][0], 0, agent.navPath[-1][1]])
            pathTarg = pathTarg * navMap["scale"] + navMap["origin"]
        
        fol = follow(pathTarg, a["b1"].offset[:3],
                     2, 0, a["moving"])
        a["moving"] = fol[0]

        if agent.stuck == 0:
            diffDir = (a["cr"] % (2*pi)) - (fol[1] % (2*pi))
            if abs(diffDir) > 0:
                # Counterclockwise
                agent.dirCC = ((diffDir > 0) and (diffDir < pi)) or (diffDir < -pi)
            
        a["cr"] = fol[1]
        
        #a["moving"] *= 0.5
        
        if a["moving"] and (np.sum(diff) == 0):
            agent.stuck += 1
            #a["cv"] = (self.dirCC * 2 - 1) * 3
            #print("Stuck", self.stuck)

            a["cr"] += (agent.dirCC * 2 - 1) * 0.8
            if agent.stuck > 2:
                a["cr"] *= 1.5
            if agent.stuck > 4:
                a["cr"] *= 1.5
            if agent.stuck > 8:
                self.jump(pn)
                agent.behavior["navigate"] = 100
                agent.behavior["pathfind"] = 0
                self.stuck = 0
                #a["cr"] = 0

        agent.pathLen += 1
        
        if agent.pathLen > 3:
            if sightLine(agent.navTarget["b1"].offset[:3], a["b1"].offset[:3],
                              self.atriumNav, clear=True):
                agent.behavior["follow"] += 0.1
                agent.lostTrack = 0

if __name__ == "__main__":
    from PIL import Image
    import time
    a = Image.open("../Atrium/AtriumNavA.png")
    b = np.array(a)[:,:,0] < 80
    dt1 = time.perf_counter()
    p = dijkstra([51, 48], [27, 12], b)
    dt2 = time.perf_counter()
    print(dt2 - dt1, "secs")
    
    d = p[0]
    i = np.zeros((*b.shape, 3), "uint8")
    i[d==-1] = (128, 0, 0)
    d[d==-1] = 0
    i[:,:,1] = (d * 255. / np.max(d)).astype("uint8")
    Image.fromarray(i).show()

    g = [1, 5, 3, 8, 2, 0, 1]
    f = np.zeros((len(g),),"int")
    for i in range(1000):
        f[sample(g)] += 1
    print(f)
