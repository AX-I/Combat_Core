// Stochastic circle dof

#version 330

#define DOF_SAMPLES 16
#define MAX_UINT 4294967295.f
#define PI2 6.283f

#define CHROM

uniform sampler2D tex1;
uniform sampler2D db;
out vec3 f_color;

uniform float width;
uniform float height;
uniform float exposure;

uniform float focus;
uniform float aperture;

uniform int tonemap;

uniform float blackPoint;


uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}


vec3 ACESFilm(vec3 x)
{
    float a = 2.51f;
    float b = 0.03f;
    float c = 2.43f;
    float d = 0.59f;
    float e = 0.14f;
    return min(vec3(1.f), max(vec3(0.f), (x*(a*x+b))/(x*(c*x+d)+e)));
}
vec3 ACESFilmLum(vec3 x)
{
    float lum = dot(x, vec3(0.2126f, 0.7152f, 0.0722f));
    float a = 2.51f;
    float b = 0.03f;
    float c = 2.43f;
    float d = 0.59f;
    float e = 0.14f;
    return (x / lum) * min(vec3(1.f), max(vec3(0.f), (lum*(a*lum+b))/(lum*(c*lum+d)+e)));
}

vec3 rtt_and_odt_fit(vec3 v)
{
    vec3 a = v * (v + 0.0245786f) - 0.000090537f;
    vec3 b = v * (0.983729f * v + 0.4329510f) + 0.238081f;
    return a / b;
}

void main() {
	vec2 wh = 1 / vec2(width, height);
  vec2 center = vec2(width, height)/2;

	vec2 tc = gl_FragCoord.xy;

	// For VR mode
	//tc.y = height - tc.y;
	//tc.x = (tc.x - width/2) * 0.95 + width/2;

	float d = texture(db, tc*wh).r;

  float coc = aperture * abs(d-focus) / focus / d;

	vec3 color = vec3(0);

  uint rng_state = uint(tc.y * height + tc.x);
	float cover;
  float nsamples = 0;
  float ri,rj,si,sj;
	for (int k = 0; k<DOF_SAMPLES; k++) {

    ri = float(rng_state & 31u) / 31;
    rng_state = rand_xorshift(rng_state);
    rj = float(rng_state & 31u) / 31;
    rng_state = rand_xorshift(rng_state);

    si = coc * 1.07 * sqrt(ri) * cos(PI2 * rj);
    sj = coc * 1.07 * sqrt(ri) * sin(PI2 * rj);

    cover = 1;

    vec2 target = tc + vec2(si, sj);

    float sz = texture(db, target * wh).r;
    float ecoc = aperture * abs(sz-focus) / focus / sz;

    if (coc > ecoc) cover *= ecoc / coc;
    nsamples += cover;

    #ifdef CHROM
    vec2 coord = tc + vec2(si, sj) - center;
    color.r += cover * texture(tex1, (coord*0.996 + center)*wh).r;
    color.g += cover * texture(tex1, (coord + center)*wh).g;
    color.b += cover * texture(tex1, (coord*1.003 + center)*wh).b;
    #else
    color += cover * texture(tex1, (tc + vec2(si, sj))*wh).rgb;
    #endif
	}
	color /= nsamples;

    vec3 j = max(vec3(0.f), 8 * exposure * color - blackPoint);
    // now is in [0,1]

  float vignette = dot((tc - center) * wh, (tc - center) * wh);

  j *= 1 - vignette*vignette * 2.5;

  if (tonemap == 0) {
    // Basic gamma
	j = sqrt(j) / 1.1f;
	float m = max(j.r, max(j.g, j.b));
	if (m > 1.f) {
	  j = j / sqrt(m);
    }
  }

  if (tonemap == 1) {
    // Reinhard luminance with white point
    float WHITE = 2.f;
    float lum = dot(j, vec3(0.2126f, 0.7152f, 0.0722f));
	j = j * (1.f + lum / (WHITE*WHITE)) / (lum + 1.f);
    j = sqrt(j);
  }

  if (tonemap == 2) {
    // Reinhard per-channel with white point
    float WHITE = 2.f;
    j = j * (1.f + j / (WHITE*WHITE)) / (j + 1.f);
    j = sqrt(j);
  }

  if (tonemap == 3) {
    // ACES
	/*j = ACESFilm(j/2);
    j = sqrt(j);*/
    mat3 acesIn = mat3(vec3(0.59719f, 0.35458f, 0.04823f),
                       vec3(0.07600f, 0.90834f, 0.01566f),
                       vec3(0.02840f, 0.13383f, 0.83777f));
    mat3 acesOut = mat3(vec3( 1.60475f, -0.53108f, -0.07367f),
                       vec3(-0.10208f,  1.10813f, -0.00605f),
                       vec3(-0.00327f, -0.07276f,  1.07602f));
    j = j * acesIn;
    j = rtt_and_odt_fit(j);
    j = j * acesOut;
    j = sqrt(j);
  }

  f_color = j;
}
