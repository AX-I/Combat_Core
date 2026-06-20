
!shader_args

float emPow,

!

!shader_setup
!

!shader_core

:IF_DEPTH_TEST {

    Ro[wF * cy + ax] = convert_ushort3_sat(
      convert_float3(Ro[wF * cy + ax]) * emPow);
}

!