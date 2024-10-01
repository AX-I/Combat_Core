#version 330

#define KSIZE 12

#define MAX_CONTINUITY 0.2f

#define DOWNSCALED 1
#define SCALEK 1

uniform sampler2D ssao;
uniform sampler2D texd;
uniform float width;
uniform float height;

out float f_color;


void main() {
  vec2 wh = DOWNSCALED / vec2(width, height);

	vec2 tc = gl_FragCoord.xy;
  vec2 offset;

	float ao = 0.f;
  float nsamples = 0.f;
  float fact;

	float d = texture(texd, tc*wh).r;
  float di;

	float dx = texture(texd, (tc + vec2(1, 0))*wh).r - d;
	float dy = texture(texd, (tc + vec2(0, 1))*wh).r - d;

	// Use the other side if closer object is in the way
	if (abs(dx) > MAX_CONTINUITY) {
		dx = d - texture(texd, (tc + vec2(-1, 0))*wh).r;
	}
	if (abs(dy) > MAX_CONTINUITY) {
		dy = d - texture(texd, (tc + vec2(0, -1))*wh).r;
	}

  for (int i=0; i<KSIZE*KSIZE; i++) {
    offset = (vec2(i/KSIZE, i%KSIZE) - KSIZE/2) * SCALEK;
        
    di = texture(texd, (tc + offset) * wh).r;
    
    fact = 1 - (abs(offset.x) + abs(offset.y)) / (KSIZE * SCALEK);

    if (abs(di - d) < MAX_CONTINUITY) {
      ao += texture(ssao, (tc + offset) * wh).r * fact;
      nsamples += 1 * fact;
    }
  }

	ao /= nsamples;

  f_color = ao;
}
