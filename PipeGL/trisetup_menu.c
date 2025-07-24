// For postprocess

#version 330

in vec3 in_vert;
in vec2 in_UV;
out vec2 v_UV;

uniform float sw;
uniform float sh;
uniform float ox;
uniform float oy;
uniform float W;
uniform float H;

void main() {
  vec3 pos = in_vert;
  pos.x = pos.x * sw/W + 2*ox/W-1;
  pos.y = pos.y * sh/H + 2*oy/H-1;
  gl_Position = vec4(pos, 1.0);
  v_UV = in_UV;
}