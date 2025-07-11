import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import moderngl as mgl

VS = open('PipeGL/trisetup_menu.c').read()
FS = open('ShadersGL/menu.c').read()

x = np.array([-1, -1, 1, 1, -1, 1])
y = np.array([1, -1, 1, 1, -1, -1])
z = np.ones(6)*-0.9999
u = (x+1)/2
v = (y+1)/2
TRI = np.dstack([x,y,z,u,v])

METHOD = {'alpha':1, 'add':2, 'screen':3, 'replace':4, 'hard light':5}
EFFECT = {None:0, 'flip':1, 'crop':2, 'roll':3, 'rot':4, 'mult':5, 'fadey':6}

blendParam = {'alpha':(mgl.FUNC_ADD, mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA),
              'add':(mgl.FUNC_ADD, mgl.ONE, mgl.ONE),
              'screen':(mgl.FUNC_REVERSE_SUBTRACT, mgl.ONE_MINUS_DST_COLOR, mgl.ONE),
              'replace':(mgl.FUNC_ADD, mgl.ONE, mgl.ZERO),
              'hard light':(mgl.FUNC_ADD, mgl.ONE, mgl.SRC_ALPHA)}

class GLObject:
    name: str
    buf: mgl.Texture
    shape: np.array

    prog: mgl.Program
    vbo: mgl.Buffer
    vao: mgl.VertexArray

    def __init__(self, ctx, cq, name: str, x: np.array, shape: tuple = None):
        x = (x/255).astype('float16')

        buf = ctx.texture(x.shape[1::-1], x.shape[2], x, dtype='f2')
        buf.repeat_x = False
        buf.repeat_y = False

        self.name = name
        self.buf = buf
        if shape is None: shape = x.shape
        else: shape = shape[::-1]
        self.shape = np.array(shape, dtype='int32')
        self.filters = {}

        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)

        v = TRI
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

        self.blend(fr, source, coords[::-1], 'alpha')


    def blend(self, dest: mgl.Framebuffer, source: GLObject,
              coords: tuple, method='alpha',
              effect=None, effectArg=0) -> None:
        """Blend image source onto dest, centered at coords (x, y)
        Preconditions:
            - method in {'alpha', 'add', 'screen',
                         'replace', 'hard light'}
            - effect in {None, 'flip', 'crop', 'roll', 'rot', 'mult', 'fadey'}
        """
        effectApplied = EFFECT[effect]

        if 'flip' in source.filters:
            effectApplied = EFFECT['flip']
            del source.filters['flip']
        if 'crop' in source.filters:
            effectApplied = EFFECT['crop']
            effectArg = source.filters['crop']
            del source.filters['crop']

        source.buf.use(location=0)
        dest.use()

        self.ctx.blend_equation = blendParam[method][0]
        self.ctx.blend_func = blendParam[method][1:]

        prog = source.prog
        prog['W'] = self.W; prog['H'] = self.H
        prog['ox'], prog['oy'] = coords
        prog['sw'], prog['sh'] = source.shape[1::-1]
        prog['SRC'] = 0
        prog['method'] = METHOD[method]
        prog['effect'] = effectApplied
        prog['effectArg'] = effectArg

        source.vao.render(mgl.TRIANGLES)


    def setupPost(self):
        trisetup2d = open('PipeGL/trisetup2d.c').read()
        gamma = open('ShadersGL/Post/gamma.c').read()
        gamma = gamma.replace('#define CHROM', '').replace('#define VIGNETTE', '')
        self.post_prog = self.ctx.program(vertex_shader=trisetup2d, fragment_shader=gamma)

        self.post_vbo = self.ctx.buffer(TRI[:,:,:3].astype('float32').tobytes())
        self.post_vao = self.ctx.vertex_array(self.post_prog, self.post_vbo, 'in_vert')
        self.post_prog['tex1'] = 0

        self.post_prog['width'] = self.W
        self.post_prog['height'] = self.H

        self.post_prog['exposure'] = 1/6.67
        self.post_prog['tonemap'] = 0
        self.post_prog['blackPoint'] = 0

    def gamma(self, dest: mgl.Framebuffer):
        """Convert linear -> gamma"""
        self.ctx.blend_equation = mgl.FUNC_ADD
        self.ctx.blend_func = mgl.ONE, mgl.ZERO
        self.FB.use(location=0)

        self.postBuf.use()

        self.post_vao.render(mgl.TRIANGLES)
