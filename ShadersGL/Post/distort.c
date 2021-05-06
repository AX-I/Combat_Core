#version 330

#define dsize 64.f
#define fade 128
#define fadeZ 4.f

uniform sampler2D tex1;
uniform sampler2D texd;
out vec3 f_color;
uniform float width;
uniform float height;
uniform float x;
uniform float y;
uniform float z;
uniform float portal;
uniform float strength;

void main() {
	vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;

	vec2 tc = gl_FragCoord.xy;

	vec2 offset = tc - vec2(x * wF, y * hF);

	float dist = length(offset);
	dist = max(0.f, dist - portal) / dsize;

	float factor = strength * sin(1/(dist*dist + 0.213f));

	if ((tc.x < fade) || (tc.x >= wF-fade)) {
		factor *= min(tc.x, wF-tc.x) / fade;
	} if ((tc.y < fade) || (tc.y >= hF-fade)) {
		factor *= min(tc.y, hF-tc.y) / fade;
	}

	if (texture(texd, tc*wh).r < z) {
		factor *= 1.f - min(1.f, (z - texture(texd, tc*wh).r) / fadeZ);
	}
	if (dist == 0) factor = 0;
	offset = normalize(offset);

	vec2 dest = tc + factor * offset;

	vec3 color = texture(tex1, dest*wh).rgb;

    f_color = color;
}
