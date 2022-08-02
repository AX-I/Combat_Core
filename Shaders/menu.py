#define BS 128

#define BLEND_ALPHA 1
#define BLEND_ADD 2
#define BLEND_SCREEN 3
#define BLEND_REPLACE 4
#define BLEND_HARDLIGHT 5

#define EFFECT_FLIP 1
#define EFFECT_CROP 2
#define EFFECT_ROLL 3
#define EFFECT_ROT 4
#define EFFECT_MULT 5

#define cropHeight 3.f

float2 rot(float2 xy, float t) {
    float2 r1 = (float2)(cos(t),-sin(t));
    float2 r2 = (float2)(sin(t),cos(t));
    return (float2)(dot(r1,xy), dot(r2,xy));
}


__kernel void blend(
    __global ushort *DST, const int W, const int H,
    __global ushort *SRC, const float sh, const float sw, const float sc,
    const int ox, const int oy,
    const int method,
    const int effect,
    const float effectArg
) {
    int bi = get_group_id(0);
    int ti = get_local_id(0);

    int tx = (bi * BS + ti) % W;
    int ty = (bi * BS + ti) / W;

    int left = ox - sw/2;
    int right = left + sw;
    int up = oy - sh/2;
    int down = up + sh;

    float2 newxy;
    if (effect == EFFECT_ROT) {
        newxy = rot((float2)(tx-ox, ty-oy), effectArg) + (float2)(ox, oy);
    }

    float mult = 1.f;
    if (effect == EFFECT_MULT) {
        mult = effectArg;
    }


    if (((left <= tx) && (tx < right)) &&
        ((up <= ty) && (ty < down))) {

      int srcX = tx - left;
      int srcY = ty - up;
      for (int c = 0; c < 3; c++) {
        int samplecoord = sc * (srcY * sw + srcX) + c;

        if (effect == EFFECT_FLIP) {
            samplecoord = sc * (srcY * sw + (sw - 1 - srcX)) + c;
        }
        if (effect == EFFECT_CROP) {
            // crop vertically
            if ((oy - cropHeight/2 < ty) && (ty < oy + cropHeight/2)) {
                srcY = ty - (oy - cropHeight/2) + effectArg;
                samplecoord = sc * (srcY * sw + srcX) + c;
            } else break;
        }
        if (effect == EFFECT_ROLL) {
            samplecoord = sc * (srcY * sw + (int)fmod(srcX + effectArg, sw)) + c;
        }
        if (effect == EFFECT_ROT) {
            srcY = newxy.y - up;
            srcX = newxy.x - left;
            samplecoord = sc * (srcY * sw + srcX) + c;
            if (((0 > srcX) || (srcX >= sw)) ||
                ((0 > srcY) || (srcY >= sh))) break;
        }



        float pix = SRC[samplecoord] / 256.f;
        float pixdst = DST[3 * ((ty * W) + tx) + c] / 256.f;

        pix = pix * mult;

        if (method == BLEND_ALPHA) {
            float alpha = SRC[samplecoord - c + 3] / 256.f / 255.f;
            pix = pix * alpha + pixdst * (1-alpha);
        }
        if (method == BLEND_ADD) {
            pix += pixdst;
            pix = min(pix, 255.f);
        }
        if (method == BLEND_SCREEN) {
            pix = 255 - (255 - pixdst) * (255 - pix) / 255;
        }

        if (method == BLEND_HARDLIGHT) {
            float px = pix / 255.f;
            float nmask = min(px * 3, 1.f);
            float nmask2 = max(px * 3 - 1, 0.f) * 0.5;
            pix = pixdst * nmask * (1-nmask2);
            pix += 255 * nmask2;
        }

        if (method == BLEND_REPLACE) {
        }

        DST[3 * ((ty * W) + tx) + c] = pix * 256.f;
      }
    }
}

__kernel void gamma(__global ushort *DST, const int W, const int H) {
    int bi = get_group_id(0);
    int ti = get_local_id(0);
    int tc = bi * BS + ti;
    int tx = tc % W;
    int ty = tc / W;

    //float bias = 0.5f * ((tx & 1) ^ (ty & 1)) + 0.25f * (ty & 1);
    float bias = 0;

    DST[3*tc  ] = sqrt(DST[3*tc  ] + bias);
    DST[3*tc+1] = sqrt(DST[3*tc+1] + bias);
    DST[3*tc+2] = sqrt(DST[3*tc+2] + bias);
}


