#version 330

#define BLEND_ALPHA 1
#define BLEND_ADD 2
#define BLEND_SCREEN 3
#define BLEND_REPLACE 4
#define BLEND_HARDLIGHT 5

#define EFFECT_FLIP 1
#define EFFECT_CROP 2
#define EFFECT_ROLL 3
//#define EFFECT_ROT 4
#define EFFECT_MULT 5
#define EFFECT_ROLLFADEY 6

#define cropHeight 3.f

//const sampler_t smp = CLK_NORMALIZED_COORDS_FALSE | CLK_ADDRESS_CLAMP | CLK_FILTER_LINEAR;

in vec3 in_vert;
in vec2 v_UV;

uniform sampler2D SRC;
uniform float sw;
uniform float sh;
uniform int method;
uniform int effect;
uniform float effectArg;

out vec4 DST;


void main() {
    float srcX = v_UV.x;
    float srcY = v_UV.y;
    vec2 samplecoord = v_UV.xy;

    float mult = 1.f;
    if (effect == EFFECT_MULT) {
        mult = effectArg;
    }

    if (effect == EFFECT_FLIP) {
        samplecoord.x = 1 - srcX;
    }
    if (effect == EFFECT_CROP) {
        // crop vertically
        float ty = (srcY-0.5) * sh;
        if ((ty > -cropHeight/2) && (ty < cropHeight/2)) {
          samplecoord.y -= effectArg/sh/2;
        } else discard;
    }
    if (effect == EFFECT_ROLL) {
        samplecoord.x = fract(abs(srcX + effectArg/sw));
    }

    if (effect == EFFECT_ROLLFADEY) {
      samplecoord.y = fract(abs(srcY + effectArg/sh));
      mult = pow(1 - pow(abs(srcY - 0.5) / 0.5, 2), 2);
    }

    vec4 pix = texture(SRC, samplecoord).rgba;
    pix = pix * mult;

    if (method == BLEND_ALPHA) {}
    if (method == BLEND_ADD) {}
    if (method == BLEND_SCREEN) {
        pix = 1 - pix;
    }
    if (method == BLEND_HARDLIGHT) {
        vec3 px = pix.rgb;
        vec3 nmask = min(px * 3, 1.f);
        vec3 nmask2 = max(px * 3 - 1, 0.f) * 0.5f;

        pix.a = nmask.r * (1-nmask2.r);
        pix.rgb = nmask2;
    }
    if (method == BLEND_REPLACE) {}

    DST = pix;// * 0.0001 + vec4(v_UV.x, v_UV.y, 0, 1);
}

