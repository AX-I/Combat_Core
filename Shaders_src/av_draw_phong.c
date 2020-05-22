// Perspective-correct bilinear texture drawing with smooth brightness
// Per-pixel lighting on one directional light

!shader_args

:Vertex float2 UV
:Vertex float3 I
:Vertex float3 N
:Vertex float3 PXYZ

    __constant float *Vpos, __constant float3 *VV,

__constant float3 *LInt,
__constant float3 *LDir,

:Texture ushort TR TG TB lenT

__global float *SD, const int wS, const float sScale,
__constant float3 *SV, __constant float *SPos,
!

!shader_setup
    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    float3 SVd = VV[0];
    float3 SVx = VV[1];
    float3 SVy = VV[2];

    float3 SP = (float3)(SPos[0], SPos[1], SPos[2]);
    float3 SHd = SV[0];
    float3 SHx = SV[1];
    float3 SHy = SV[2];
!

!shader_core

:DEPTH_COMPARE

:IF_DEPTH_TEST {

	F[wF * cy + ax] = tz;

	float2 texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz * lenT;
	int tex1 = (int)texr12.x;
	texr12.x -= tex1;
	tex1 = abs(tex1) & (lenT - 1);
	int tex2 = (int)texr12.y;
	texr12.y -= tex2;
	tex2 = abs(tex2) & (lenT - 1);

	int tex = tex1 + lenT*tex2;
	int tex10 = min(tex1+1, lenT-1) + lenT*tex2;
	int tex01 = tex1 + lenT*min(tex2+1, lenT-1);
	int tex11 = min(tex1+1, lenT-1) + lenT*min(tex2+1, lenT-1);
	float texr1 = texr12.x; float texr2 = texr12.y;
	float texi1 = 1-texr1; float texi2 = 1-texr2;

	float3 pos = ((1-t)*currvertPXYZ2 + t*currvertPXYZ1) * tz - SP;
	float depth = dot(pos, SHd);
	float sfx = (dot(pos, SHx) * sScale) + wS;
	float sfy = (dot(pos, SHy) * -sScale) + wS;
	int sx = sfx; sfx -= sx;
	int sy = sfy; sfy -= sy;
	float shadow = 0;
	if ((sx >= 0) && (sx < 2*wS-1) &&
		(sy >= 0) && (sy < 2*wS-1)) {
		  if (SD[2*wS * sy + sx] < depth) shadow += (1-sfy)*(1-sfx);
		  if (SD[2*wS * (sy+1) + sx] < depth) shadow += sfy*(1-sfx);
		  if (SD[2*wS * sy + (sx+1)] < depth) shadow += (1-sfy)*sfx;
		  if (SD[2*wS * (sy+1) + (sx+1)] < depth) shadow += sfy*sfx;
	}
	float light = 1 - shadow;
	float3 col = ((1-t)*currvertI2 + t*currvertI1) * tz;

	pos = ((1-t)*currvertPXYZ2 + t*currvertPXYZ1) * tz;
	float3 norm = fast_normalize(((1-t)*currvertN2 + t*currvertN1) * tz);

	float3 a = pos - vp;
	float nd = dot(a, norm);
    float3 refl = fast_normalize(a - 2 * nd * norm);
    float theta = max(0.f, dot(refl, -LDir[0]));

	float3 dirCol = max(0.f, dot(norm, LDir[0])) * LInt[0];

	int specPow = 64;
	float sunPow = 1.25f;
	float spec = pown(theta, specPow) * 256 * light * sunPow;
	spec *= specPow;

	Ro[wF * cy + ax] = convert_ushort(spec + TR[tex] * (light * dirCol.x + col.x));
	Go[wF * cy + ax] = convert_ushort(spec + TG[tex] * (light * dirCol.y + col.y));
	Bo[wF * cy + ax] = convert_ushort(spec + TB[tex] * (light * dirCol.z + col.z));
}
!