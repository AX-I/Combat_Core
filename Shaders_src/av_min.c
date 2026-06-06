// For early Z
!writeZ
!checkSkip

!shader_args
:Vertex float2 UV
!

!shader_setup
!

!shader_core

:DEPTH_COMPARE

:IF_DEPTH_TEST {

	F[wF * cy + ax] = tz;
}
!