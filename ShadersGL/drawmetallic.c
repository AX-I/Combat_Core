#version 330

#define NEAR 0.1
#define FAR 200.0

#define SBIAS -0.04

in vec3 v_pos;

uniform vec3 LDir;
uniform vec3 LInt;

uniform vec3 SPos;
uniform mat3 SV;
uniform float sScale;
uniform sampler2D SM;
uniform int wS;


uniform vec3 SPos2;
uniform mat3 SV2;
uniform float sScale2;
uniform sampler2D SM2;
uniform int wS2;


uniform vec3 DInt[8];
uniform vec3 DDir[8];
uniform int lenD;

uniform vec3 PInt[16];
uniform vec3 PPos[16];
uniform int lenP;

out vec4 f_color;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

in vec3 vertLight;

uniform vec3 vpos;

uniform float roughness;
uniform int isMetal;

void main() {
	float tz = 1.0/depth;

	vec3 sxyz = SV * (v_pos*tz - SPos);
	float sz = (sxyz.z/2 - SBIAS - NEAR)/FAR + 0.5;
	vec2 sf = sxyz.xy * sScale/2 + 0.5;
	sf = clamp(sf, 0.0, 1.0) * wS;

	vec2 sxy = floor(sf) / wS;
	vec2 s10 = floor(sf + vec2(1,0)) / wS;
	vec2 s01 = floor(sf + vec2(0,1)) / wS;
	vec2 s11 = floor(sf + vec2(1,1)) / wS;
	float sr1 = sf.x - sxy.x*wS;
	float sr2 = sf.y - sxy.y*wS;
	float si1 = 1-sr1;
	float si2 = 1-sr2;

	float shadow = 0;
	shadow += texture(SM, sxy).r < sz ? si1*si2 : 0;
	shadow += texture(SM, s10).r < sz ? sr1*si2 : 0;
	shadow += texture(SM, s01).r < sz ? si1*sr2 : 0;
	shadow += texture(SM, s11).r < sz ? sr1*sr2 : 0;




	sxyz = SV2 * (v_pos*tz - SPos2);
	sz = (sxyz.z/2 - SBIAS - NEAR)/FAR + 0.5;
	sf = sxyz.xy * sScale2/2 + 0.5;
	if ((sf.x > 0) && (sf.y > 0) && (sf.x < 1) && (sf.y < 1)) {
	  sf = sf * wS2;

	  sxy = floor(sf) / wS2;
	  s10 = floor(sf + vec2(1,0)) / wS2;
	  s01 = floor(sf + vec2(0,1)) / wS2;
	  s11 = floor(sf + vec2(1,1)) / wS2;
	  sr1 = sf.x - sxy.x*wS2;
	  sr2 = sf.y - sxy.y*wS2;
	  si1 = 1-sr1;
	  si2 = 1-sr2;

	  shadow += texture(SM2, sxy).r < sz ? si1*si2 : 0;
	  shadow += texture(SM2, s10).r < sz ? sr1*si2 : 0;
	  shadow += texture(SM2, s01).r < sz ? si1*sr2 : 0;
	  shadow += texture(SM2, s11).r < sz ? sr1*sr2 : 0;
    }

	shadow = clamp(shadow, 0, 1);


    vec3 norm = normalize(v_norm * tz);

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