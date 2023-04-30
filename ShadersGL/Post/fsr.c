#version 450

#define A_GPU 1
#define A_GLSL 1

#include "ffx_a.h"

#define FSR_EASU_F 1

uniform sampler2D Source;
out vec3 f_color;

uniform float width_in;
uniform float height_in;
uniform float width_out;
uniform float height_out;

AF4 FsrEasuRF(AF2 p) { return textureGather(Source, p, 0); }
AF4 FsrEasuGF(AF2 p) { return textureGather(Source, p, 1); }
AF4 FsrEasuBF(AF2 p) { return textureGather(Source, p, 2); }

#include "ffx_fsr1.h"

AU4 con0,con1,con2,con3,con4;

void CurrFilter(AU2 pos) {
	AF3 c;
	FsrEasuF(c, pos, con0, con1, con2, con3);

	f_color = AF4(c, 1).rgb;
}

void main() {
	FsrEasuCon(
		con0,con1,con2,con3,
		width_in, height_in,
		width_in, height_in,
		width_out, height_out
	);

	AU2 gxy = AU2(gl_FragCoord.xy);
	CurrFilter(gxy);
}