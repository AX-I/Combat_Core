// Perspective-correct trilinear texture drawing with smooth brightness
// Per-pixel lighting on one directional light
// 2 shadow maps

!shader_args

:Vertex float2 UV
:Vertex float3 I
:Vertex float3 N
:Vertex float3 PXYZ

__constant float3 *LInt,
__constant float3 *LDir,

const float mipBias,

:Texture ushort TR TG TB numMip

__global float *SD, const int wS, const float sScale,
__constant float3 *SV, __constant float *SPos,
__global float *SD2, const int wS2, const float sScale2,
__constant float3 *SV2, __constant float *SPos2,
!

!shader_setup
	vertUV1 /= z1; vertUV2 /= z2; vertUV3 /= z3;
	float2 slopeu1 = fabs((vertUV2-vertUV1) / (float)((y2-y1)*(y2-y1)+(x2-x1)*(x2-x1)));
	float2 slopeu2 = fabs((vertUV3-vertUV1) / (float)((y3-y1)*(y3-y1)+(x3-x1)*(x3-x1)));

	float dt = max(slopeu1.x, max(slopeu1.y, max(slopeu2.x, slopeu2.y)));
	float fmip = min((float)(numMip-1), fabs(log2(dt))/2 + mipBias);
	int mip = (int)fmip;
	fmip -= mip;
	int lenMip = 1 << mip;
	int lenMip2 = lenMip << 1;
	int startMip = 0;
	for (int i = 0; i < mip; i++) {
	  startMip += (1 << i) * (1 << i);
	}
    int startMip2 = startMip + (lenMip * lenMip);

	vertUV1 *= z1; vertUV2 *= z2; vertUV3 *= z3;

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

:DEPTH_COMPARE

:IF_DEPTH_TEST {

	F[wF * cy + ax] = tz;

	float2 texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz * lenMip;
	int tex1 = (int)texr12.x;
	texr12.x -= tex1;
	tex1 = abs(tex1) & (lenMip - 1);
	int tex2 = (int)texr12.y;
	texr12.y -= tex2;
	tex2 = abs(tex2) & (lenMip - 1);

	int tex = startMip + tex1 + lenMip*tex2;
	int tex10 = startMip + min(tex1+1, lenMip-1) + lenMip*tex2;
	int tex01 = startMip + tex1 + lenMip*min(tex2+1, lenMip-1);
	int tex11 = startMip + min(tex1+1, lenMip-1) + lenMip*min(tex2+1, lenMip-1);
	float texr1 = texr12.x; float texr2 = texr12.y;
	float texi1 = 1-texr1; float texi2 = 1-texr2;

	float outR = texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
					 texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11];
	float outG = texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
	    			 texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11];
	float outB = texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
	                 texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11];

	texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz * lenMip2;
	tex1 = (int)texr12.x;
	texr12.x -= tex1;
	tex1 = abs(tex1) & (lenMip2 - 1);
	tex2 = (int)texr12.y;
	texr12.y -= tex2;
	tex2 = abs(tex2) & (lenMip2 - 1);

	tex = startMip2 + tex1 + lenMip2*tex2;
	tex10 = startMip2 + min(tex1+1, lenMip2-1) + lenMip2*tex2;
	tex01 = startMip2 + tex1 + lenMip2*min(tex2+1, lenMip2-1);
	tex11 = startMip2 + min(tex1+1, lenMip2-1) + lenMip2*min(tex2+1, lenMip2-1);
	texr1 = texr12.x; texr2 = texr12.y;
	texi1 = 1-texr1; texi2 = 1-texr2;

	outR = (1-fmip) * outR + fmip * (texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
					 texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11]);
	outG = (1-fmip) * outG + fmip * (texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
					 texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11]);
	outB = (1-fmip) * outB + fmip * (texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
					 texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11]);


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
	shadow *= 0.25f;

		pos = pos + SP - SP2;
		depth = dot(pos, SVd2);
		sfx = (dot(pos, SVx2) * sScale2) + wS2;
		sfy = (dot(pos, SVy2) * -sScale2) + wS2;
		sx = sfx; sfx -= sx;
		sy = sfy; sfy -= sy;
		if ((sx >= 0) && (sx < 2*wS-2) &&
			(sy >= 0) && (sy < 2*wS-2)) {
			if (SD2[2*wS2 * sy + sx] < depth) shadow += (1-sfy)*(1-sfx);
			if (SD2[2*wS2 * sy + sx+1] < depth) shadow += (1-sfy)*sfx;
			if (SD2[2*wS2 * (sy+1) + sx] < depth) shadow += sfy*(1-sfx);
			if (SD2[2*wS2 * (sy+1) + sx+1] < depth) shadow += sfy*sfx;
		}

	float light = 1 - min(shadow, 1.f);

	float3 col = ((1-t)*currvertI2 + t*currvertI1) * tz;

	float3 norm = fast_normalize(((1-t)*currvertN2 + t*currvertN1) * tz);
	float3 dirCol = max(0.f, dot(norm, LDir[0])) * LInt[0];


	Ro[wF * cy + ax] = convert_ushort(outR * (light * dirCol.x + col.x));
	Go[wF * cy + ax] = convert_ushort(outG * (light * dirCol.y + col.y));
	Bo[wF * cy + ax] = convert_ushort(outB * (light * dirCol.z + col.z));
}
!