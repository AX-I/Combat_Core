#version 330

#define NEAR 0.1
#define FAR 200.0

#define SBIAS -0.04
#define NBIAS 0.1

// # of PCF taps
#define SHS 25
// square root
#define SHSR 5
#define SHSOFT1 0.8
#define SHSOFT2 0.96
uniform float R[64]; // [0,1]

#define SCR_SHADOW
#define SCR_SOFT

#define RAYCAST_LENGTH 64
#define RAYCAST_STEP 2
#define RAYCAST_TARGET_DIST 99.0
#define RAYCAST_SURFACE_DEPTH 0.f
#define RAYCAST_DBIAS 0.02f
uniform float width;
uniform float height;
uniform float vscale;
uniform mat3 rawVM;

uniform sampler2D ssao;

in vec3 v_pos;
//in vec3 v_color;
uniform vec3 LDir;
uniform vec3 LInt;

// Shadowmap 1
uniform vec3 SPos;
uniform mat3 SV;
uniform float sScale;
uniform sampler2D SM;
uniform int wS;

// Shadowmap 2
uniform vec3 SPos2;
uniform mat3 SV2;
uniform float sScale2;
uniform sampler2D SM2;
uniform int wS2;

// Baked shadowmap sharing shadowmap 1 params
uniform sampler2D SM_im;
uniform int wS_im;

uniform int ignoreShadow;

// Lights
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
flat in vec3 v_gs_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D db;


uniform float translucent;

// Normal map
uniform int useNM;
uniform sampler2D NM;
uniform float NMmipBias;

in vec3 vertLight;

uniform vec3 vpos;

uniform float specular;
uniform float roughness;
uniform vec3 specRimEnvOff;

uniform int useNoise;
uniform float noiseDist;
uniform vec3 noisePos;
uniform sampler3D RAND;
mat2 rot(float t) {
  return mat2(cos(t),-sin(t),sin(t),cos(t));
}


uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
	float tz = 1.0/depth;

	vec3 norm = normalize(v_norm);

	vec3 sxyz = SV * (v_pos*tz - SPos);
  float normbias = min(1., 1 - dot(LDir, norm)) * NBIAS;
  float sz = (sxyz.z/2 - SBIAS - normbias - NEAR)/FAR + 0.5;
	vec2 sf = sxyz.xy * sScale/2 + 0.5;
	sf = clamp(sf, 0.0, 1.0) * wS;

	vec2 sxy;
	float sr1, sr2;

	float shadow = 0;

  vec2 tc = gl_FragCoord.xy;

  uint rng_state = uint(3.1416 * (tc.x + width*tc.y));
  uint rid1 = rand_xorshift(rng_state) & uint(63);
  rng_state = rand_xorshift(rng_state);
  uint rid2 = rand_xorshift(rng_state) & uint(63);
  vec2 sf0 = sf;

  for (int j=0; j<SHS; j++) {
    sf = sf0 + (vec2(j/SHSR, j%SHSR) - (SHSR-1)/2) * SHSOFT1 * rot(3.14/2* R[rid1]);
    for (int k=0; k<4; k++) {
      sxy = floor(sf + vec2(k>>1, k&1)) / wS;
      sr1 = abs(sf.x - sxy.x*wS);
      sr2 = abs(sf.y - sxy.y*wS);
      shadow += texture(SM, sxy).r < sz ? (1-sr1)*(1-sr2) / SHS : 0.0;
    }
  }

  // Baked shadowmap
  if (wS_im > 0) {
    sf = sxyz.xy * sScale/2 + 0.5;
    sf = clamp(sf, 0.0, 1.0);
    shadow += 1.0 - texture(SM_im, sf).r;
  }


	sxyz = SV2 * (v_pos*tz - SPos2);
	sz = (sxyz.z/2 - SBIAS - NEAR)/FAR + 0.5;
	sf = sxyz.xy * sScale2/2 + 0.5;
	if ((sf.x > 0) && (sf.y > 0) && (sf.x < 1) && (sf.y < 1)) {
	  sf *= wS2;
    sf0 = sf;

    for (int j=0; j<SHS; j++) {
      sf = sf0 + (vec2(j/SHSR, j%SHSR) - (SHSR-1)/2) * SHSOFT2 * rot(3.14/2* R[rid1]);
      for (int k=0; k<4; k++) {
        sxy = floor(sf + vec2(k>>1, k&1)) / wS2;
        sr1 = abs(sf.x - sxy.x*wS2);
        sr2 = abs(sf.y - sxy.y*wS2);
        shadow += texture(SM2, sxy).r < sz ? (1-sr1)*(1-sr2) / SHS : 0.0;
      }
    }
  }
  
    vec2 wh = 1 / vec2(width, height);
    float wF = width;
    float hF = height;
    float sVScale = vscale * hF / 2;
    
    vec3 SVd = rawVM[0];
    vec3 SVx = rawVM[1];
    vec3 SVy = rawVM[2];
    vec3 a = v_pos*tz - vpos;


  #ifdef SCR_SHADOW
    vec2 rxy = tc;
    #ifdef SCR_SOFT
      vec3 LDirTG1 = normalize(cross(LDir, vec3(1,0,0)));
      vec3 LDirTG2 = normalize(cross(LDir, LDirTG1));
      vec3 LDirSample = LDir + 0.1 * LDirTG1 * R[rid1] + 0.1 * LDirTG2 * R[rid2];
    #else
      vec3 LDirSample = LDir;
    #endif
    vec3 target = a - LDirSample*RAYCAST_TARGET_DIST;
    float rpz = dot(target, SVd);
    if (rpz < 0) { // direction is reversed
      target = a + (-dot(SVd, a) / dot(SVd, LDirSample) * 0.99) * LDirSample;
      rpz = dot(target, SVd);
    }
    vec2 rp = vec2(dot(target, SVx) * -sVScale / rpz + wF/2,
                   dot(target, SVy) * sVScale / rpz + hF/2);

    int hit = 0;
    vec3 hitPos;

    float dt = max(abs(rp.x - rxy.x), abs(rp.y - rxy.y));
    int vx = RAYCAST_STEP;
    float slopex = (rp.x - rxy.x) / dt * vx;
    float slopey = (rp.y - rxy.y) / dt * vx;
    float slopez = (1.f/rpz - depth) / dt * vx;

    float sy = tc.y;
    float sx = tc.x;
    sz = 1.f/tz;
    float sd = RAYCAST_SURFACE_DEPTH;
    int rn = 0;

    for (rn = 0; (hit == 0) && (rn < RAYCAST_LENGTH) &&
                 (sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF) && (sz > 0);
         rn += vx) {
        float currdist = texture(db, vec2(int(sx)+0.5f, int(sy)+0.5f) * wh).r;
        if ((currdist < 1.f/sz) &&
            (currdist > 1.f/sz - sd)) {

            hit = (rn > 2) ? 1 : 0;
            
            hitPos = currdist * (SVd - vec3((sx-wF/2)/sVScale) * SVx + vec3((sy-hF/2)/sVScale) * SVy);
        }
        sx += slopex;
        sy += slopey;
        sz += slopez;
        sd = abs(1.f/sz - 1.f/(sz - slopez)) + RAYCAST_DBIAS;
    }
    float shfact = ((dot(LDirSample, v_gs_norm) <= 0.04) && (dot(LDirSample, norm) > 0)) ? 0 : 1;
    shadow += hit * max(0.0, (1 - dot(hitPos-a, hitPos-a))) * shfact;
  #endif

	shadow = clamp(shadow, 0, 1);

	if (ignoreShadow == 1) shadow = 0;

  float ao = texture(ssao, tc/vec2(width, height)).r;

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

    vec3 light;
    if (translucent > 0) {light = abs(dot(norm, LDir)) * (1-shadow) * LInt;}
    else {light = max(0., dot(norm, LDir)) * (1-shadow) * LInt;}

    for (int i = 1; i < lenD; i++) {
		light += max(0., dot(norm, DDir[i]) + 0.5) * 0.66 * DInt[i] * (1 - ao);
	}

  vec3 spec = vec3(0);
  float theta;

  float rough = (roughness == 0) ? 0.6 : roughness;
  int specPow = int(exp2(12*(1.f - rough)));
	float fac = (specPow + 2) / (2*8 * 3.1416f);

	// Rim light
  vec3 specRimEnv = vec3(0.008) * (specRimEnvOff + 1);
    float nd = dot(a, norm);
    vec3 refl = normalize(a - 2 * nd * norm);
    theta = max(0.f, 0.1 + 0.9 * dot(normalize(a), refl));
    spec += specular * (theta * theta * specRimEnv) * (1 - ao);

	// Sun specular
	a = normalize(a);
	vec3 h = normalize(a + LDir);
	//theta = min(1.f, max(0.f, dot(h, norm) + 0.1f));
	theta = max(0.f, dot(h, norm));

	float fr = 1 - max(0.f, dot(normalize(v_pos*tz - vpos), norm));
    fr *= fr; fr *= fr; //fr *= fr;

	spec += fac * specular * fr * pow(theta, specPow) * (1-shadow) * LInt;


  for (int i = 0; i < lenP; i++) {
    vec3 pl = v_pos * tz - PPos[i];
    if (dot(norm, pl) > 0.0) {
	    light += dot(norm, normalize(pl)) / (1.0 + length(pl)*length(pl)) * PInt[i];

      vec3 h = normalize(normalize(pl) + a);
      theta = max(0.f, dot(h,norm));
      spec += fac * specular * fr * pow(theta, specPow) * PInt[i] / (1.0 + length(pl)*length(pl));
    }
  }

    light += vertLight * (1 - ao);

    light += highColor;

    light *= (1 + highMult);

    vec3 rgb = texture(tex1, v_UV / depth).rgb;
    if (useNoise != 0) {
      float val = 0;
      vec3 c = tz*v_pos * 0.1;
      for (int i = 0; i < 6; i++) {
        val += 1.f/float(1<<i) * texture(RAND, c).r;
        c.xz = c.xz * rot(1.f); c *= 2;
      }
      val *= 0.5; // val is in [0,1) after this

      val = val + noiseDist - 0.12*length(tz*v_pos - noisePos);

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