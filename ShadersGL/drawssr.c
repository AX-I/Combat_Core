// Screen Space Reflection
// Refraction test

#version 330

#define REFL_STEP 2
#define REFL_LENGTH {REFL_LENGTH}
#define REFL_DEPTH 2.f
#define REFL_VSIZE 2.f
#define REFL_DBIAS 0.5f
#define REFL_FADE 60.f
#define MAXDIST 3000
#define maxattn 0.1f
#define ABSORB 0.3f

#include UBO_VMP

out vec4 f_color;

uniform float width;
uniform float height;

in vec3 v_norm;
in vec3 v_pos;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D db;
uniform sampler2D currFrame;

// Normal map
uniform int useNM;
uniform sampler2D NM;


uniform int useEquiEnv;
uniform float rotY;
uniform sampler2D equiEnv;

uniform float roughness;
uniform float R[64];

uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
	vec3 SVd = rawVM[0];
	vec3 SVx = rawVM[1];
	vec3 SVy = rawVM[2];

	vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;
	vec2 tc = gl_FragCoord.xy;
	float cx = tc.x;
	float cy = tc.y;

	vec3 vp = vpos;
	float sScale = vscale * hF / 2;

	float tz = 1.0/depth;
	vec3 pos = v_pos / depth;
	vec3 norm = normalize(v_norm / depth);

  if (useNM > 0) {
    vec2 dUV1 = dFdx(v_UV*tz);
    vec2 dUV2 = dFdy(v_UV*tz);
    vec3 dPos1 = dFdx(v_pos*tz);
    vec3 dPos2 = dFdy(v_pos*tz);

    float det = dUV1.x * dUV2.y - dUV1.y * dUV2.x;
    float rdet = 1.0 / det;

    vec3 tangent = normalize((dPos1 * dUV2.y - dPos2 * dUV1.y) * rdet);
    vec3 bitangent = normalize((dPos2 * dUV1.x - dPos1 * dUV2.x) * rdet);

    vec3 tgvec = texture(NM, v_UV*tz).rgb * 2.0 - 1.0;
    tgvec = normalize(tgvec);

    norm = (det != 0.) ? normalize(tgvec.z * norm + -tgvec.y * tangent + -tgvec.x * bitangent) : norm;
  }

  if (roughness > 0) {
    uint rng_state = uint(cy * hF + cx);
    uint rid1 = rand_xorshift(rng_state) & uint(63);
    rng_state = rand_xorshift(rng_state);
    uint rid2 = rand_xorshift(rng_state) & uint(63);
    rng_state = rand_xorshift(rng_state);
    uint rid3 = rand_xorshift(rng_state) & uint(63);
    rng_state = rand_xorshift(rng_state);
    vec3 svec = vec3(R[rid1], R[rid2], R[rid3]) * 2.f - 1.f;
    norm += roughness * normalize(svec);
    norm = normalize(norm);
  }

	vec3 rgb = texture(tex1, v_UV / depth).rgb;

	float fr = 1 - max(0.f, dot(normalize(pos - vp), norm)) * maxattn;
    fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr;





    vec3 a = pos - vp;
    float nd = dot(a, norm);
    vec3 refl = normalize(a - 2 * nd * norm) * REFL_VSIZE;

    int maxRLen = REFL_LENGTH;
    //if (dot(refl, SVd) < -0.1f) maxRLen = 1;
    if (refl.y < 0) maxRLen = 1;

    vec2 rxy = tc;
    float rpz = dot(a + refl, SVd);
    vec2 rp = vec2(dot(a + refl, SVx) * -sScale / rpz + wF/2,
                   dot(a + refl, SVy) * sScale / rpz + hF/2);

    int hit = 0;

    float dt = max(abs(rp.x - rxy.x), abs(rp.y - rxy.y));
    int vx = REFL_STEP;
    float slopex = (rp.x - rxy.x) / dt * vx;
	float slopey = (rp.y - rxy.y) / dt * vx;
	float slopez = (1.f/rpz - 1.f/tz) / dt * vx;

	vec3 ssr_out = vec3(0);
    vec2 ssr_loc = vec2(0);

    float sy = cy;
	float sx = cx;
	float sz = 1.f/tz;
	float sd = REFL_DEPTH;
    int rn = 0;

    for (rn = 0; (hit == 0) && (rn < maxRLen) &&
                 (sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF) && (sz > 0);
         rn += vx) {
	    float currdist = texture(db, vec2(int(sx)+0.5f, int(sy)+0.5f) * wh).r;
        if ((currdist < 1.f/sz) &&
            (currdist > 1.f/sz - sd)) {

            ssr_loc = vec2(sx, sy);
            hit = 1;
        }
        sx += slopex;
        sy += slopey;
        sz += slopez;
        sd = abs(1.f/sz - 1.f/(sz - slopez)) + REFL_DBIAS;

        if ((1.f/sz > MAXDIST) && (currdist > MAXDIST)) {
			ssr_loc = vec2(sx, sy);
            hit = 1;
		}
    }

    float fade = min(1.f, float(REFL_LENGTH - rn) / REFL_FADE);

    // Equirect fallback
    refl = normalize(refl);
    vec2 uvEnv;
    uvEnv.x = atan(refl.x, refl.z) / 6.2832 + rotY;
    uvEnv.y = acos(refl.y) / 3.1416;

    vec3 refltest = vec3(0.04, 0.08, 0.12);
    if (useEquiEnv == 1) {
      refltest = texture(equiEnv, uvEnv).rgb;
    }

    float refractDist = texture(db, tc*wh).r - tz;
    vec3 refractDir = normalize(a + 0.5 * nd * norm) * refractDist * (sScale/800);

	rpz = dot(a + refractDir, SVd);
    rp = vec2(dot(a + refractDir, SVx) * -sScale / rpz + wF/2,
              dot(a + refractDir, SVy) * sScale / rpz + hF/2);

    if (rp.y >= hF - 2) {
		rp = tc;
	}

	vec2 refractCoord = clamp(rp, vec2(0), vec2(wF-1, hF-1));

	if (texture(db, refractCoord*wh).r - tz < -0.1) refractCoord = tc;

    vec3 refracted = texture(currFrame, refractCoord*wh).rgb;


    float scatter = exp(ABSORB * min(0.f, tz - texture(db, refractCoord*wh).r));
	// is actually transmittance

    vec3 tsr = (1-scatter) * texture(tex1, v_UV / depth).rgb;


	if (hit == 1) {
		ssr_out = texture(currFrame, ssr_loc*wh).rgb;
		vec3 finalRefl = fade * ssr_out + (1-fade) * refltest;
		f_color = vec4((1-fr) * tsr + fr * finalRefl + (1-fr) * scatter * refracted, 0.0);
    } else {
		if (refl.y > 0) {
			f_color = vec4((1-fr) * tsr + fr * refltest + (1-fr) * scatter * refracted, 0.0);
		}
		else {
			// Underwater
			f_color = vec4(texture(tex1, v_UV / depth).rgb * 0.5, 0.5);
		}
	}

	// Blend mode Src ONE Dest SRC_ALPHA
}