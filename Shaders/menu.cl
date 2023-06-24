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
#define EFFECT_ROLLFADEY 6

#define cropHeight 3.f

float2 rot(float2 xy, float t) {
    float2 r1 = (float2)(cos(t),-sin(t));
    float2 r2 = (float2)(sin(t),cos(t));
    return (float2)(dot(r1,xy), dot(r2,xy));
}

const sampler_t smp = CLK_NORMALIZED_COORDS_FALSE | CLK_ADDRESS_CLAMP | CLK_FILTER_LINEAR;

__kernel void blend(
    __global ushort *DST, const int W, const int H,
    __read_only image2d_t SRC,
    const int sh, const int sw, const int sc,
    const float ox, const float oy,
    const int method,
    const int effect,
    const float effectArg
) {
    int bi = get_group_id(0);
    int ti = get_local_id(0);

    int tx = (bi * BS + ti) % W;
    int ty = (bi * BS + ti) / W;

    float left = ox - sw/2;
    float right = left + sw;
    float up = oy - sh/2;
    float down = up + sh;

    float2 newxy;
    if (effect == EFFECT_ROT) {
        newxy = rot((float2)(tx-ox, ty-oy), effectArg) + (float2)(ox, oy);
    }

    float mult = 1.f;
    if (effect == EFFECT_MULT) {
        mult = effectArg;
    }

    if (((left-0.5f <= tx) && (tx < right+0.5f)) &&
        ((up-0.5f <= ty) && (ty < down+0.5f))) {

      float srcX = tx - left;
      float srcY = ty - up;

      float2 samplecoord = (float2)(srcX, srcY);

      if (effect == EFFECT_FLIP) {
          samplecoord.x = sw - 1 - srcX;
      }
      if (effect == EFFECT_CROP) {
          // crop vertically
          if ((oy - cropHeight/2 < ty) && (ty < oy + cropHeight/2)) {
              srcY = ty - (oy - cropHeight/2) + effectArg;
              samplecoord.y = srcY;
          } else return;
      }
      if (effect == EFFECT_ROLL) {
          samplecoord.x = fmod(fabs(srcX + effectArg), sw);
      }
      if (effect == EFFECT_ROT) {
          srcY = newxy.y - up;
          srcX = newxy.x - left;
          samplecoord = (float2)(srcX, srcY);
          if (((0 > srcX) || (srcX >= sw)) ||
              ((0 > srcY) || (srcY >= sh))) return;
      }
      if (effect == EFFECT_ROLLFADEY) {
        samplecoord.y = fmod(fabs(srcY + effectArg), sh);
        mult = pown(1 - pown(fabs(srcY - sh/2) / (sh/2), 2), 2);
      }

      float3 pix = read_imagef(SRC, smp, samplecoord).xyz;
      pix = pix * mult;

      float3 pixdst = (float3)(DST[3 * ((ty * W) + tx)],
                               DST[3 * ((ty * W) + tx)+1],
                               DST[3 * ((ty * W) + tx)+2]) / 256.f;

      if (method == BLEND_ALPHA) {
          float alpha = read_imagef(SRC, smp, samplecoord).w / 255.f;
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
          float3 px = pix / 255.f;
          float3 nmask = min(px * 3, 1.f);
          float3 nmask2 = max(px * 3 - 1, 0.f) * 0.5f;
          pix = pixdst * nmask * (1-nmask2);
          pix += 255 * nmask2;
      }

      if (method == BLEND_REPLACE) {
      }
      pix *= 256.f;
      DST[3 * ((ty * W) + tx) + 0] = pix.x;
      DST[3 * ((ty * W) + tx) + 1] = pix.y;
      DST[3 * ((ty * W) + tx) + 2] = pix.z;
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
