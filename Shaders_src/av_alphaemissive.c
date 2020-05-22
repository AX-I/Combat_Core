// Perspective-correct bilinear texture drawing with smooth brightness and PCF shadow map
// Alpha test
// Per-pixel lighting on one directional light

#define shDist 2
#define EMPOW 6.f

!shader_args
    __global float *SD, const int wS, const float sScale,
    __constant float3 *SV, __constant float *SPos,
    __global float *SD2, const int wS2, const float sScale2,
    __constant float3 *SV2, __constant float *SPos2,
    __global bool *TA, __global bool *TE,
!

!shader_setup
    float3 SP = (float3)(SPos[0], SPos[1], SPos[2]);
    float3 SVd = SV[0];
    float3 SVx = SV[1];
    float3 SVy = SV[2];

    float3 SP2 = (float3)(SPos2[0], SPos2[1], SPos2[2]);
    float3 SVd2 = SV2[0];
    float3 SVx2 = SV2[1];
    float3 SVy2 = SV2[2];
!

!shader_core

if (F[wF * cy + ax] > tz) {

    float texr1 = ((1-t)*cu2 + t*cu1) * tz * lenT;
    int tex1 = (int)texr1;
    texr1 -= tex1;
    tex1 = abs(tex1) & (lenT - 1);
    float texr2 = lenT * ((1-t)*cv2 + t*cv1) * tz;
    int tex2 = (int)texr2;
    texr2 -= tex2;
    tex2 = abs(tex2) & (lenT - 1);

    int tex = tex1 + lenT*tex2;
    int tex10 = min(tex1+1, lenT-1) + lenT*tex2;
    int tex01 = tex1 + lenT*min(tex2+1, lenT-1);
    int tex11 = min(tex1+1, lenT-1) + lenT*min(tex2+1, lenT-1);
    float texi1 = 1-texr1;
    float texi2 = 1-texr2;
    float ca = texi1*texi2*(float)TA[tex] + texr1*texi2*(float)TA[tex10] +
               texi1*texr2*(float)TA[tex01] + texr1*texr2*(float)TA[tex11];

    float light;
    if (useShadow) {
        float3 pos = ((1-t)*cp2 + t*cp1) * tz - SP;
        float depth = dot(pos, SVd);
        int sx = (int)(dot(pos, SVx) * sScale) + wS;
        int sy = (int)(dot(pos, SVy) * -sScale) + wS;
        int shadow = 0;
        if ((sx >= shDist) && (sx < 2*wS-shDist) &&
            (sy >= shDist) && (sy < 2*wS-shDist)) {
          if (SD[2*wS * sy + sx] < depth) shadow += 1;
          if (SD[2*wS * (sy+shDist) + sx] < depth) shadow += 1;
          if (SD[2*wS * (sy-shDist) + sx] < depth) shadow += 1;
          if (SD[2*wS * sy + (sx+shDist)] < depth) shadow += 1;
          if (SD[2*wS * sy + (sx-shDist)] < depth) shadow += 1;
        }
        pos = ((1-t)*cp2 + t*cp1) * tz - SP2;
        depth = dot(pos, SVd2);
        sx = (int)(dot(pos, SVx2) * sScale2) + wS2;
        sy = (int)(dot(pos, SVy2) * -sScale2) + wS2;
        if ((sx >= shDist) && (sx < 2*wS2-shDist) &&
            (sy >= shDist) && (sy < 2*wS2-shDist)) {
          if (SD2[2*wS2 * sy + sx] < depth) shadow += 1;
          if (SD2[2*wS2 * (sy+shDist) + sx] < depth) shadow += 1;
          if (SD2[2*wS2 * (sy-shDist) + sx] < depth) shadow += 1;
          if (SD2[2*wS2 * sy + (sx+shDist)] < depth) shadow += 1;
          if (SD2[2*wS2 * sy + (sx-shDist)] < depth) shadow += 1;
        }
        shadow = min(5, shadow);
        light = shadow * ambLight + (5-shadow);
        light *= 0.2f;
    } else light = 1;

    float3 col =  ((1-t)*cl2 + t*cl1);
    if (TE[tex]) col = (float3)EMPOW;

    float3 norm = fast_normalize(((1-t)*cn2 + t*cn1) * tz);
    float3 dirCol = max(0.f, dot(norm, LDir[0])) * LInt[0];

    if (ca > 0.5) {
        F[wF * cy + ax] = tz;

        Ro[wF * cy + ax] = convert_ushort_sat((texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
                           texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11]) * (light * dirCol.x + col.x));
        Go[wF * cy + ax] = convert_ushort_sat((texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
                           texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11]) * (light * dirCol.y + col.y));
        Bo[wF * cy + ax] = convert_ushort_sat((texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
                           texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11]) * (light * dirCol.z + col.z));
    }
}

!