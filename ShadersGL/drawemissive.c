#version 330

out vec3 f_color;

uniform float emPow;

uniform float fadeDist;
#define fadeBias 1.f

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	float tz = 1 / depth;
	vec3 norm = v_norm / tz;

    vec3 light = vec3(emPow);
    if (fadeDist != 0) {
      light *= vec3(clamp((tz-fadeBias)/(0.001+fadeDist), 0.f, 1.f));
    }
    light += (norm) * 0.00001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}