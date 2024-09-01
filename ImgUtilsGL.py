import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import moderngl as mgl

VS = open('PipeGL/trisetup_2d.c').read()
FS = open('ShadersGL/menu.c').read()

x = np.array([-1, -1, 1, 1, -1, 1])
y = np.array([1, -1, 1, 1, -1, -1])
z = np.ones(6)*-0.9999
u = (x+1)/2
v = (y+1)/2
TRI = np.dstack([x,y,z,u,v])

class GLObject:
    name: str
    buf: mgl.Texture
    shape: np.array

    prog: mgl.Program
    vbo: mgl.Buffer
    vao: mgl.VertexArray

    def __init__(self, ctx, cq, name: str, x: np.array):
        x = x.astype('uint8')

        buf = ctx.texture(x.shape[1::-1], x.shape[2], x, dtype='f1')

        self.name = name
        self.buf = buf
        self.shape = np.array(x.shape, dtype='int32')
        self.filters = {}

        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)

        v = TRI #* np.array((*x.shape[:2],1))
        self.vbo = ctx.buffer(v.astype('float32').tobytes())

        self.vao = ctx.vertex_array(self.prog, self.vbo, 'in_vert', 'in_UV')


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
    ctx: mgl.Context

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


    def drawText(self, fr: mgl.Framebuffer, dText: str, dFill: tuple, dFont,
                 coords: tuple,
                 blur=2, bFill=(0,0,0), method='box', blurWidth=6) -> None:
        """Draw text onto fr
        coords => offset from center (y, x)
        """
        coords = (coords[0] + self.H//2, coords[1] + self.W//2)

        if dText not in self.UItexts:
            b = self.imgText(dText, dFill, dFont, blur, bFill,
                             method, blurWidth)

            self.UItexts[dText] = GLObject(self.ctx, self.cq, dText, b)

        source = self.UItexts[dText]

        self.blend(fr, source, coords, 'alpha')


    def blend(self, dest: mgl.Framebuffer, source: GLObject,
              coords: tuple, method='alpha',
              effect=None, effectArg=0) -> None:
        """Blend image source onto dest, centered at coords (x, y)
        Preconditions:
            - method in {'alpha', 'add', 'screen',
                         'replace', 'hard light'}
            - effect in {None, 'flip', 'crop', 'roll', 'rot', 'mult', 'fadey'}
        """

        METHOD = {'alpha':1, 'add':2, 'screen':3, 'replace':4, 'hard light':5}
        EFFECT = {None:0, 'flip':1, 'crop':2, 'roll':3, 'rot':4, 'mult':5, 'fadey':6}
        effectApplied = EFFECT[effect]

        if 'flip' in source.filters:
            effectApplied = EFFECT['flip']
            del source.filters['flip']
        if 'crop' in source.filters:
            effectApplied = EFFECT['crop']
            effectArg = source.filters['crop']
            del source.filters['crop']

        if effect == 'roll':
            effectArg /= source.shape[1]

        source.buf.use(location=0)
        dest.use()

        blendParam = {'alpha':(mgl.FUNC_ADD, mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA),
                      'add':(mgl.FUNC_ADD, mgl.ONE, mgl.ONE),
                      'screen':(mgl.FUNC_REVERSE_SUBTRACT, mgl.ONE_MINUS_DST_COLOR, mgl.ONE),
                      'replace':(mgl.FUNC_ADD, mgl.ONE, mgl.ZERO),
                      'hard light':(mgl.FUNC_ADD, mgl.ONE, mgl.SRC_ALPHA)}
        self.ctx.blend_equation = blendParam[method][0]
        self.ctx.blend_func = blendParam[method][1:]

        prog = source.prog
        #prog['W'] = self.W; prog['H'] = self.H
        #prog['ox'] = coords[0]; prog['oy'] = coords[1]
        prog['SRC'] = 0
        prog['method'] = METHOD[method]
        prog['effect'] = effectApplied
        prog['effectArg'] = effectArg

        source.vao.render(mgl.TRIANGLES)


    def gamma(self, dest: mgl.Framebuffer):
        """Convert linear -> gamma"""
        return
##        self.prog.gamma(self.cq, (self.W*self.H//BLOCK_SIZE, 1), (BLOCK_SIZE, 1),
##                        dest, self.W, self.H,
##                        g_times_l=True)
