#version 330

#define KSIZE 8

#define MAX_CONTINUITY 0.2f

#define DOWNSCALED 1
#define SCALEK 2

uniform sampler2D ssao;
uniform sampler2D texd;
uniform float width;
uniform float height;

out float f_color;


void main() {
  vec2 wh = 1 / vec2(width, height);

	vec2 tc = gl_FragCoord.xy;
  vec2 offset;

	float ao = 0.f;
  float nsamples = 0.f;

	float d = texture(texd, tc*wh * DOWNSCALED).r;
  float di;

  for (int i=0; i<KSIZE*KSIZE; i++) {
    offset = vec2(i/KSIZE, i%KSIZE) - (KSIZE-1.0)/2.0;
        
    di = texture(texd, (tc + offset * SCALEK) * wh * DOWNSCALED).r;

    if (abs(di - d) < MAX_CONTINUITY) {
      ao += texture(ssao, (tc + offset * SCALEK) * wh * DOWNSCALED).r;
      nsamples += 1;
    }
  }

	ao /= nsamples;

  f_color = ao;
}
