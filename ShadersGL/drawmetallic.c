#version 420

#define NEAR 0.1
#define FAR 200.0

#define SBIAS -0.04

#include UBO_VMP

in vec3 v_pos;

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

// Normal map
uniform int useNM;
uniform sampler2D NM;
uniform float NMmipBias;

in vec3 vertLight;

uniform float roughness;
uniform int isMetal;

void main() {
	float tz = 1.0/depth;

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


  vec3 norm = normalize(v_norm);
  if (useNM > 0) {
    vec2 dUV1 = dFdx(v_UV*tz);
    vec2 dUV2 = dFdy(v_UV*tz);
    vec3 dPos1 = dFdx(v_pos*tz);
    vec3 dPos2 = dFdy(v_pos*tz);

    float det = dUV1.x * dUV2.y - dUV1.y * dUV2.x;
    float rdet = 1.0 / det;

    vec3 tangent = normalize((dPos1 * dUV2.y - dPos2 * dUV1.y) * rdet);
    vec3 bitangent = normalize((dPos2 * dUV1.x - dPos1 * dUV2.x) * rdet);

    float nmBias = -0.8f;
    if (NMmipBias != 0) nmBias = NMmipBias;

    vec3 tgvec = texture(NM, v_UV*tz, nmBias).rgb * 2.0 - 1.0;
    tgvec = normalize(tgvec);

    norm = (det != 0.) ? normalize(tgvec.z * norm + -tgvec.y * tangent + -tgvec.x * bitangent) : norm;
  }

    vec3 light = vec3(0); // max(0., dot(norm, LDir)) * (1-shadow) * LInt;

    vec3 spec = vec3(0.f);
    vec3 a = normalize(v_pos*tz - vpos);
    float specPow = exp2(12*(1.f - roughness));
    vec3 h; float theta;

    for (int i = 1; i < lenD; i++) {
      light += max(0., dot(norm, DDir[i]) + 0.5) * 0.66 * DInt[i];
    }

    for (int i = 0; i < lenP; i++) {
      vec3 pl = v_pos * tz - PPos[i];
      if (dot(norm, pl) > 0.0) {
        float pdist = length(pl)*length(pl);
        // light += dot(norm, normalize(pl)) / (1.0 + pdist) * PInt[i];
        h = normalize(a + normalize(pl));
        theta = max(0.f, dot(h, norm));
        spec += pow(theta, specPow) * PInt[i] / pdist * (specPow + 2) / (8 * 3.1416f);
      }
    }

    light += vertLight;



    // Key light
    h = normalize(a + LDir);
    theta = max(0.f, dot(h, norm));
    spec += pow(theta, specPow) * (1-shadow) * LInt * (specPow + 2) / (8 * 3.1416f);

    a = v_pos*tz - vpos;
    float nd = dot(a, norm);
    vec3 refl = normalize(a - 2 * nd * norm);

    // Fill light
    theta = max(0.f, dot(refl, vec3(0.7,0.7,0)));
    spec += theta*theta * vec3(0.1,0.1,0.1);
    spec += vec3(1,0.8,0.3) * 0.1;

    // Rim light
    theta = max(0.f, dot(normalize(a), refl));
    spec += pow(theta, int(sqrt(specPow))) * vec3(0.2);


    vec3 albedo = texture(tex1, v_UV / depth).rgb;

    if (isMetal == 1) {
      spec *= albedo;
      light *= 0;
    }

    vec3 rgb = albedo * light + spec;
    f_color = vec4(rgb, 1);
}