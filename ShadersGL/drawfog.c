// Raymarch fog with 2-lobe HG phase function

#version 330

#define NEAR 0.1
#define FAR 100.0

#define NSAMPLES 16
#define DIST 1.f
#define LIGHT .036f
#define ABSORB 0.06f
#define G 0.5f
#define GBACK -0.25f

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


out vec4 f_color;


void main() {
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

	vec3 Vd = vmat[0];
	vec3 Vx = vmat[1];
	vec3 Vy = vmat[2];

	vec3 rayDir = normalize(Vd + (-Vx * (cx - wF/2) + Vy * (cy - hF/2)) / (vscale * hF/2));
	vec3 pos = vpos + rayDir * (0.5f + 0.25f * float(int(cx) & 1) + 0.125f * float(1-(int(cy) & 1)));

	float light = 0.f;
	float rn = 0;
	float currDepth = dot(pos - vpos, Vd);
	float transmit = 1.f;

	float inscatter = 0.f;
	float RdotL = -dot(rayDir, LDir);
	float phase = 0.5f * (1.f - G*G) / (4.f*3.14f* pow(1.f + G*G - 2.f*G * RdotL, 1.5f));
	phase += 0.5f * (1.f - GBACK*GBACK) / (4.f*3.14f* pow(1.f + GBACK*GBACK - 2.f*GBACK * RdotL, 1.5f));

	for (rn = 0; (rn < NSAMPLES) && (currDepth < maxZ); rn += 1.f) {

		vec3 sxyz = SV * (pos - SPos);
	    float sz = (sxyz.z/2 - NEAR)/FAR + 0.5;
	    vec2 sf = sxyz.xy * sScale/2 + 0.5;
	    sf = clamp(sf, 0.0, 1.0) * wS;
	    vec2 sxy = floor(sf) / wS;

		float scatter = exp(- ABSORB * currDepth);

		//if ((sx >= 0) && (sx < 2*wS-1) && (sy >= 0) && (sy < 2*wS-1)) {
			if (texture(SM, sxy).r > sz) light += LIGHT * scatter * phase;
			else light += LIGHT * inscatter * scatter;
		//}
		pos += rayDir * DIST;
		currDepth = dot(pos - vpos, Vd);
	}

	light += (- 1.f / ABSORB) * (exp(-ABSORB * maxZ) - exp(-ABSORB * currDepth)) * LIGHT * phase;
	transmit = exp(- ABSORB * maxZ);

	// Blend mode src.alpha
	f_color = vec4(light * LInt, (1.0 - transmit));



}