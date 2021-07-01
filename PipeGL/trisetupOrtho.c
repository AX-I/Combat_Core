// For shadowmaps

#version 330

#define NEAR 0.1
#define FAR 200.0

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
uniform float sbias;

in vec3 in_vert;
in vec2 in_UV;
out vec2 v_UV;

void main() {

    vec3 pos = vmat*(in_vert-vpos);

    pos.z = (pos.z + sbias - NEAR)/FAR;

    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

    v_UV = in_UV;

}