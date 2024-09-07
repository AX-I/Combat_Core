#version 330

#define NEAR 0.1
#define FAR 200.0

#define SBIAS 0.0

in vec3 v_pos;
//in vec3 v_color;
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

uniform vec3 highColor;
uniform vec3 highMult;

out vec4 f_color;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D TA;

uniform int translucent;

// Normal map
uniform int useNM;
uniform sampler2D NM;
uniform float NMmipBias;

in vec3 vertLight;

uniform vec3 vpos;

uniform float specular;
#define roughness 0.6f

uniform float f0;
uniform int hairShading;
uniform int tangentDir;

void main() {
	float tz = 1.0/depth;

	float alpha = texture(TA, v_UV / depth).r;
	if (alpha < 0.5) discard;

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
  float shadow0 = 0;
  float shadowDepth = 0;
  if ((sf.x > 0) && (sf.y > 0) && (sf.x < wS) && (sf.y < wS)) {
    shadow += texture(SM, sxy).r < sz ? si1*si2 : 0.0;
    shadow += texture(SM, s10).r < sz ? sr1*si2 : 0.0;
    shadow += texture(SM, s01).r < sz ? si1*sr2 : 0.0;
    shadow += texture(SM, s11).r < sz ? sr1*sr2 : 0.0;
  }
  shadow0 = shadow;

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

	  shadow += texture(SM2, sxy).r < sz ? si1*si2 : 0.0;
	  shadow += texture(SM2, s10).r < sz ? sr1*si2 : 0.0;
	  shadow += texture(SM2, s01).r < sz ? si1*sr2 : 0.0;
	  shadow += texture(SM2, s11).r < sz ? sr1*sr2 : 0.0;
    shadowDepth = max(0, sxyz.z - ((texture(SM2, sxy).r - 0.5)*FAR + NEAR + SBIAS) * 2);
    }

    shadow = clamp(shadow, 0, 1);

	vec3 norm = normalize(v_norm * tz);

  vec3 tangent;
  vec3 bitangent;
  if (useNM > 0) {
    vec2 dUV1 = dFdx(v_UV*tz);
    vec2 dUV2 = dFdy(v_UV*tz);
    vec3 dPos1 = dFdx(v_pos*tz);
    vec3 dPos2 = dFdy(v_pos*tz);

    float det = dUV1.x * dUV2.y - dUV1.y * dUV2.x;
    float rdet = 1.0 / det;

    tangent = normalize((dPos1 * dUV2.y - dPos2 * dUV1.y) * rdet);
    bitangent = normalize((dPos2 * dUV1.x - dPos1 * dUV2.x) * rdet);

    float nmBias = -0.8f;
    if (NMmipBias != 0) nmBias = NMmipBias;

    vec3 tgvec = texture(NM, v_UV*tz, nmBias).rgb * 2.0 - 1.0;
    tgvec = normalize(tgvec);

    norm = (det != 0.) ? normalize(tgvec.z * norm + -tgvec.y * tangent + -tgvec.x * bitangent) : norm;
  }

    vec3 light;
    if (translucent == 1) {
      if (hairShading == 0) {
        light = 0.6 * abs(dot(norm, LDir)) * (1-shadow) * LInt;
      }
    }
    else {
      light = max(0., dot(norm, LDir)) * (1-shadow) * LInt;
    }


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

    light += highColor;

    // Rim light
	vec3 a = v_pos*tz - vpos;
	float nd = dot(a, norm);
	vec3 refl = normalize(a - 2 * nd * norm);
	float theta = max(0.f, 0.1 + 0.9 * dot(normalize(a), refl));
	vec3 spec = theta * theta * vec3(0.008);

  // Sun specular
	a = normalize(a);
	vec3 h = normalize(a + LDir);
	theta = max(0.f, dot(h, norm));

	float fr = 1 - (1-f0)*max(0.f, dot(normalize(v_pos*tz - vpos), norm));
    fr *= fr; fr *= fr; //fr *= fr;

  vec3 tg = tangentDir * bitangent + (1-tangentDir) * tangent;

	int specPow = int(exp2(12*(1.f - roughness)));
	float fac = (specPow + 2) / (2*8*1.5 * 3.1416f);
  if (hairShading == 1) {
    // R
    h = normalize(a + LDir - 0.1 * tg);
    theta = max(0.f, dot(h, norm));
    fr *= (1-shadow0);
    spec += fac * specular * fr * pow(theta, specPow) * exp(-32.f*shadowDepth) * LInt;
  } else {
	spec += fac * specular * fr * pow(theta, specPow) * (1-shadow) * LInt;
  }

  if (hairShading == 1) {
    // TRT
    h = normalize(a + LDir + 0.2 * tg);
    theta = max(0.f, dot(h, norm));
	  specPow = int(specPow / 3);
	  fac = (specPow + 2) / (2*8 * 3.1416f);
    spec += fac * fr * pow(theta, specPow) * exp(-32.f*shadowDepth) * LInt * texture(tex1, v_UV/depth).rgb * 64;

    // TT
    float azimuthalTheta = max(0, dot(normalize(LDir * dot(a, LDir) + tg * dot(a, tg)), -LDir));
    azimuthalTheta = pow(azimuthalTheta, specPow);
    float longitudinalTheta = max(0, dot(normalize(-normalize(a - dot(a, tg)) + LDir + 0.06 * tg), normalize(v_norm * tz)));
    longitudinalTheta = pow(longitudinalTheta, specPow);
    spec += fac * fr * azimuthalTheta * longitudinalTheta * 0.25 * exp(-32.f*shadowDepth) * LInt * sqrt(texture(tex1, v_UV/depth).rgb * 8);

    // Forward scatter
    theta = max(0.f, dot(a, -LDir));
	  specPow = int(exp2(12*(1.f - roughness)));
	  fac = (specPow + 2) / (2*8 * 3.1416f);
    spec += fac * fr * pow(theta, specPow) * 0.25 * exp(-32.f*shadowDepth) * LInt * sqrt(texture(tex1, v_UV/depth).rgb * 8);

    // Multiple scatter
    spec += fac * fr * pow(theta, specPow) * 0.25 * exp(-12.f*shadowDepth) * LInt * texture(tex1, v_UV/depth).rgb * 8;

    // Back scatter
    theta = max(0.f, dot(a, norm));
	  specPow = int(exp2(12*(1.f - roughness * 2)));
	  fac = (specPow + 2) / (2*8 * 3.1416f);
    spec += fac * fr * pow(theta, specPow) * exp(-32.f*shadowDepth) * LInt * texture(tex1, v_UV/depth).rgb * 8;
  }



    light *= (1 + highMult);

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light + spec * specular;
    f_color = vec4(rgb, 0.5);
}