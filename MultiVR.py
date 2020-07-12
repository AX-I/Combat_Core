# VR HMD and Controllers

import Multi
import numpy as np
import random
import AI

import json
import time

import OpsConv

import openvr
import ctypes

PATH = OpsConv.PATH

class CombatVR(Multi.CombatApp):
    def __init__(self):
        super().__init__()
        
        vr_sys = openvr.init(openvr.VRApplication_Scene)
        poses_t = openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount
        poses = poses_t()

        ctrls = []

        for i in range(5):
            c = vr_sys.getTrackedDeviceClass(i)
            if c == openvr.TrackedDeviceClass_HMD:
                HMD_id = i
            elif c == openvr.TrackedDeviceClass_Controller:
                print("Controller:", i)
                ctrls.append(i)
    
        self.ov = openvr.VROverlay()
        self.cmp = openvr.VRCompositor()
        self.vrsys = openvr.VRSystem()

        self.CONTROLLERS = ctrls
        
        self.VRposes = poses

        k = random.randint(0, 1000)
        self.vrBuf1 = self.ov.createOverlay("Buffer 1 " + str(k), "A")
        self.vrBuf2 = self.ov.createOverlay("Buffer 2 " + str(k), "B")

        # FOV 80 size 0.2
        # FOV 120 size 0.6
        self.ov.setOverlayWidthInMeters(self.vrBuf1, 0.6)
        self.ov.setOverlayWidthInMeters(self.vrBuf2, 0.6)

        self.ov.setOverlayFromFile(self.vrBuf1, PATH+"lib/Combat.png")
        self.ov.setOverlayFromFile(self.vrBuf2, PATH+"lib/Combat.png")
        self.ov.showOverlay(self.vrBuf1)
        self.ov.showOverlay(self.vrBuf2)

        mt = [(ctypes.c_float * 4) (1, 0, 0, 0.02),
              (ctypes.c_float * 4) (0, 1, 0, 0),
              (ctypes.c_float * 4) (0, 0, 1, -0.2)]
        
        y = openvr.HmdMatrix34_t(*mt)
        
        self.ov.setOverlayTransformTrackedDeviceRelative(self.vrBuf1, HMD_id, y)
        self.ov.setOverlayTransformTrackedDeviceRelative(self.vrBuf2, HMD_id, y)

        self.VRMode = True

    def frameUpdateVR(self):
        if self.frameNum == 0:
            self.players[self.selchar]["fCam"] = True

        self.frameStart = time.perf_counter()

        sc = self.selchar

        scale = 1.55
        offY = -0
        
        self.cmp.waitGetPoses(self.VRposes, None)
        HMD_pose = self.VRposes[openvr.k_unTrackedDeviceIndex_Hmd]

        mat = np.array(HMD_pose.mDeviceToAbsoluteTracking.m)
        
        self.pos = mat[:,3] * scale
        self.pos[0] *= -1
        self.pos[1] += -self.players[sc]["cheight"] + offY
        self.pos += self.players[sc]["b1"].offset[:3]
        
        self.vMat = np.array(mat[:,:3])
        self.vMat = np.transpose(self.vMat)
        self.vMat[::2] = self.vMat[::-2]
        self.vMat[1:] = self.vMat[:0:-1]
        self.vMat[:,1] *= -1
        self.vMat[:,2] *= -1

        self.vv = self.vMat[0]


        if len(self.CONTROLLERS) > 0:
            CTR_pose = self.VRposes[self.CONTROLLERS[0]]

            mat = np.array(CTR_pose.mDeviceToAbsoluteTracking.m)
            vMat = np.array(mat[:,:3])
            vMat = np.transpose(vMat)
            vMat[::2] = vMat[::-2]
            vMat[1:] = vMat[:0:-1]
            vMat[:,1] *= -1
            vMat[:,2] *= -1

            forward = vMat[0]

            d = AI.follow(forward, np.zeros(3), 1, 1, 0)
            if self.players[sc]["fCam"]:
                self.players[sc]["cr"] = d[1]
            vh = d[2]


            i = self.vrsys.getControllerState(self.CONTROLLERS[0])[1]
            x, y = i.rAxis[0].x, i.rAxis[0].y # Touchpad
            self.players[sc]["moving"] = round(y)
            self.players[sc]["cv"] = -3 * x

            if i.ulButtonPressed & 4: # Grip
                self.jump()
            if i.ulButtonPressed & 2: # Upper menu
                if self.frameNum & 3 == 0:
                    self.players[sc]["fCam"] = not self.players[sc]["fCam"]

            if (i.ulButtonPressed > 1000) and (x*x + y*y == 0): # Trigger
                if self.frameNum & 7 == 0:
                    self.tgControl()
        
        if len(self.CONTROLLERS) > 1:
            if self.frameNum & 1:
                CTRL = self.CONTROLLERS[1]
                CTR_pose = self.VRposes[CTRL]
                i = self.vrsys.getControllerState(self.CONTROLLERS[1])[1]
                x, y = i.rAxis[0].x, i.rAxis[0].y

                if (y > 0.8): self.fire("blank", vh=vh)
                if (x > 0.8): self.fire("red", vh=vh)
                if (y < -0.8): self.fire("orange", vh=vh)
                if (x < -0.8): self.fire("black", vh=vh)

                if i.ulButtonPressed & 4:
                    self.gesture(self.selchar, 0)
                if i.ulButtonPressed & 2:
                    self.gesture(self.selchar, 2)
                if (i.ulButtonPressed > 1000) and (x*x + y*y == 0):
                    self.gesture(self.selchar, 3)

def run():
    global app
    
    while True:
        app = CombatVR()
        if app.proceed:
            print("Starting")
            app.start()
            print("Running")
            app.runBackend()
            if hasattr(app, "WIN"):
                state = 0
                try:
                    with open(PATH+"lib/Stat.txt") as f:
                        state = int(f.read())
                except: pass
                with open(PATH+"lib/Stat.txt", "w") as f:
                    state = state | (1 << app.stage)
                    f.write(str(state))
            print("Closing network")
            app.qi.put(None)
            while not app.qo.empty():
                try: app.qo.get(True, 0.2)
                except: pass
            app.qi.close()
            app.qo.close()
            app.qi.join_thread()
            app.qo.join_thread()
            app.server.terminate()
            app.server.join()
            try:
                with open(PATH+"lib/Stat.txt") as f: pass
            except FileNotFoundError:
                with open(PATH+"lib/Stat.txt", "w") as f: f.write("")
        print("Closing sound")
        app.si.put({"Fade":0}, True, 0.1)
        time.sleep(2.1)
        app.si.put(None, True, 0.1)
        app.finish()
        print("Finished")
        if not app.proceed: break
        fps = app.frameNum/app.totTime
        print("Average fps:", fps)

if __name__ == "__main__":
    run()
