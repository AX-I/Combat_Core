#version 330

#define SAMPLES 12.f
#define SSKIP 4

uniform sampler2D tex1;
uniform sampler2D texd;

uniform sampler2D blue;

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

    vec3 vp = Vpos - oldPos;
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

	vec3 worldPos = vp + vec3(d) * (Vd - vec3((cx-wF/2)/sScale) * Vx + vec3((cy-hF/2)/sScale) * Vy);

	float oldZ = dot(worldPos, oldVV);
	float oldX = (dot(worldPos, oldVX) / oldZ) * -sScale + wF/2;
	float oldY = (dot(worldPos, oldVY) / oldZ) * sScale + hF/2;

	vec3 outRGB = texture(tex1, tc*wh).rgb * 0.0001;
	float dy = oldY - cy;
	float dx = oldX - cx;
  float accum = 1.f * 0.0001;
  float offset = texture(blue, vec2(((int(cx) & 15) + 0.5f)/16.f, ((int(cy) & 15) + 0.5f)/16.f)).r;
	for (float i=offset*SSKIP; i <= SAMPLES; i+=SSKIP) {
		float sy = clamp(cy + i/SAMPLES*EXPOSURE * dy, 1.f, hF-1.f);
		float sx = clamp(cx + i/SAMPLES*EXPOSURE * dx, 1.f, wF-1.f);

    float compd = texture(texd, vec2(sx, sy)*wh).r;
    worldPos = vp + vec3(compd) * (Vd - vec3((sx-wF/2)/sScale) * Vx + vec3((sy-hF/2)/sScale) * Vy);
    oldZ = dot(worldPos, oldVV);
	  oldX = (dot(worldPos, oldVX) / oldZ) * -sScale + wF/2;
	  oldY = (dot(worldPos, oldVY) / oldZ) * sScale + hF/2;
    vec2 compDxy = vec2(oldX-sx, oldY-sy);
    float influence = clamp(dot(vec2(dx,dy), compDxy) / (i * length(vec2(dx,dy))), 0, 1);

		outRGB += texture(tex1, vec2(sx, sy)*wh).rgb * influence;
    accum += influence;
	}

	f_color = outRGB / accum;

}
