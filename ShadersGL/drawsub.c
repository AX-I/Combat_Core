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
uniform int fadeUV; // 0 none, 1 circle, 2 star

uniform int useTex;

void main() {
  vec3 norm = v_norm / depth;
  vec3 light = (LInt + LDir + norm) * 0.001;

  vec3 rgb = tColor + vec3(0) * light;

  float opacity = (1 - emPow);

  if (fadeUV == 1) {
    opacity *= max(0., 1-2*length(v_UV / depth - vec2(0.5)));
  }
  if (fadeUV == 2) {
    vec2 d = v_UV / depth - vec2(0.5);
    float m = 2*length(d);
    m = exp(-7*m);
    m += 6*max(0., 0.5-2.*sqrt(abs(d.x))) * m;
    m += 6*max(0., 0.5-2.*sqrt(abs(d.y))) * m;
    opacity = min(1.0, opacity * m);
  }
  if (useTex == 1) {
    opacity = texture(tex1, v_UV / depth).r;
    if (opacity < 0.5) discard;
    f_color = vec4(rgb * opacity, opacity);
  }
  else {
    f_color = vec4(rgb, opacity);
  }
}