// Early skydraw

!shader_args

:Vertex float2 UV
:Texture ushort TR TG TB lT

!

!shader_setup

int hT = lT / 6;

!

!shader_core

:IF_DEPTH_TEST {
	float2 texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz;

	float texr1 = texr12.x * lT;
	int tex1 = (int)texr1;
	texr1 -= tex1;
	tex1 = max(0, min(tex1, lT-1));

	float texr2 = texr12.y * hT;
	int tex2 = (int)texr2;
	texr2 -= tex2;
	tex2 = max(0, min(tex2, hT-1));

	int tex = tex1 + lT*tex2;
	int tex10 = min(tex1+1, lT-1) + lT*tex2;
	int tex01 = tex1 + lT*min(tex2+1, hT-1);
	int tex11 = min(tex1+1, lT-1) + lT*min(tex2+1, hT-1);
	float texi1 = 1-texr1;
	float texi2 = 1-texr2;

	Ro[wF * cy + ax] = convert_ushort(texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
					   texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11]);
	Go[wF * cy + ax] = convert_ushort(texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
					   texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11]);
	Bo[wF * cy + ax] = convert_ushort(texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
					   texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11]);
}
!