// Stochastic circle dof

#version 330

#define DOF_SAMPLES {DOF_SAMPLES}
#define DOF_P2 {DOF_P2}
#define DOF_2P2 {DOF_2P2}

#define PI2 6.28318531f

uniform sampler2D tex1;
uniform sampler2D db;
out vec3 f_color;

uniform float width;
uniform float height;

uniform float focus;
uniform float aperture;


uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
	vec2 wh = 1 / vec2(width, height);
  vec2 center = vec2(width, height)/2;

	vec2 tc = gl_FragCoord.xy;

	float d = texture(db, tc*wh).r;

  float coc = aperture * abs(d-focus) / focus / d;

	vec3 color = vec3(0);

  uint rng_state = uint((tc.y * height + tc.x)*PI2);
	float cover;
  float nsamples = 0;
  float ri,rj,si,sj;
	for (int k = 0; k<DOF_SAMPLES; k++) {

    ri = ((k&(DOF_P2-1)) + float(rng_state & 31u) / 31) / DOF_P2;
    rng_state = rand_xorshift(rng_state);
    rj = ((k>>DOF_2P2) + float(rng_state & 31u) / 31) / DOF_P2;
    rng_state = rand_xorshift(rng_state);
    float rq = sqrt(ri);

    si = coc * 1.07 * rq * cos(PI2 * rj);
    sj = coc * 1.07 * rq * sin(PI2 * rj);

    cover = 1;

    vec2 target = tc + vec2(si, sj);

    float sz = texture(db, target * wh).r;
    float ecoc = aperture * abs(sz-focus) / focus / sz;

    if (coc * 1.07 * rq > ecoc) cover *= 0;
    nsamples += cover;

    color += cover * texture(tex1, target*wh).rgb;
	}
  color = (nsamples > 0) ? color/nsamples : texture(tex1, tc*wh).rgb;

  f_color = color;
}
