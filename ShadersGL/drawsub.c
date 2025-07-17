#version 330

out vec4 f_color;

uniform float emPow;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform vec3 tColor;
uniform int fadeUV; // 0 none, 1 circle, 2 star

uniform int useTex;

mat2 rot(float t) {
  return mat2(cos(t),-sin(t),sin(t),cos(t));
}

void main() {
  vec3 rgb = tColor + (v_norm) * 0.00001;

  float opacity = (1 - emPow);

  if (fadeUV == 1) {
    opacity *= max(0., 1-2*length(v_UV / depth - vec2(0.5)));
  }
  if (fadeUV == 2) {
    vec2 d = v_UV / depth - vec2(0.5);
    d *= rot(3.1415 / 4) * 0.8;
    float m = 2*length(d);
    m = exp(-7*m);
    m += 6*max(0., 0.5-2.*sqrt(abs(d.x))) * m;
    m += 6*max(0., 0.5-2.*sqrt(abs(d.y))) * m;
    opacity = min(1.0, opacity * m);
  }
  if (useTex == 1) {
    opacity *= texture(tex1, v_UV / depth).r;
    f_color = vec4(rgb, opacity);
  }
  else {
    f_color = vec4(rgb, opacity);
  }
}