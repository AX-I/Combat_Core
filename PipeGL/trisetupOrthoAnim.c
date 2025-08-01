// For shadowmaps

#version 420

#define NEAR 0.1
#define FAR 200.0

#include UBO_SMP

in vec3 in_vert;
in vec2 in_UV;
out vec2 v_UV;

uniform mat4 RR[32];
uniform vec3 bOrigin[32];
uniform int off;
in float boneNum;

void main() {
	int bone = int(boneNum) - off;
    vec3 b_vert = (RR[bone] * vec4(in_vert - bOrigin[bone], 1)).xyz;

    vec3 pos = vmat*(b_vert-vpos);

    pos.z = (pos.z + sbias - NEAR)/FAR;

    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

    v_UV = in_UV;

}