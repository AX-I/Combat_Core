// For shadowmaps

#version 330

#define NEAR 0.1
#define FAR 100.0

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
uniform float sbias;

in vec3 in_vert;

void main() {

    vec3 pos = vmat*(in_vert-vpos);

    pos.z = (pos.z + sbias - NEAR)/FAR;

    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

}