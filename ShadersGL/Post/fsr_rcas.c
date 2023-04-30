#version 450

#define A_GPU 1
#define A_GLSL 1

#include "ffx_a.h"

#define FSR_RCAS_F 1

uniform sampler2D Source;
out vec3 f_color;

AF4 FsrRcasLoadF(ASU2 p) { return AF4(texelFetch(Source, p, 0)); }
void FsrRcasInputF(inout AF1 r, inout AF1 g, inout AF1 b) {}

#include "ffx_fsr1.h"

AU4 const0;

void main() {
	FsrRcasCon(const0, 0.8);

	AF3 c;
	AU2 gxy = AU2(gl_FragCoord.xy);
	FsrRcasF(c.r, c.g, c.b, gxy, const0);

	f_color = AF4(c, 1).rgb;
}