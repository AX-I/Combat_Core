// Perspective-correct bilinear texture drawing with smooth brightness
// Per-pixel lighting on one directional light
// Bigger PCF shadow filter radius

!shader_args

:Vertex float2 UV
:Vertex float3 I
:Vertex float3 N
:Vertex float3 PXYZ

__constant float3 *LInt,
__constant float3 *LDir,

:Texture ushort TR TG TB lenT

__global float *SD, const int wS, const float sScale,
__constant float3 *SV, __constant float *SPos,
!

!shader_setup
    float3 SP = (float3)(SPos[0], SPos[1], SPos[2]);
    float3 SVd = SV[0];
    float3 SVx = SV[1];
    float3 SVy = SV[2];
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
	float depth = dot(pos, SVd);
	float sfx = (dot(pos, SVx) * sScale) + wS + 0.5f;
	float sfy = (dot(pos, SVy) * -sScale) + wS + 0.5f;
	int sx = sfx; sfx -= sx;
    int sy = sfy; sfy -= sy;
	float shadow = 0;
	if ((sx >= 1) && (sx < 2*wS-2) &&
		(sy >= 1) && (sy < 2*wS-2)) {
		  if (SD[2*wS * (sy-1) + (sx-1)] < depth) shadow += 1*(1-sfy)*(1-sfx);
		  if (SD[2*wS * (sy-1) + sx] < depth) shadow += 1-sfy;
		  if (SD[2*wS * (sy-1) + (sx+1)] < depth) shadow += 1*(1-sfy)*sfx;
		  if (SD[2*wS * sy + (sx-1)] < depth) shadow += (1-sfx);
		  if (SD[2*wS * sy + sx] < depth) shadow += 1.f;
		  if (SD[2*wS * sy + (sx+1)] < depth) shadow += sfx;
		  if (SD[2*wS * (sy+1) + (sx-1)] < depth) shadow += 1*sfy*(1-sfx);
		  if (SD[2*wS * (sy+1) + sx] < depth) shadow += sfy;
		  if (SD[2*wS * (sy+1) + (sx+1)] < depth) shadow += 1*sfy*sfx;
	}
	float light = 1 - shadow / 4.f;
	float3 col = ((1-t)*currvertI2 + t*currvertI1) * tz;

	float3 norm = fast_normalize(((1-t)*currvertN2 + t*currvertN1) * tz);
	float3 dirCol = max(0.f, dot(norm, LDir[0])) * LInt[0];

	Ro[wF * cy + ax] = convert_ushort((texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
					   texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11]) * (light * dirCol.x + col.x));
	Go[wF * cy + ax] = convert_ushort((texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
					   texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11]) * (light * dirCol.y + col.y));
	Bo[wF * cy + ax] = convert_ushort((texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
					   texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11]) * (light * dirCol.z + col.z));
}
!