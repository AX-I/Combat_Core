// Perspective-correct bilinear texture drawing with smooth brightness
// Per-pixel lighting on one directional light

!shader_args

:Vertex float2 UV
:Vertex float3 I
:Vertex float3 N
:Vertex float3 PXYZ

__constant float3 *LInt,
__constant float3 *LDir,

:Texture ushort TR TG TB lenT

!

!shader_setup
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

	float light = 1;
	float3 col = ((1-t)*currvertI2 + t*currvertI1) * tz;

	float3 norm = fast_normalize(((1-t)*currvertN2 + t*currvertN1) * tz);
	float3 dirCol = max(0.f, dot(norm, LDir[0])) * LInt[0];

	Ro[wF * cy + ax] = convert_ushort((texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
					   texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11]) * (light * (dirCol.x + col.x) + (1-light) * col.x));
	Go[wF * cy + ax] = convert_ushort((texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
					   texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11]) * (light * (dirCol.y + col.y) + (1-light) * col.y));
	Bo[wF * cy + ax] = convert_ushort((texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
					   texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11]) * (light * (dirCol.z + col.z) + (1-light) * col.z));
}
!