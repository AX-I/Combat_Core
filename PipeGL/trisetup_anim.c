//

#version 330

#define NEAR 0.1

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
//uniform float far;
uniform float aspect;

uniform mat4 RR[32];
uniform vec3 bOrigin[32];

in vec3 in_vert;
out vec3 v_pos;

in vec2 in_UV;
out vec2 v_UV;
in vec3 in_norm;
out vec3 v_norm;

in float boneNum;

uniform int off;

out float depth;

void main() {

    vec3 p = in_vert;
    vec3 n = in_norm;

    int bone = int(boneNum) - off;

    vec3 b_vert = (RR[bone] * vec4(p - bOrigin[bone], 1)).xyz; // Transformed position
    vec3 b_norm = (RR[bone] * vec4(n, 0)).xyz; // Transformed normal

    vec3 pos = vmat*(b_vert-vpos);

	depth = 1.0 / pos.z;
    v_pos = b_vert * depth;
    v_UV = in_UV * depth;
	v_norm = b_norm * depth;

    pos.xy /= abs(pos.z);
    if (pos.z < 0) pos.z /= 1000.;

    pos.z = 1.0 - NEAR / pos.z;

    pos.x *= aspect;
    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

}