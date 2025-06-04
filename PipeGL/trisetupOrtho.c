// For shadowmaps

#version 330

#define NEAR 0.1
#define FAR 200.0

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
uniform float sbias;

in vec3 in_vert;

uniform float isInstanced;
in vec4 inst_pos_scale;
in vec3 inst_rot_0;
in vec3 inst_rot_1;
in vec3 inst_rot_2;

in vec2 in_UV;
out vec2 v_UV;

void main() {
  vec3 world_pos = in_vert;
  if (isInstanced > 0) {
    mat3 inst_rot = mat3(inst_rot_0, inst_rot_1, inst_rot_2);
    world_pos = inst_rot*in_vert*inst_pos_scale.w + inst_pos_scale.xyz;
  }

    vec3 pos = vmat*(world_pos - vpos);

    pos.z = (pos.z + sbias - NEAR)/FAR;

    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);

    v_UV = in_UV;

}