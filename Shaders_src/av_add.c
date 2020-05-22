
!shader_args

float emPow,
:Vertex float2 UV
:Texture ushort TR TG TB lenT

!

!shader_setup
!

!shader_core

:DEPTH_COMPARE

:IF_DEPTH_TEST {


    float2 texr12 = ((1-t)*currvertUV2 + t*currvertUV1) * tz * lenT;
	int tex1 = (int)texr12.x;
	texr12.x -= tex1;
	tex1 = abs(tex1) & (lenT - 1);
	int tex2 = (int)texr12.y;
	texr12.y -= tex2;
	tex2 = abs(tex2) & (lenT - 1);

    int tex = tex1 + lenT*tex2;

    Ro[wF * cy + ax] = convert_ushort_sat(Ro[wF * cy + ax] + TR[tex] * emPow);
    Go[wF * cy + ax] = convert_ushort_sat(Go[wF * cy + ax] + TG[tex] * emPow);
    Bo[wF * cy + ax] = convert_ushort_sat(Bo[wF * cy + ax] + TB[tex] * emPow);

}

!