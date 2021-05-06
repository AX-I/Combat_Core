#version 330

uniform sampler2D tex1;
out vec3 f_color;
uniform float width;
uniform float height;
uniform int useLum;

void main() {
	vec2 wh = 1 / vec2(width, height);
	vec2 tc = gl_FragCoord.xy;

	vec3 color = texture(tex1, tc*wh).rgb;

	float lum = dot(vec3(0.3626, 0.5152, 0.1222), color);

    vec3 j = color;

    if (useLum == 1) {
		j = color * lum;
	}

    f_color = j;
}
