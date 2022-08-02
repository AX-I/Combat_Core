import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import pyopencl as cl

BLOCK_SIZE = 128
mf = cl.mem_flags

class CLObject:
    name: str
    buf: cl.Buffer
    shape: np.array

    def __init__(self, name: str, buf: cl.Buffer, shape: np.array):
        self.name = name
        self.buf = buf
        self.shape = shape
        self.filters = {}

    def __getitem__(self, i):
        if i == 'buf':
            return self.buf
        if i == 'shape':
            return self.shape

        if type(i) is slice:
            self.filters['crop'] = i.start
            return self
        if type(i) is tuple:
            if i[1].step == -1:
                self.filters['flip'] = 1
            return self


class NPCanvas:
    ctx: cl.Context
    cq: cl.CommandQueue
    prog: cl.Program

    def imgText(self, dText: str, dFill: tuple, dFont,
                blur=4, bFill=(0,0,0), method='box', blurWidth=6) -> np.array:
        """returns np array of text
        method is box or gauss
        """
        pad = 8 + blur * 8 + int(blurWidth * 3)

        s = self.textSize.textsize(dText, font=dFont)
        a = Image.new("RGBA", (2*(s[0]//2)+pad, 2*(s[1]//2)+pad),
                      color=(*bFill,0))
        for ix in range(blur):
            d = ImageDraw.Draw(a)
            d.text((pad//2,pad//2), dText, fill=(*bFill,255), font=dFont, align="center")
            if method == 'box':
                a = a.filter(ImageFilter.BoxBlur(blurWidth))
            elif method == 'gauss':
                a = a.filter(ImageFilter.GaussianBlur(blurWidth))
        d = ImageDraw.Draw(a)
        d.text((pad//2,pad//2), dText, fill=dFill, font=dFont, align="center")
        return np.array(a)


    def drawText(self, fr: cl.Buffer, dText: str, dFill: tuple, dFont,
                 coords: tuple,
                 blur=2, bFill=(0,0,0), method='box', blurWidth=6) -> None:
        """Draw text onto fr
        coords => offset from center (y, x)
        """
        coords = (int(coords[0] + self.H//2), int(coords[1] + self.W//2))

        if dText not in self.UItexts:
            b = self.imgText(dText, dFill, dFont, blur, bFill,
                             method, blurWidth)

            b = (b*256).astype('uint16')

            buf = cl.Buffer(self.ctx, mf.READ_ONLY, size=b.nbytes)
            cl.enqueue_copy(self.cq, buf, b)
            self.UItexts[dText] = {'buf': buf, 'shape': np.array(b.shape, 'float32')}

        b = self.UItexts[dText]

        self.prog.blend(self.cq, (self.W*self.H//BLOCK_SIZE, 1), (BLOCK_SIZE, 1),
                        fr, self.W, self.H,
                        b['buf'], *b['shape'],
                        np.int32(coords[1]), np.int32(coords[0]),
                        np.int32(1),
                        np.int32(0),
                        np.float32(0),
                        g_times_l=True)


    def blend(self, dest: cl.Buffer, source: cl.Buffer,
              coords: tuple, method='alpha',
              effect=None, effectArg=0) -> None:
        """Blend image source onto dest, centered at coords (x, y)
        Preconditions:
            - method in {'alpha', 'add', 'screen',
                         'replace', 'hard light'}
            - effect in {None, 'flip', 'crop', 'roll', 'rot', 'mult'}
        """

        METHOD = {'alpha':1, 'add':2, 'screen':3, 'replace':4, 'hard light':5}
        EFFECT = {None:0, 'flip':1, 'crop':2, 'roll':3, 'rot':4, 'mult':5}

        effectApplied = EFFECT[effect]

        if type(source) is CLObject:
            if 'flip' in source.filters:
                effectApplied = EFFECT['flip']
                del source.filters['flip']
            if 'crop' in source.filters:
                effectApplied = EFFECT['crop']
                effectArg = source.filters['crop']
                del source.filters['crop']

        self.prog.blend(self.cq, (self.W*self.H//BLOCK_SIZE, 1), (BLOCK_SIZE, 1),
                        dest, self.W, self.H,
                        source['buf'], *source['shape'],
                        np.int32(coords[0]), np.int32(coords[1]),
                        np.int32(METHOD[method]),
                        np.int32(effectApplied),
                        np.float32(effectArg),
                        g_times_l=True)


    def gamma(self, dest: cl.Buffer):
        """Convert linear -> gamma"""
        self.prog.gamma(self.cq, (self.W*self.H//BLOCK_SIZE, 1), (BLOCK_SIZE, 1),
                        dest, self.W, self.H,
                        g_times_l=True)
