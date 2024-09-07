
#version 330

#define NEAR 0.1
#define FAR 200.0



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

uniform vec3 SPos2;
uniform mat3 SV2;
uniform float sScale2;
uniform sampler2D SM2;
uniform int wS2;

uniform vec3 LInt;
uniform vec3 LDir;

uniform float width;
uniform float height;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;
uniform sampler2D db;

uniform float mul;

out vec4 f_color;

void main() {

    vec2 wh = 1 / vec2(width, height);
    float wF = width;
	float hF = height;
	vec2 tc = gl_FragCoord.xy;
	float cx = tc.x;
	float cy = tc.y;

  float intensity = 1.f;
  if (mul != 0) intensity = mul;

	float d = texture(db, tc*wh).r;

  float maxZ = v_norm.x + v_UV.x + aspect;
  if (maxZ != d) maxZ = d;

	vec3 Vd = vmat[0];
	vec3 Vx = vmat[1];
	vec3 Vy = vmat[2];

	

	vec3 rayDir = normalize(Vd + (-Vx * (cx - wF/2) + Vy * (cy - hF/2)) / (vscale * hF/2));


  float shadow = 0;

  vec3 sxyz = SV * (vpos - SPos);
  float sz = (sxyz.z/2 - NEAR)/FAR + 0.5;
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

  shadow += texture(SM, sxy).r < sz ? si1*si2 : 0.0;
  shadow += texture(SM, s10).r < sz ? sr1*si2 : 0.0;
  shadow += texture(SM, s01).r < sz ? si1*sr2 : 0.0;
  shadow += texture(SM, s11).r < sz ? sr1*sr2 : 0.0;

  sxyz = SV2 * (vpos - SPos2);
	sz = (sxyz.z/2 - NEAR)/FAR + 0.5;
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
  }
  shadow = clamp(shadow, 0, 1);

  float sunDot = max(0, -dot(rayDir,LDir));
  vec3 te = LInt;

  vec3 col = 0.01 * te * pow(sunDot, 8.0);
  col += 0.04 * te * pow(sunDot, 256.0);


  float fac = texture(tex1, vec2(0.5, 0.5) + (tc - vec2(wF/2,hF/2)) / width / vscale).r;
  col += te * fac * 4 * sunDot;


  col += 0.00000001 * maxZ;
  col *= (1-shadow) * intensity;

  f_color = vec4(col, 1.);



}