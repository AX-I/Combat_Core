// Screen Space Reflection
// For AXI Combat

#define REFL_STEP 2
#define REFL_LENGTH 600
#define REFL_DEPTH 2.f
#define REFL_VSIZE 2.f
#define REFL_DBIAS 0.5f
#define REFL_FADE 60
#define maxattn 0.1f
#define ABSORB 0.3f

!shader_args

:Vertex float2 UV
:Vertex float3 I
:Vertex float3 N
:Vertex float3 PXYZ

    __constant float *Vpos, __constant float3 *VV,
    const float sScale,

:Texture ushort TR TG TB lenT
:Texture ushort RR RG RB dimR

!

!shader_setup
    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    float3 SVd = VV[0];
    float3 SVx = VV[1];
    float3 SVy = VV[2];
!

!shader_core

:DEPTH_COMPARE

:IF_DEPTH_TEST {
    float3 pos = ((1-t)*currvertPXYZ2 + t*currvertPXYZ1) * tz;
    float3 norm = fast_normalize(((1-t)*currvertN2 + t*currvertN1) * tz);

    float2 texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz * lenT;
	int tex1 = (int)texr12.x;
	texr12.x -= tex1;
	tex1 = abs(tex1) & (lenT - 1);
	int tex2 = (int)texr12.y;
	texr12.y -= tex2;
	tex2 = abs(tex2) & (lenT - 1);

    int tex = tex1 + lenT*tex2;
    float fr = 1 - max(0.f, dot(normalize(pos - vp), norm)) * maxattn;
    fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr;

    float scatter = exp(ABSORB * (tz - F[wF * cy + ax]));
    // is actually transmittance

    float tsr = scatter * Ro[wF*cy+ax] + (1-scatter) * TR[tex];
    float tsg = scatter * Go[wF*cy+ax] + (1-scatter) * TG[tex];
    float tsb = scatter * Bo[wF*cy+ax] + (1-scatter) * TB[tex];

    float3 a = pos - vp;
    float nd = dot(a, norm);
    float3 refl = fast_normalize(a - 2 * nd * norm) * REFL_VSIZE;

    int maxRLen = REFL_LENGTH;
	if (dot(refl, SVd) < -0.1f) maxRLen = 1;
    if (refl.y < 0) maxRLen = 1;

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
    int2 ssr_loc = (int2)0;

    float sy = cy;
    float sx = ax;
    float sz = 1.f/tz;
    float sd = REFL_DEPTH;
    int rn = 0;

    // Raymarch
    for (rn = 0;
         (hit == 0) && (rn < maxRLen) && (sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF) && (sz > 0);
         rn += vx) {
        if ((F[wF * (int)sy + (int)sx] < 1.f/sz) &&
            (F[wF * (int)sy + (int)sx] > 1.f/sz - sd)) {

            ssr_loc = (int2)(sx, sy);
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

    float cs = (RR[rex] + RG[rex] + RB[rex] >= 3*65535) ? 16 : 1;

    if (hit == 1) {
        ssr_out.x = Ro[wF * ssr_loc.y + ssr_loc.x];
        ssr_out.y = Go[wF * ssr_loc.y + ssr_loc.x];
        ssr_out.z = Bo[wF * ssr_loc.y + ssr_loc.x];

        Ro[wF * cy + ax] = (1-fr) * tsr + fr * (fade * ssr_out.x + (1-fade) * RR[rex] * cs);
        Go[wF * cy + ax] = (1-fr) * tsg + fr * (fade * ssr_out.y + (1-fade) * RG[rex] * cs);
        Bo[wF * cy + ax] = (1-fr) * tsb + fr * (fade * ssr_out.z + (1-fade) * RB[rex] * cs);
        F[wF * cy + ax] = tz;
    }
    else {
		Ro[wF * cy + ax] = (1-fr) * tsr + fr * RR[rex] * cs;
        Go[wF * cy + ax] = (1-fr) * tsg + fr * RG[rex] * cs;
        Bo[wF * cy + ax] = (1-fr) * tsb + fr * RB[rex] * cs;
        F[wF * cy + ax] = tz;
    }
}

!