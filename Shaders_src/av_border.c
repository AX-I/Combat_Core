
!shader_args

float emPow,
__constant float *Vpos, __constant float3 *VV,

:Vertex float2 UV
:Vertex float3 PXYZ
:Texture ushort3 TR lenT

!

!shader_setup
    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    float3 SVd = VV[0];
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

	float3 pos = ((1-t)*currvertPXYZ2 + t*currvertPXYZ1) * tz;
	float d = fast_length(pos - (vp + 4 * SVd));
    float vPow = min(0.5f, emPow / (d*d*0.6f));

    Ro[wF * cy + ax] = convert_ushort3_sat(
      convert_float3(Ro[wF * cy + ax]) +
      convert_float3(TR[tex]) * vPow);

}

!