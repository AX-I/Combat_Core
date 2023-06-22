#version 330

out vec3 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float emPow;

uniform float fadeDist;
#define fadeBias 1.f

in vec3 v_norm;
in vec3 v_pos;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform vec3 VV;
uniform float iTime;

void main() {
  float tz = 1 / depth;
  vec3 norm = v_norm / tz;

  vec3 light = vec3(emPow) * 2.;
  vec3 up = vec3(0,1,0);
  vec3 right = normalize(cross(up, VV));
  up = cross(right, VV);

  vec2 tuv = 0.5+0.5*vec2(dot(norm, right), dot(norm, up));

  light += (LInt + LDir + v_UV.x) * 0.00001;

  float value = texture(tex1, v_UV / depth).r;
  value = max(0., 1.-64.*abs(value-0.125*fract(-(iTime-length(v_pos*tz))/6.))) * (value*8);
  vec3 rgb = vec3(value) * light;

  rgb += texture(tex1, tuv).rgb * light*0.001;

  value = texture(tex1, v_UV / depth).r;
  value = max(0., 1.-64.*abs(value-0.125*fract(-(iTime-length(v_pos*tz))/6. + 0.5))) * (value*8);
  rgb += vec3(value) * light;

  //vec3 refl = VV - 2 * norm * dot(norm, VV);
  //rgb += 0.125 * max(0., dot(refl, VV));
  f_color = rgb;
}