// with square dof

#version 330

#define MAXCOC 4.f
#define PI2 6.283f

uniform sampler2D tex1;
uniform sampler2D db;
out vec3 f_color;
uniform float width;
uniform float height;
uniform float exposure;
uniform float focus;

//uniform float focus;

void main() {
	vec2 wh = 1 / vec2(width, height);
	vec2 tc = gl_FragCoord.xy;

	float d = texture(db, tc*wh).r;

    float apeture = 12.f;
    float coc = apeture * abs(d-focus) / focus / d;

	vec3 color = vec3(0);

	float nsamples = 0;
	float cover;
	int skip = max(1, int(coc / MAXCOC));
    float radius = coc;

	for (int i = -int(radius); i <= int(radius); i += skip) {
		for (int j = -int(radius); j <= int(radius); j += skip) {
			if (abs(i)+abs(j) <= int(coc * 1.5)) {
				cover = 1;

				vec2 target = tc + vec2(i, j);

				if ((target.x < 0) || (target.x >= width) || (target.y < 0) || (target.y >= height)) cover = 0;

				float sz = texture(db, target * wh).r;
				float ecoc = apeture * abs(sz-focus) / focus / sz;
				ecoc = min(MAXCOC, ecoc);

				if (radius > ecoc) cover *= ecoc / radius;
				nsamples += cover;

		        color += cover * texture(tex1, (tc+vec2(i, j))*wh).rgb;
		    }
		}
	}
	color /= nsamples;

	vec3 j = sqrt(8*exposure*color) / 1.1f;
	float m = max(j.r, max(j.g, j.b));
	if (m > 1.f) {
	  j = j / sqrt(m);
    }
    f_color = j;
}
