#version 330

#define radius 1.f
#define bias 0.002f
#define nsamples 32
#define FALLOFF_DIST 0.5f

#define MAX_CONTINUITY 0.2f

#define DOWNSCALED {DOWNSCALED}

uniform sampler2D texd;
uniform float width;
uniform float height;
uniform float vscale;
uniform float R[64];

out float f_color;


uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
    vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;

	vec2 tc = gl_FragCoord.xy * DOWNSCALED;
	float cx = tc.x;
	float cy = tc.y;

	float sScale = vscale * hF/2;

	float ao = 0.f;

	uint rng_state = uint(cy * hF + cx);

	float d = texture(texd, tc*wh).r;

	vec3 pos = d * vec3((cx+0.5f-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);

	float dx = texture(texd, (tc + vec2(1, 0))*wh).r;
	float dy = texture(texd, (tc + vec2(0, 1))*wh).r;

	// Use the other side if closer object is in the way
	if (abs(dx - d) > MAX_CONTINUITY) {
		dx = 2*d - texture(texd, (tc + vec2(-1, 0))*wh).r;
	}
	if (abs(dy - d) > MAX_CONTINUITY) {
		dy = 2*d - texture(texd, (tc + vec2(0, -1))*wh).r;
	}

	int rx = 1;
	int ry = 1;


	vec3 px = dx * vec3((cx+0.5f+rx-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);
	vec3 py = dy * vec3((cx+0.5f-wF/2)/sScale, -(cy+0.5f+ry-hF/2)/sScale, 1);
	vec3 norm = rx*ry*normalize(cross(pos-px, pos-py));

    // Bias to prevent grayness
	int sig_x = norm.x > 0 ? 1 : -1;
	int sig_y = norm.y > 0 ? -1 : 1;

	for (int i = 0; i < nsamples; i++) {
		uint rid1 = rand_xorshift(rng_state) & uint(63);
		rng_state = rand_xorshift(rng_state);
		uint rid2 = rand_xorshift(rng_state) & uint(63);
		rng_state = rand_xorshift(rng_state);
		uint rid3 = rand_xorshift(rng_state) & uint(63);
		rng_state = rand_xorshift(rng_state);

		vec3 svec = vec3(R[rid1], R[rid2], R[rid3]) * 2.f - 1.f;

		svec = normalize(svec);

		if (dot(svec, norm) < 0) svec = svec - 2*norm*dot(svec, norm);

		rid1 = rand_xorshift(rng_state) & uint(63);
		rng_state = rand_xorshift(rng_state);

		float rlen = R[rid1];
		svec *= rlen*rlen * radius;

		svec += pos;

		float sz = svec.z;
		float sx = (svec.x/sz*sScale) + wF/2;
		float sy = (-svec.y/sz*sScale) + hF/2;

		if ((sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF)) {

			float sampd = texture(texd, vec2(int(sx) + 0.5*sig_x, int(sy) + 0.5*sig_y)*wh).r;

			float disct = clamp(2.f - (d-sampd)/FALLOFF_DIST, 0.f, 1.f);
		    ao += disct * ((sampd < sz - bias) ? 1.f : 0.f);

   	    }
	}
	ao /= nsamples;

	if (d > 200) ao = 0;

	ao = clamp(ao*1.25f, 0.f, 1.f);

  f_color = ao;
}
