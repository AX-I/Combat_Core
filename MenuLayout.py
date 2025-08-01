
import time
from math import sin
import numpy as np
from PIL import Image, ImageFilter, ImageFont

import os, sys

if getattr(sys, "frozen", False):
    PATH = os.path.dirname(sys.executable) + "/"
else:
    PATH = os.path.dirname(os.path.realpath(__file__)) + "/"

blueFG = (200,230,255)
blueBG = (70,130,255)
greenFG = (200,255,200)
greenBG = (60,210,60)
yellowFG = (255,230,200)
yellowBG = (255,130,70)
redFG = (255,200,200)
redBG = (255,70,70)


smallScale = 0.92

def mainMenuSetup(self):
    resScale = self.H / 600

    global bHalfTop, bHalfBot
    bHalfTop = 50 * smallScale * resScale
    bHalfBot = 48 * smallScale * resScale

    tFont = "../Assets/HTowerT_Bold_4.ttf"
    sFont = "../Assets/HTOWERT.TTF"

    #s = "FrankRuehlCLM-Medium.ttf ITCBLKAD.TTF PARCHM.TTF RAGE.TTF"
    #self.sFont = ImageFont.truetype(sFont, int(48 * resScale))

    self.tFont = ImageFont.truetype(tFont, int(97 * resScale))

    self.aFont = ImageFont.truetype(sFont, int(68 * resScale))

    self.bFont = ImageFont.truetype("../Assets/ITCBLKAD.TTF",
                                    int(60 * resScale * smallScale))

    self.c2Font = ImageFont.truetype(sFont, int(36 * resScale))
    self.cFont = ImageFont.truetype(sFont, int(26 * resScale * smallScale))

    perf = time.perf_counter()

    i = self.openImageCover('../Assets/Forest.jpg')
    self.bg = np.array(i)
    self.bg = (self.bg / 255.)*self.bg
    self.bg *= 0.4
    self.bg = self.makeCL('Bg', self.bg)


    i = self.openImageCover('../Assets/TitleLeaves.png')
    i = np.array(i)
    i = (i/255.) * i
    self.titleLeaves = self.makeCL('Leaves', i)

    self.notConnectedTG = 0

    icons = ["IconHome.png", "IconWeb.png"]
    self.icons = []
    for i in icons:
        b = Image.open('../Assets/' + i)
        sw = int(b.size[0]*0.45 * smallScale * resScale)
        sh = int(b.size[1]*0.45 * smallScale * resScale)
        b = b.resize((sw,sh), Image.BILINEAR)
        b = np.array(b)
        b[:,:,:3] = b[:,:,3:4]
        self.icons.append(self.makeCL(i, b))


    b = Image.open('../Assets/Circles.png')
    sw = int(b.size[0]*0.75 * resScale)
    sh = int(b.size[1]*0.75 * resScale)
    b = b.resize((sw,sh), Image.BILINEAR)
    b = np.repeat(np.array(b)[:,:,0:1], 4, axis=-1)
    self.titleCircles = self.makeCL('titleCircle', b)

    self.textEntry = 'User'

    print("mainMenuSetup", time.perf_counter() - perf)


def mainMenuLayout(self):

    frame = self.frameBuf
    resScale = self.H / 600


    sTime = time.time() - self.st

    self.blend(frame, self.bg,
               (self.W2 - self.parx/6, self.H2 - self.pary/6), 'replace')

    self.blend(frame, self.titleLeaves,
               (self.W2 - self.parx/4, self.H*0.4 - self.pary/4), 'alpha')

    self.blend(frame, self.bgNoise,
               (self.W2, self.H2), 'alpha',
               effect='roll', effectArg=20*sTime*resScale)


    bBlur = 1
    bWidth = 5*resScale
    offset = (self.menuButton.shape[1] + self.menuOrnament.shape[1]) // 2 - 0.5

    h2 = self.H * 0.54



    xpos = self.W*0.8 - self.parx

    buttonCenters = [(self.H*(0.2 + 0.21*i) - self.pary, xpos) for i in range(4)]
    self.menuButtonCenters = buttonCenters

    yc = buttonCenters[-1][0]

    if 0 < self.buttonSelect <= 4:
        c = buttonCenters[self.buttonSelect - 1]
        self.blend(frame, self.menuButtonHighlight,
                   c[::-1], 'add',
                   effect='mult', effectArg=1.2)


    i1 = int(3 * resScale)
    i2 = int(6 * resScale + 0.8)

    # Start button
    for i in range(3):
        ypos = buttonCenters[i][0]
        self.blend(frame, self.menuButton,
                   (xpos, ypos), 'alpha')
        self.blend(frame, self.menuOrnament[:,::-1],
                   (xpos + offset, ypos), 'alpha')
        self.blend(frame, self.menuLights[i1:i2],
                   (xpos, ypos - bHalfTop), 'alpha')
        self.blend(frame, self.menuLights[i1:i2],
                   (xpos, ypos + bHalfBot), 'alpha')



    # About Controls button

    self.blend(frame, self.menuOrnamentLine,
               (xpos - self.H*0.2, yc), 'alpha')
    self.blend(frame, self.menuButton,
               (xpos, yc), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xpos, yc - bHalfTop), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xpos, yc + bHalfBot), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xpos, yc), 'alpha')
    self.blend(frame, self.menuOrnament[:,::-1],
               (xpos + offset, yc), 'alpha')



    # Username Server
    yc = buttonCenters[-1][0] - 32*resScale
    xc = xpos - self.H*0.56
    offset2 = (self.menuEntry.shape[1] - self.menuButton.shape[1])/2
    self.blend(frame, self.menuEntry,
               (xc + offset2, yc), 'alpha')
    self.blend(frame, self.menuEntry,
               (xc + offset2, yc+65*resScale), 'alpha')

    if self.textEntry == 'User':
        # yc += 65*resScale
        yc += self.H*0.1083

    xo = 144*smallScale*resScale
    yo = 23*smallScale*resScale
    self.blend(frame, self.menuLights[i1:i2],
               (xc, yc - yo), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xc + xo, yc - yo), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xc, yc + yo), 'alpha')
    self.blend(frame, self.menuLights[i1:i2],
               (xc + xo, yc + yo), 'alpha')

##    self.blend(frame, self.entryHL,
##               (self.W2 + offset2 + 120*resScale*sin(time.time() - self.st),
##                self.H*(0.7 + 0.1083 * (self.textEntry == 'Serv'))), 'alpha')


    yc = buttonCenters[-1][0] - 32*resScale

    if self.notConnectedTG:
        self.blend(frame, self.menuEntryHighlightRed,
                   (xc + offset2, yc+65*resScale), 'add')

    self.drawText(frame, self.unameDisplay, (255,255,255), self.eFont,
                  (yc-self.H2 -2, xc-self.W2 + offset2), blur=0)
    self.drawText(frame, self.servDisplay, (255,255,255), self.eFont,
                  (yc-self.H2 + self.H*0.1083 -2, xc-self.W2 + offset2), blur=0)


    # Web/Local icons
    self.iconsPos = (xpos - self.H*0.86, yc + self.H*0.1083)
    for i in range(len(self.icons)):
        s = i ^ (self.runMod['state'] == 'disabled')
        self.blend(frame, self.icons[i],
                   (self.iconsPos[0] + 50*i*resScale, self.iconsPos[1]), 'add',
                   effect='mult', effectArg=0.1 + 0.6*s)



    mainHandleMouse(self, frame)


    fills = [yellowFG, yellowFG, yellowFG, yellowFG]
    blurs = [bBlur, bBlur, bBlur, bBlur]

    #if self.buttonSelect > 0:
    for i in range(len(fills)):
        if i != self.buttonSelect - 1:
            fills[i] = (160,160,160)
            blurs[i] = 0


    offsets = [(-6 - 2*resScale, 0),
               (-6 + 4*resScale, 4*resScale),
               (-2, 0)]
    texts = 'Start Join Settings'.split(' ')

    for i in range(len(texts)):
        self.drawText(frame, texts[i], fills[i], self.bFont,
                      (buttonCenters[i][0]-self.H2 + offsets[i][0],
                       xpos-self.W2 + offsets[i][1]),
                      blur=blurs[i], bFill=yellowBG,
                      method='gauss', blurWidth=bWidth)


    yc = buttonCenters[-1][0]
    self.drawText(frame, 'About', fills[3], self.cFont,
                  (yc-self.H2-3 -22*resScale, xpos-self.W2),
                  blur=blurs[3], bFill=yellowBG, method='gauss')
    self.drawText(frame, 'Controls', fills[3], self.cFont,
                  (yc-self.H2-3 +25*resScale, xpos-self.W2),
                  blur=blurs[3], bFill=yellowBG, method='gauss')


    titleX = self.W*0.36 - self.parx/2
    titleY = self.H*0.4 - self.pary/2

    titleYTop = titleY - self.H*0.1
    titleH = self.H*0.25
    titleYC = titleYTop + titleH*0.55

    self.blend(frame, self.titleCircles, (titleX, titleYC), 'add',
               effect='fadey', effectArg=sTime*20*resScale)


    self.blend(frame, self.menuTitle,
               (titleX, titleY + self.H*0.11), 'alpha')


    self.blendCursor(frame)


    whiteFG = (255,255,255)
    whiteBG = (180,180,180)
    self.drawText(frame, "AXI Combat", whiteFG, self.tFont,
                  (titleY-self.H2, titleX-self.W2 -14*resScale),
                  blur=2, bFill=whiteBG,
                  method='gauss', blurWidth=bWidth)
    self.drawText(frame, "v1.4", whiteFG, self.c2Font,
                  (titleY-self.H2 + 84*resScale, titleX-self.W2 + self.H*0.37),
                  bFill=whiteBG,
                  blur=2, blurWidth=bWidth, method='gauss')


##    self.drawText(frame, "Test", whiteFG, self.sFont,
##                  (-self.H//3 + 84*resScale, 0), blur=2, bFill=whiteBG,
##                  method='gauss', blurWidth=bWidth)


def mainHandleMouse(self, frame, click=False):
    """
    ####
    #### Handle mouse for main menu
    ####
    """
    if frame is None:
        frame = self.frameBuf

    CTIME = time.time()-self.st

    mx = self.mx + self.W2
    my = self.my + self.H2


    c = self.iconsPos[::-1]
    h = self.H//10
    w = self.W//10
    ey = (c[0] - h//2, c[0] + h//2)
    ex = (c[1] - w//2, c[1] + w//2)
    if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
        if click:
            if self.runMod['state'] != 'disabled':
                self.mkRouter()
                self.servDisplay = self.hostname.get()


    h = self.menuEntry.shape[0]
    w = self.menuEntry.shape[1]
    h2 = self.H*0.54

    xc = self.W*0.8 - self.H*0.6 - self.parx
    yc = self.menuButtonCenters[-1][0] - 0.053*self.H
    offset2 = (self.menuEntry.shape[1] - self.menuButton.shape[1])/2

    buttonCenters = [(yc, xc + offset2),
                     (yc + self.H*0.1083, xc + offset2)]

    bSel = 0
    for i in range(len(buttonCenters)):
        c = buttonCenters[i]
        ey = (c[0] - h//2, c[0] + h//2)
        ex = (c[1] - w//2, c[1] + w//2)

        if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
            if click:
                self.textEntry = ('User', 'Serv')[i]

            self.blend(frame, self.menuEntryOutline,
                       c[::-1], 'add', effect='mult', effectArg=1.2)

    h = self.menuButton.shape[0]
    w = self.menuButton.shape[1]

    buttonCenters = self.menuButtonCenters

    buttonCmds = [self.goStart, self.goJoin, self.gSettings, self.about]

    bSel = 0
    for i in range(len(buttonCenters)):
        c = buttonCenters[i]
        ey = (c[0] - h//2, c[0] + h//2)
        ex = (c[1] - w//2, c[1] + w//2)

        if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
            bSel = i + 1

            if click:
                buttonCmds[i]()
                break

            self.blend(frame, self.menuHighlight,
                       c[::-1], 'add',
                       effect='mult', effectArg=(0.9 + 0.3*sin(2.8*CTIME)))
            self.blend(frame, self.menuRingsW,
                       c[::-1], 'alpha',
                       effect='roll', effectArg=-20*CTIME)

            break

    if bSel and (bSel != self.buttonSelect):
        self.si.put({'Play':(PATH+'../Sound/Misc/MenuClickT.wav',
                             self.volmFX*0.5, False)})

    if bSel != self.buttonSelect:
        t = ['Start', 'Join', 'Settings', 'About']
        for i in t:
            try:
                del self.UItexts[i]
            except KeyError:
                pass

    self.buttonSelect = bSel



def stageSelectSetup(self):
    self.selectedStage = 0

    try: _ = self.stageBgs
    except AttributeError:
        makeStageBgs(self)


def makeStageBgs(self):
    resScale = self.H / 600
    self.stageBgs = []
    for i in range(len(self.loc)):
        im = self.openImageCover("../Assets/Preview_"+self.loc[i]+".jpg",
                                 blur=5*resScale)
        im = np.array(im).astype('float32')
        np.multiply(im, im, out=im)
        np.multiply(im, 0.4/255, out=im)
        im = self.makeCL(f'Bg{i}', im)
        self.stageBgs.append(im)

    self.stagePreviews = []
    for i in range(len(self.loc)):
        im = Image.open(PATH+"../Assets/Preview_"+self.loc[i]+".jpg").convert('RGBA')
        im = im.resize((int(320*resScale), int(200*resScale)), Image.BILINEAR)
        im = np.array(im)
        im = im / 255. * im * 0.9
        im = self.makeCL(f'Im{i}', im)
        self.stagePreviews.append(im)


def stageSelectLayout(self):
    """
    ####
    #### Stage select layout
    ####
    """

    frame = self.frameBuf
    resScale = self.H / 600


    sTime = time.time() - self.st

    self.blend(frame, self.stageBgs[self.selectedStage],
               (self.W2-self.parx/6, self.H2-self.pary/6), 'replace')
    self.blend(frame, self.bgNoise,
               (self.W2, self.H2), 'alpha',
               effect='roll', effectArg=20*sTime*resScale)

    bBlur = 1
    bWidth = 5*resScale

    self.loc = ["Desert", "CB Atrium", "Taiga", "New Stage", "Forest", 'Strachan']

    for i in range(len(self.loc)):
        yc = int(self.H * (0.2 + 0.8*i/len(self.loc))) - self.pary

        xc = self.W//4 - 30 * resScale - self.parx

        xoffset = 40 * (self.selectedStage == i)

        if self.buttonSelect == i + 1:
            self.blend(frame, self.menuEntryOutline,
                       (xc + xoffset, yc), 'add',
                       effect='mult', effectArg=1.2)

        self.blend(frame, self.menuEntry,
                   (xc + xoffset, yc), 'alpha')

        if self.selectedStage == i:
            self.blend(frame, self.menuRingsW,
                       (xc + xoffset, yc), 'alpha',
                       effect='roll', effectArg=-20*sTime)

        texty = yc - self.H2 - 4*resScale
        self.drawText(frame, self.loc[i], yellowFG, self.cFont,
                      (texty, xc - self.W2 + xoffset), blur=1,
                      bFill=yellowBG)


    self.blend(frame, self.stagePreviews[self.selectedStage],
               (self.W*0.7-self.parx/2, self.H2-self.pary/2), 'replace')

    self.blend(frame, self.menuFrame,
               (self.W*0.7 - 2*resScale-self.parx/2,
                self.H2 - 8*resScale-self.pary/2), 'alpha')


    # Back button
    wp = self.W*0.7-self.parx
    hp = self.H*0.85-self.pary
    self.blend(frame, self.menuButton,
               (wp, hp), 'alpha')
    self.blend(frame, self.menuLights[3:6],
               (wp, hp - bHalfTop), 'alpha')
    self.blend(frame, self.menuLights[3:6],
               (wp, hp + bHalfBot), 'alpha')


    stageHandleMouse(self, frame)

    

    fills = [yellowFG, yellowFG, yellowFG, yellowFG]
    blurs = [bBlur, bBlur, bBlur, bBlur]

    #if self.buttonSelect > 0:
##    for i in range(len(fills)):
##        if i != self.buttonSelect - 1:
##            fills[i] = (190,190,190)
##            blurs[i] = 0


    self.drawText(frame, 'Back', yellowFG, self.cFont,
                  (self.H*0.35-self.pary, self.W*0.2-self.parx), blur=1, bFill=yellowBG,
                  method='gauss', blurWidth=bWidth)


    self.blendCursor(frame)

    self.drawText(frame, "Select Location", (255,255,255), self.aFont,
                  (-self.H*0.36-self.pary/2,self.W//5-self.parx/2),
                  blur=2, bFill=(180,180,180),
                  method='gauss', blurWidth=bWidth)



def getButtonCoord(self, i):

    resScale = self.H / 600
    
    yc = int(self.H * (0.2 + 0.8*i/len(self.loc)))
    xc = self.W//4 - 30 * resScale
    xoffset = 40 * (self.selectedStage == i)
    return (yc-self.pary, xc+xoffset-self.parx)


def stageHandleMouse(self, frame, click=False):
    """
    ####
    #### Handle mouse for stage select
    ####
    """

    CTIME = time.time()-self.st

    mx = self.mx + self.W2
    my = self.my + self.H2

    # LRUD
    h = self.menuEntry.shape[0]
    w = self.menuEntry.shape[1]

    buttonCenters = [getButtonCoord(self, i) for i in range(len(self.loc))]
    buttonCenters.append((self.H*0.85-self.pary, self.W*0.7-self.parx)) # Back button

    bSel = 0
    for i in range(len(buttonCenters)):
        c = buttonCenters[i]
        ey = (c[0] - h//2, c[0] + h//2)
        ex = (c[1] - w//2, c[1] + w//2)

        if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
            bSel = i + 1

            if click:
                if i == len(buttonCenters) - 1:
                    self.goBack(0)
                else:
                    self.goStart(i)

                break

            self.blend(frame, self.menuEntryHighlight,
                       c[::-1], 'add',
                       effect='mult', effectArg=(0.9 + 0.3*sin(2.8*CTIME)))
            break


    if bSel and (bSel != self.buttonSelect):
        self.si.put({'Play':(PATH+'../Sound/Misc/MenuClickT.wav',
                             self.volmFX*0.5, False)})

        if bSel <= len(self.loc):
            self.selectedStage = bSel - 1

    if bSel != self.buttonSelect:
        pass

    self.buttonSelect = bSel


def joinSetup(self):
    pass

def joinLayout(self):
    """
    ####
    #### Join game layout
    ####
    """
    frame = self.frameBuf
    resScale = self.H / 600


    sTime = time.time() - self.st

    self.blend(frame, self.bg,
               (self.W2, self.H2), 'replace')
    self.blend(frame, self.bgNoise,
               (self.W2, self.H2), 'alpha',
               effect='roll', effectArg=20*sTime*resScale)

    for i in range(self.avls.size()):
        yc = int(self.H * (0.33 + 0.66*i/5))
        xc = self.W//4
        texty = yc - self.H2 - 3 * resScale

        self.blend(frame, self.menuEntry,
                   (xc, yc), 'alpha')

        self.drawText(frame, self.avls.get(i), yellowFG, self.cFont,
                      (texty, xc + 50 * resScale - self.W2), blur=1,
                      bFill=yellowBG)

    # Back button
    self.blend(frame, self.menuButton,
               (self.W*0.7, self.H*0.85), 'alpha')
    self.blend(frame, self.menuLights[3:6],
               (self.W*0.7, self.H*0.85 - bHalfTop), 'alpha')
    self.blend(frame, self.menuLights[3:6],
               (self.W*0.7, self.H*0.85 + bHalfBot), 'alpha')

    bWidth = 5*resScale
    self.drawText(frame, 'Back', yellowFG, self.cFont,
                  (self.H*0.35, self.W*0.2), blur=1, bFill=yellowBG,
                  method='gauss', blurWidth=bWidth)
    
    joinHandleMouse(self, frame)

    self.blendCursor(frame)

    self.drawText(frame, "Join Game", (255,255,255), self.aFont,
                  (-self.H*0.36,0), blur=2, bFill=(180,180,180),
                  method='gauss', blurWidth=bWidth)



def joinHandleMouse(self, frame, click=False):
    """
    ####
    #### Handle mouse for join game
    ####
    """

    CTIME = time.time()-self.st

    mx = self.mx + self.W2
    my = self.my + self.H2


    # LRUD
    h = self.menuEntry.shape[0]
    w = self.menuEntry.shape[1]

    buttonCenters = []
    for i in range(self.avls.size()):
        yc = int(self.H * (0.33 + 0.66*i/5))
        xc = self.W//4
        buttonCenters.append((yc, xc))
    buttonCenters.append((self.H*0.85, self.W*0.7))

    bSel = 0
    for i in range(len(buttonCenters)):
        c = buttonCenters[i]
        ey = (c[0] - h//2, c[0] + h//2)
        ex = (c[1] - w//2, c[1] + w//2)

        if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
            bSel = i + 1

            if click:
                if i == len(buttonCenters) - 1:
                    self.goBack(0)
                else:
                    self.gd = self.avls.get(i)
                    self.joinGame()

                break

            self.blend(frame, self.menuEntryHighlight,
                       c[::-1], 'add',
                       effect='mult', effectArg=(0.9 + 0.3*sin(2.8*CTIME)))
            break


    if bSel and (bSel != self.buttonSelect):
        self.si.put({'Play':(PATH+'../Sound/Misc/MenuClickT.wav',
                             self.volmFX*0.5, False)})

##        if bSel <= len(self.loc):
##            self.selectedStage = bSel - 1

    if bSel != self.buttonSelect:
        pass

    self.buttonSelect = bSel



def charLayout(self):
    """
    ####
    #### Character select layout
    ####
    """
    try: _ = self.stageBgs
    except AttributeError:
        makeStageBgs(self)

    frame = self.frameBuf
    resScale = self.H / 600

    sTime = time.time() - self.st

    self.blend(frame, self.stageBgs[self.selectedStage],
               (self.W2, self.H2), 'replace')
    self.blend(frame, self.bgNoise,
               (self.W2, self.H2), 'alpha',
               effect='roll', effectArg=20*sTime*resScale)

    fg = blueFG if self.chooseAI else yellowFG
    bg = blueBG if self.chooseAI else yellowBG

    for i in range(len(self.charNames)):
        yc, xc = getCharCoord(self, i)
        texty = yc - 3 * resScale

        charEnabled = 1 - int(self.stb[i]['state'] == 'disabled')

        self.drawText(frame, self.charNames[i], fg, self.cFont,
                      (texty - self.H2, xc - self.W2), blur=charEnabled,
                      bFill=bg)

    yc, xc = getCharCoord(self, len(self.charNames))

    if not self.gameConfig[4]:
        self.drawText(frame, 'Add AI', blueFG, self.cFont,
                      (yc - self.H2, xc - self.W2), blur=1,
                      bFill=blueBG)


    charHandleMouse(self, frame)

    self.blendCursor(frame)

    bWidth = 5*resScale
    self.drawText(frame, "Select Character", (255,255,255), self.aFont,
                  (-self.H*0.36,0), blur=2, bFill=(180,180,180),
                  method='gauss', blurWidth=bWidth)

def getCharCoord(self, i):
    if i < self.NSPECIAL:
        yc = self.H * (0.32 + 0.15*(i//3))
        xc = self.W2 + self.H * 1.4 * 0.25*((1.5-self.NSPECIAL*0.5 + i%3) - 1)
    else:
        j = i - self.NSPECIAL
        yc = self.H * (0.32 + 0.15*(1 + j//3))
        xc = self.W2 + self.H * 1.4 * 0.25*((j%3) - 1)
    return (yc, xc)


def charHandleMouse(self, frame, click=False):
    """
    ####
    #### Handle mouse for character select
    ####
    """
    CTIME = time.time()-self.st

    mx = self.mx + self.W2
    my = self.my + self.H2

    # LRUD
    h = self.menuButton.shape[0]
    w = self.menuButton.shape[1]

    buttonCenters = []
    for i in range(len(self.charNames) + (not self.gameConfig[4])):
        buttonCenters.append(getCharCoord(self, i))

    bSel = 0
    for i in range(len(buttonCenters)):
        c = buttonCenters[i]
        ey = (c[0] - h//2, c[0] + h//2)
        ex = (c[1] - w//2, c[1] + w//2)

        if (ey[0] < my < ey[1]) and (ex[0] < mx < ex[1]):
            if i < len(self.charNames):
                if self.stb[i]['state'] == 'disabled':
                    break
            bSel = i + 1

            if click:
                if i == len(self.charNames):
                    self.tgAI()
                else:
                    self.selChar(i)
                clearCharTexts(self)
                break

            self.blend(frame, self.menuHighlight,
                       c[::-1], 'add',
                       effect='mult', effectArg=(0.9 + 0.3*sin(2.8*CTIME)))
            self.blend(frame, self.menuRingsW,
                       c[::-1], 'alpha',
                       effect='roll', effectArg=-20*CTIME)

            break

    if bSel and (bSel != self.buttonSelect):
        self.si.put({'Play':(PATH+'../Sound/Misc/MenuClickT.wav',
                             self.volmFX*0.5, False)})

    self.buttonSelect = bSel

def clearCharTexts(self):
    for i in self.charNames:
        try:
            del self.UItexts[i]
        except KeyError:
            pass
