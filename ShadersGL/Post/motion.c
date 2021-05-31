#version 330

#define SAMPLES 12.f

uniform sampler2D tex1;
uniform sampler2D texd;

uniform float EXPOSURE;

uniform vec3 Vpos;
uniform mat3 VV;
uniform float vscale;

uniform vec3 oldPos;
uniform vec3 oldVV;
uniform vec3 oldVX;
uniform vec3 oldVY;

uniform float width;
uniform float height;

out vec3 f_color;


void main() {

    vec3 vp = Vpos;
	vec3 Vd = VV[0];
	vec3 Vx = VV[1];
    vec3 Vy = VV[2];

    vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;

	vec2 tc = gl_FragCoord.xy;
	float cx = tc.x;
	float cy = tc.y;

	float sScale = vscale * hF / 2;


	float d = texture(texd, tc*wh).r;

	vec3 worldPos = vp - oldPos + vec3(d) * (Vd - vec3((cx-wF/2)/sScale) * Vx + vec3((cy-hF/2)/sScale) * Vy);

	float oldZ = dot(worldPos, oldVV);
	float oldX = (dot(worldPos, oldVX) / oldZ) * -sScale + wF/2;
	float oldY = (dot(worldPos, oldVY) / oldZ) * sScale + hF/2;

	vec3 outRGB = vec3(0);
	float dy = oldY - cy;
	float dx = oldX - cx;
	for (float i=0; i <= SAMPLES; i+= 1) {
		float sy = clamp(cy + i/SAMPLES*EXPOSURE * dy, 0.f, hF-1.f);
		float sx = clamp(cx + i/SAMPLES*EXPOSURE * dx, 0.f, wF-1.f);

		outRGB += texture(tex1, vec2(sx, sy)*wh).rgb;
	}

	f_color = outRGB / vec3(SAMPLES);

}
