#version 420

#define NEAR 0.1
#define FAR 200.0

#define SBIAS -0.04

in vec3 v_pos;
//in vec3 v_color;
#include UBO_PRI_LIGHT

uniform sampler2D SM;
#include UBO_SHM

uniform sampler2D SM2;
#include UBO_SH2

#include UBO_LIGHTS

out vec4 f_color;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

in vec3 vertLight;

#include UBO_VMP

uniform vec3 fadeOrigin;
uniform float fadeFact;


void main() {
	float tz = 1.0/depth;

	vec3 worldPos = v_pos*tz;
	float value = length(worldPos - fadeOrigin);
	value += 0.2 * (sin((worldPos.x+worldPos.z)*3) + sin((worldPos.x-worldPos.z)*3));
	if (value > fadeFact) discard;

	vec3 sxyz = SV * (v_pos*tz - SPos);
	float sz = (sxyz.z/2 - SBIAS - NEAR)/FAR + 0.5;
	vec2 sf = sxyz.xy * sScale/2 + 0.5;
	sf = clamp(sf, 0.0, 1.0) * wS;

  float sr1, sr2;
  vec4 stx;

	float shadow = 0;
  sr1 = fract(sf.x);
  sr2 = fract(sf.y);
  sf += 0.5;
  stx = 1-step(sz, textureGather(SM, sf/wS).wzxy);
  shadow += dot(stx, vec4((1-sr1)*(1-sr2), sr1*(1-sr2), (1-sr1)*sr2, sr1*sr2));

	sxyz = SV2 * (v_pos*tz - SPos2);
	sz = (sxyz.z/2 - SBIAS - NEAR)/FAR + 0.5;
	sf = sxyz.xy * sScale2/2 + 0.5;
	if ((sf.x > 0) && (sf.y > 0) && (sf.x < 1) && (sf.y < 1)) {
	  sf = sf * wS2;

    sr1 = fract(sf.x);
    sr2 = fract(sf.y);
    sf += 0.5;
    stx = 1-step(sz, textureGather(SM2, sf/wS2).wzxy);
    shadow += dot(stx, vec4((1-sr1)*(1-sr2), sr1*(1-sr2), (1-sr1)*sr2, sr1*sr2));
    }

	shadow = clamp(shadow, 0, 1);


	vec3 norm = normalize(v_norm * tz);

    vec3 light = max(0., dot(norm, LDir)) * (1-shadow) * LInt;

    for (int i = 1; i < lenD; i++) {
		light += max(0., dot(norm, DDir[i]) + 0.5) * 0.66 * DInt[i];
	}

	for (int i = 0; i < lenP; i++) {
      vec3 pl = v_pos * tz - PPos[i];
      if (dot(norm, pl) > 0.0) {
	    light += dot(norm, normalize(pl)) / (1.0 + length(pl)*length(pl)) * PInt[i];
      }
    }

    light += vertLight;


    value = max(0., value + 0.2 - fadeFact);

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = vec4(rgb + vec3(value), 0.5);
}