// Test perspective correct

#version 330

#define NEAR 0.1

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
//uniform float far;
uniform float aspect;

in vec3 in_vert;
out vec3 v_pos;

in vec2 in_UV;
out vec2 v_UV;
in vec3 in_norm;
out vec3 v_norm;


uniform vec3 SLInt[128];
uniform vec3 SLPos[128];
uniform vec3 SLDir[128];
uniform int lenSL;
out vec3 vertLight;


out float depth;

void main() {

    vec3 pos = vmat*(in_vert-vpos);

	depth = 1.0 / pos.z;
    v_pos = in_vert * depth;
    v_UV = in_UV * depth;
	v_norm = in_norm * depth;

    pos.xy /= abs(pos.z);
    if (pos.z < 0) pos.z /= 1000.;

    pos.z = 1.0 - NEAR / pos.z;

    pos.x *= aspect;
    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);


    vec3 light = vec3(0);
    for (int i = 0; i < lenSL; i++) {
	  vec3 pl = in_vert - SLPos[i];
	  if ((dot(in_norm, pl) > 0.0) && (dot(SLDir[i], pl) > 0.0)) {
	    light += dot(in_norm, normalize(pl)) * dot(SLDir[i], normalize(pl))
			     / (1.0 + length(pl)*length(pl)) * SLInt[i];
	  }
    }
    vertLight = light;

}