#version 330

out vec4 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float emPow;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform vec3 tColor;
uniform int fadeUV;

void main() {
  vec3 norm = v_norm / depth;

  vec3 light = emPow + (LInt + LDir + norm) * 0.001;

  vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
  if (rgb != vec3(0)) rgb = vec3(0);

  rgb = (rgb != tColor) ? tColor : vec3(0);
  float opacity = (1 - emPow);

  if (fadeUV == 1) {
    opacity *= max(0., 1-2*length(v_UV / depth - vec2(0.5)));
  }

  f_color = vec4(rgb, opacity);
}