// Raymarch fog with 2-lobe HG phase function

#version 330

#define NEAR 0.1
#define FAR 200.0

#define NSAMPLES 32
#define G 0.5f
#define GBACK -0.2f

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;
uniform float aspect;

in vec3 v_pos;

uniform vec3 SPos;
uniform mat3 SV;
uniform float sScale;
uniform sampler2D SM;
uniform int wS;

uniform vec3 LInt;
uniform vec3 LDir;

uniform float width;
uniform float height;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D db;

uniform float R[64]; // [0,1]

out vec4 f_color;

uniform float fogAbsorb;
uniform float fogLight;
uniform float fogDist;
uniform float fogScatter;
uniform float fogHeight;

uniform float fogAmbDistFac;
uniform vec3 fogAmb;

uniform float fogAmbDistAdd;

uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
	float LIGHT = .2f;
	if (fogLight != 0) LIGHT = fogLight / 8.f;

	float ABSORB = 0.06f;
	if (fogAbsorb != 0) ABSORB = fogAbsorb;

	float inscatter = 0.f;
	if (fogScatter != 0) inscatter = fogScatter;

    float fHeight = 1000.f;
	if (fogHeight != 0) fHeight = fogHeight;
	
	vec3 ambient = LIGHT * LInt * inscatter;

  ambient += fogAmb;
	

    vec2 wh = 1 / vec2(width, height);
    float wF = width;
	float hF = height;
	vec2 tc = gl_FragCoord.xy;
	float cx = tc.x;
	float cy = tc.y;

	float d = texture(db, tc*wh).r;

    float maxZ = 0 + v_norm.x + v_UV.x + texture(tex1, tc*wh).r;
    maxZ += aspect + vpos.x;
    if (maxZ != d) maxZ = d;

    float ambDistFac = 1.;
    if (fogAmbDistFac != 0) ambDistFac = fogAmbDistFac;

    float stepDist = 0.5;
    float stepFac = 1.2;
    if (fogDist != 0) {
      stepDist = fogDist * (1-stepFac) / (1-pow(stepFac,NSAMPLES));
      maxZ = min(maxZ, fogDist * ambDistFac);
    }

	vec3 Vd = vmat[0];
	vec3 Vx = vmat[1];
	vec3 Vy = vmat[2];

	uint rng_state = uint(cy * hF + cx);
	rng_state += uint(59 * (cy * hF + cx) + 83 * cx);
	uint rid1 = rand_xorshift(rng_state) & uint(63);
	rng_state = rand_xorshift(rng_state);
	rng_state += uint(17 * (cy * hF + cx) + 31 * cx);
	uint rid2 = rand_xorshift(rng_state) & uint(63);
	rng_state = rand_xorshift(rng_state);
	uint rid3 = rand_xorshift(rng_state) & uint(63);

	vec3 rayDir = normalize(Vd + (-Vx * (30*(R[rid2]-0.5f) + cx - wF/2) + Vy * (30*(R[rid3]-0.5f) + cy - hF/2)) / (vscale * hF/2));

  stepDist *= 1 + stepFac * (R[rid1]-0.5f) * (1 - 1/stepFac);
  stepDist *= 1.5;
	vec3 pos = vpos + rayDir * stepDist * (R[rid1] + 0.125f * float(int(cx) & 1) + 0.0625f * float(1-(int(cy) & 1)));

	vec3 light = vec3(0);
	float rn = 0;
	float currDepth = dot(pos - vpos, Vd);
	float transmit = 1.f;

	float RdotL = -dot(rayDir, LDir);
	float phase = 0.5f * (1.f - G*G) / (4.f*3.14f* pow(1.f + G*G - 2.f*G * RdotL, 1.5f));
	phase += 0.5f * (1.f - GBACK*GBACK) / (4.f*3.14f* pow(1.f + GBACK*GBACK - 2.f*GBACK * RdotL, 1.5f));

	float totDensity = 0.f;

	for (rn = 0; (rn < NSAMPLES) && (currDepth < maxZ); rn += 1.f) {

		vec3 sxyz = SV * (pos - SPos);
	    float sz = (sxyz.z/2 - NEAR)/FAR + 0.5;
	    vec2 sf = sxyz.xy * sScale/2 + 0.5;
	    sf = clamp(sf, 0.0, 1.0) * wS;
	    vec2 sxy = floor(sf) / wS;

        float heightFac = (pos.y > fHeight) ? 0 : 1;
		totDensity += heightFac * stepDist;

    // int e^{-cx} dx = -1/c e^{-cx}
    float scatter = 1/ABSORB * (exp(-ABSORB * currDepth) - exp(- ABSORB * (currDepth + stepDist))) * heightFac;

		if ((sf.x > 0) && (sf.y > 0) && (sf.x < wS) && (sf.y < wS)) {
			if (texture(SM, sxy).r > sz) light += LIGHT * scatter * phase * LInt;
			else light += ambient * scatter * phase;
		} else light += (LIGHT * LInt + fogAmbDistAdd * ambient) * (scatter * phase);
		pos += rayDir * stepDist;
		currDepth = dot(pos - vpos, Vd);
    stepDist *= stepFac;
	}

	float heightFac = (pos.y > fHeight) ? 0 : 1;

	light += heightFac * (- 1.f / ABSORB) * (exp(-ABSORB * maxZ) - exp(-ABSORB * currDepth)) * ambient * phase;

	transmit = exp(-ABSORB * totDensity);

	// Blend mode src.alpha
	f_color = vec4(max(vec3(0), light), (1.0 - transmit));

}