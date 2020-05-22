// Screen Space Reflection
// With cubemap fallback
// Perspective-correct
// Fade out
// Metallic

#define REFL_STEP 2
#define REFL_LENGTH 800
#define REFL_DEPTH 2.f
#define REFL_VSIZE 2.f
#define REFL_DBIAS 0.5f
#define REFL_FADE 80
#define maxattn 0.1f
#define ABSORB 0.4f


//__global float2 *UV,
//__global float3 *I,
//__global float3 *N,
//__global float3 *PXYZ,
//__constant float3 *LInt, __constant float3 *LDir,

!shader_args
    __constant float *Vpos, __constant float3 *VV,
    const float sScale,
    __global ushort *RR, __global ushort *RG, __global ushort *RB, const int dimR,
!

!shader_setup
    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    float3 SVd = VV[0];
    float3 SVx = VV[1];
    float3 SVy = VV[2];
!

!shader_core

if (F[wF * cy + ax] > tz) {

    float3 pos = ((1-t)*cp2 + t*cp1) * tz;
    float3 norm = fast_normalize(((1-t)*cn2 + t*cn1) * tz);

    float texr1 = ((1-t)*cu2 + t*cu1) * tz * lenT;
    int tex1 = (int)texr1;
    texr1 -= tex1;
    tex1 = abs(tex1) & (lenT - 1);
    float texr2 = lenT * ((1-t)*cv2 + t*cv1) * tz;
    int tex2 = (int)texr2;
    texr2 -= tex2;
    tex2 = abs(tex2) & (lenT - 1);

    int tex = tex1 + lenT*tex2;
    float fr = 1;//float fr = 1 - max(0.f, dot(normalize(pos - vp), norm)) * maxattn;
    //fr *= fr;// fr *= fr; fr *= fr; fr *= fr;// fr *= fr; fr *= fr;

    float scatter = exp(ABSORB * (tz - F[wF * cy + ax]));
    // is actually transmittance

    float tsr = scatter * Ro[wF*cy+ax] + (1-scatter) * TR[tex];
    float tsg = scatter * Go[wF*cy+ax] + (1-scatter) * TG[tex];
    float tsb = scatter * Bo[wF*cy+ax] + (1-scatter) * TB[tex];

    float3 a = pos - vp;
    float nd = dot(a, norm);
    float3 refl = fast_normalize(a - 2 * nd * norm) * REFL_VSIZE;
    float2 rxy = (float2)(ax, cy);
    float rpz = dot(a + refl, SVd);
    float2 rp = (float2)(dot(a + refl, SVx) * -sScale / rpz + wF/2,
                         dot(a + refl, SVy) * sScale / rpz + hF/2);

    int hit = 0;

    float dt = max(fabs(rp.x - rxy.x), fabs(rp.y - rxy.y));

    int vx = REFL_STEP;

    float slopex = (rp.x - rxy.x) / dt * vx;
    float slopey = (rp.y - rxy.y) / dt * vx;
    float slopez = (1.f/rpz - 1.f/tz) / dt * vx;

    float3 ssr_out = 0.f;

    float sy = cy;
    float sx = ax;
    float sz = 1.f/tz;
    float sd = REFL_DEPTH;
    int rn;
    for (rn = 0;
         (hit == 0) && (rn < REFL_LENGTH) && (sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF) && (sz > 0);
         rn += vx) {
        if ((F[wF * (int)sy + (int)sx] < 1.f/sz) &&
            (F[wF * (int)sy + (int)sx] > 1.f/sz - sd)) {

            ssr_out.x = Ro[wF * (int)sy + (int)sx];
            ssr_out.y = Go[wF * (int)sy + (int)sx];
            ssr_out.z = Bo[wF * (int)sy + (int)sx];
            hit = 1;
        }
        sx += slopex;
        sy += slopey;
        sz += slopez;
        sd = fabs(1.f/sz - 1.f/(sz - slopez)) + REFL_DBIAS;
    }

    int face;
    float m = max(fabs(refl.x), max(fabs(refl.y), fabs(refl.z)));
    if (m == fabs(refl.x)) {
      face = (refl.x > 0) ? 0 : 3;
      rxy = refl.zy / refl.x;
    }
    if (m == fabs(refl.y)) {
      face = (refl.y > 0) ? 1 : 4;
      rxy = refl.xz / refl.y;
    }
    if (m == fabs(refl.z)) {
      face = (refl.z > 0) ? 2 : 5;
      rxy = refl.yx / refl.z;
    }
    rxy = min((rxy + 1) * dimR, (float2)(dimR*2-1));

    int lenR = 2*dimR;
    int side = face+1;

    int rex1 = (int)rxy.x + face*lenR;
    int rex2 = (int)rxy.y;
    int rex = rex1 + 6*lenR*rex2;

    float fade = min(1.f, (float)(REFL_LENGTH - rn) / (float)REFL_FADE);

    if (hit == 1) {
        Ro[wF * cy + ax] = (1-fr) * tsr + fr * (fade * ssr_out.x + (1-fade) * RR[rex]) * TR[tex]/8192.f;
        Go[wF * cy + ax] = (1-fr) * tsg + fr * (fade * ssr_out.y + (1-fade) * RG[rex]) * TG[tex]/8192.f;
        Bo[wF * cy + ax] = (1-fr) * tsb + fr * (fade * ssr_out.z + (1-fade) * RB[rex]) * TB[tex]/8192.f;
        F[wF * cy + ax] = tz;
    }
    else {
        Ro[wF * cy + ax] = (1-fr) * tsr + fr * RR[rex] * TR[tex]/8192.f;
        Go[wF * cy + ax] = (1-fr) * tsg + fr * RG[rex] * TG[tex]/8192.f;
        Bo[wF * cy + ax] = (1-fr) * tsb + fr * RB[rex] * TB[tex]/8192.f;
        F[wF * cy + ax] = tz;
    }
}

!