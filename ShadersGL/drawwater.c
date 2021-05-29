// Screen Space Reflection
// For AXI Combat

#define REFL_STEP 2
#define REFL_LENGTH 0
#define REFL_DEPTH 2.f
#define REFL_VSIZE 2.f
#define REFL_DBIAS 0.5f
#define REFL_FADE 60
#define maxattn 0.1f
#define ABSORB 0.3f

#version 330

uniform vec3 vpos;

out vec4 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float width;
uniform float height;

in vec3 v_norm;
in vec3 v_pos;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D db;

void main() {
	vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;
	vec2 tc = gl_FragCoord.xy;
	float cx = tc.x;
	float cy = tc.y;

	vec3 vp = vpos;

	float tz = LDir.x + LInt.x;
	if (tz != 1.0/depth) tz = 1.0/depth;
	vec3 pos = v_pos / depth;
	vec3 norm = normalize(v_norm / depth);

	vec3 rgb = texture(tex1, v_UV / depth).rgb;

	float fr = 1 - max(0.f, dot(normalize(pos - vp), norm)) * maxattn;
    fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr; fr *= fr;

    float scatter = exp(ABSORB * (tz - texture(db, tc*wh).r));
    // is actually transmittance

    vec3 tsr = (1-scatter) * texture(tex1, v_UV / depth).rgb;

    // ...

    vec3 refl = vec3(0.04, 0.08, 0.12);

	// Blend mode ONE SRC_ALPHA
	f_color = vec4((1-fr) * tsr + fr * refl, (1-fr) * scatter);

}