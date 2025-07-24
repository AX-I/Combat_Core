// Screen Space Reflection
// For AXI Combat

#version 420

#define REFL_STEP 2
#define REFL_LENGTH {REFL_LENGTH}
#define REFL_DEPTH 0.5f
#define REFL_VSIZE 2.f
#define REFL_DBIAS 0.2f
#define REFL_FADE 60.f

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

	vec3 rgb = texture(tex1, v_UV / depth).rgb;

	float fr = 1 - 0.8 * abs(dot(normalize(pos - vp), normalize(norm)));
    fr *= fr; fr *= fr; //fr *= fr; fr *= fr; fr *= fr; fr *= fr;

    //float scatter = 0.2;//exp(ABSORB * (tz - texture(db, tc*wh).r));
    // is actually transmittance

    //vec3 tsr = (1-scatter) * texture(tex1, v_UV / depth).rgb;
    vec3 tsr = texture(tex1, v_UV / depth).rgb;
    if (tsr.x != 0) tsr.x = 0;




    vec3 a = pos - vp + tsr.x;
    float nd = dot(a, norm);
    vec3 refl = normalize(a - 2 * nd * norm) * REFL_VSIZE;

    int maxRLen = REFL_LENGTH;

	if (dot(refl, SVd) < -0.5f) maxRLen = 1;

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

        if ((1.f/sz > 600) && (currdist > 600)) {
			ssr_loc = vec2(sx, sy);
            hit = 1;
		}
    }

    // No cubemap fallback here

    float fade = min(1.f, float(REFL_LENGTH - rn) / REFL_FADE);


    vec3 refltest = vec3(0.06, 0.06, 0.06);


	if (hit == 1) {
		ssr_out = texture(currFrame, ssr_loc*wh).rgb;
		vec3 finalRefl = fade * ssr_out + (1-fade) * refltest;
		f_color = vec4(fr * finalRefl, 1-fr);
    } else {
		f_color = vec4(fr * refltest, 1-fr);
	}

	// Blend mode ONE SRC_ALPHA
}