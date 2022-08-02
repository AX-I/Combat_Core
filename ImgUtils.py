import numpy as np
from PIL import Image, ImageDraw, ImageFilter


class NPTextDraw:
    def drawTextNP(self, fr: np.array, dText: str, dFill: tuple, dFont,
                   coords: tuple, fOpacity=1,
                   blur=2, bFill=(0,0,0), method='box') -> None:
        """Draw text onto fr
        coords => offset from center (y, x)
        """
        coords = (int(coords[0]), int(coords[1]))

        if dText not in self.UItexts:
            b = self.imgText(dText, dFill, dFont, blur, bFill, method)
            self.UItexts[dText] = b
        else:
            b = self.UItexts[dText]

        s = b.shape
        opacity = np.expand_dims(b[:,:,3], 2) / 255. * fOpacity

        y1, y2 = self.H2 - (s[0]//2) + coords[0], self.H2 + (s[0]//2) + coords[0]
        x1, x2 = self.W2 - (s[1]//2) + coords[1], self.W2 + (s[1]//2) + coords[1]

        fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * (1-opacity) + \
                           b[:,:,:3] * opacity


class NPCanvas:

    def imgText(self, dText: str, dFill: tuple, dFont,
                blur=4, bFill=(0,0,0), method='box') -> np.array:
        """returns np array of text
        method is box or gauss
        """
        pad = 8 + blur * 12

        s = self.textSize.textsize(dText, font=dFont)
        a = Image.new("RGBA", (2*(s[0]//2)+pad, 2*(s[1]//2)+pad),
                      color=(*bFill,0))
        for ix in range(blur):
            d = ImageDraw.Draw(a)
            d.text((pad//2,pad//2), dText, fill=(*bFill,255), font=dFont, align="center")
            if method == 'box':
                a = a.filter(ImageFilter.BoxBlur(7))
            elif method == 'gauss':
                a = a.filter(ImageFilter.GaussianBlur(5))
        d = ImageDraw.Draw(a)
        d.text((pad//2,pad//2), dText, fill=dFill, font=dFont, align="center")
        return np.array(a)

    def drawText(self, fr: np.array, dText: str, dFill: tuple, dFont,
                 coords: tuple, fOpacity=1,
                 blur=2, bFill=(0,0,0), method='box') -> None:
        """Draw text onto fr
        coords => offset from center (y, x)
        """
        coords = (int(coords[0]), int(coords[1]))

        if dText not in self.UItexts:
            b = self.imgText(dText, dFill, dFont, blur, bFill, method)
            self.UItexts[dText] = b
        else:
            b = self.UItexts[dText]

        s = b.shape
        opacity = np.expand_dims(b[:,:,3], 2) / 255. * fOpacity

        y1, y2 = self.H2 - (s[0]//2) + coords[0], self.H2 + (s[0]//2) + coords[0]
        x1, x2 = self.W2 - (s[1]//2) + coords[1], self.W2 + (s[1]//2) + coords[1]

        fr[y1:y2, x1:x2] = fr[y1:y2, x1:x2] * (1-opacity) + \
                           b[:,:,:3] * opacity

    def blend(self, dest: np.array, source: np.array,
              coords: tuple, method='alpha') -> None:
        """Blend image source onto dest, centered at coords (x, y)
        Preconditions:
            - method in {'alpha', 'add', 'screen', 'replace'}
        """
        left = int(coords[0] - (source.shape[1]//2))
        right = left + source.shape[1]
        up = int(coords[1] - (source.shape[0]//2))
        down = up + source.shape[0]

        src_up = 0
        src_down = source.shape[0]
        src_left = 0
        src_right = source.shape[1]

        # Clip to bounds
        if up < 0:
            src_up -= up
            up = 0
        if left < 0:
            src_left -= left
            left = 0
        if down > self.H:
            src_down -= down - self.H
            down = self.H
        if right > self.W:
            src_right -= right - self.W
            right = self.W

        source = source[src_up:src_down, src_left:src_right]

        if method == 'alpha':
            alpha = np.expand_dims(source[:,:,3], -1) / 255.
            np.minimum(alpha, 1, out=alpha)
            dest[up:down, left:right] *= 1 - alpha
            dest[up:down, left:right] += source[:,:,:3] * alpha

        if method == 'add':
            p = np.clip(source.astype('uint16') + dest[up:down, left:right], 0, 255)
            dest[up:down, left:right] = p.astype('uint8')

        if method == 'screen':
            dest[up:down, left:right] = 255 - (255 - dest[up:down, left:right]) \
                                        * (255 - source) / 255

        if method == 'replace':
            dest[up:down, left:right] = source
