// For shadowmaps

#version 330

#define NEAR 0.1
#define FAR 200.0

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
uniform float sbias;

in vec3 in_vert;
in vec4 inst_pos_scale;
in vec2 in_UV;
out vec2 v_UV;

void main() {
    float scale = (inst_pos_scale.w == 0) ? 1 : inst_pos_scale.w;
    vec3 pos = vmat*(in_vert*scale + inst_pos_scale.xyz - vpos);

    pos.z = (pos.z + sbias - NEAR)/FAR;

    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

    v_UV = in_UV;

}