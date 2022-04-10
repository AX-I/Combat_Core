#version 330

#define NEAR 0.1
#define FAR 200.0

#define SBIAS -0.04

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

in vec3 vertLight;

uniform vec3 vpos;

uniform float specular;

uniform vec3 VV;
uniform int useNoise;
uniform float noiseDist;
uniform sampler3D RAND;
mat2 rot(float t) {
  return mat2(cos(t),-sin(t),sin(t),cos(t));
}

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

    light += highColor;

    // Rim light
    vec3 a = v_pos*tz - vpos;
    float nd = dot(a, norm);
    vec3 refl = normalize(a - 2 * nd * norm);
    float theta = max(0.f, 0.1 + 0.9 * dot(normalize(a), refl));
    vec3 spec = theta * theta * vec3(0.008);
    spec *= specular;


    light *= (1 + highMult);

    vec3 rgb = texture(tex1, v_UV / depth).rgb;
    if (useNoise) {
      float val = 0;
      vec3 c = tz*v_pos * 0.1;
      for (int i = 0; i < 6; i++) {
        val += 1.f/float(1<<i) * texture(RAND, c).r;
        c.xz = c.xz * rot(1.f); c *= 2;
      }
      val *= 0.5; // val is in [0,1) after this

      val = val + noiseDist - 0.12*length(tz*v_pos - (vpos + 4 * VV));

      val = max(0., val);
      val *= 1.4;
      val = min(1., val);
      //if ((val < 0.2) && (val > 0)) {
      //  val = (0.2 + 2*(0.2-val)) * float(val > 0.1);
      //}
      rgb = vec3(0.125) * val + rgb * (1-val);
    }
    rgb = rgb * light + spec;
    f_color = vec4(rgb, 0.5);
}