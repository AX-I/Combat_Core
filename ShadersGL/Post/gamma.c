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

//uniform float focus;

void main() {
	vec2 wh = 1 / vec2(width, height);
	vec2 tc = gl_FragCoord.xy;

	float d = texture(db, tc*wh).r;

	float focus = 3.f;
    float apeture = 8.f;
    float coc = apeture * abs(d-focus) / focus / d;

	vec3 color = vec3(0);
	float nsamples = 0;
	float cover;

	for (int i = 0; i < 8; i++) {
		cover = 1;
		vec2 target = tc + coc*vec2(cos(PI2*i/8), sin(PI2*i/8));
		target.x = int(target.x);
		target.y = int(target.y);

		if ((target.x < 0) || (target.x >= width) || (target.y < 0) || (target.y >= height)) cover = 0;

		float sz = texture(db, target * wh).r;
		float ecoc = apeture * abs(sz-focus) / focus / sz;

		if (coc > ecoc) cover *= ecoc / coc;
		nsamples += cover;

		color += texture(tex1, target * wh).rgb * cover;
	}

	/*for (int i = 0; i < 8; i++) {
		vec2 target = tc + 0.5f*coc*vec2(cos(PI2*i/8), sin(PI2*i/8));

		color += texture(tex1, target * wh).rgb;
	}*/

	color /= nsamples;


    /*int radius = int(min(MAXCOC, coc));

	vec3 color = vec3(0);
	int cover = 0;
	for (int i = -radius; i <= radius; i++) {
		for (int j = -radius; j <= radius; j++) {
			if (abs(i)+abs(j) <= int(coc * 1.5)) {
		        color += texture(tex1, (tc+vec2(i, j))*wh).rgb;
		        cover += 1;
		    }
		}
	}
	color /= cover;*/

	vec3 j = sqrt(8*exposure*color) / 1.1f;
	float m = max(j.r, max(j.g, j.b));
	if (m > 1.f) {
	  j = j / sqrt(m);
    }
    f_color = j;
}
