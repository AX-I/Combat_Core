#version 330

out vec3 f_color;

in vec3 v_pos;
uniform vec3 LDir;
uniform vec3 LInt;

uniform float width;
uniform float height;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

uniform float iTime;

// https://www.shadertoy.com/view/wtdSzX
const vec2 s = vec2(1, 1.7320508);
float hex(in vec2 p) {
    p = abs(p);
    return max(dot(p, s*.5), p.x); // Hexagon.
}
vec4 getHex(vec2 p) {
  vec4 hC = floor(vec4(p, p - vec2(.5, 1))/s.xyxy) + .5;
  vec4 h = vec4(p - hC.xy*s, p - (hC.zw + .5)*s);
  return dot(h.xy, h.xy) < dot(h.zw, h.zw) 
        ? vec4(h.xy, hC.xy) 
        : vec4(h.zw, hC.zw + .5);
}


void main() {
	vec2 wh = vec2(width, height);
	vec3 gp = vec3(gl_FragCoord.xy, 1 / depth);
	vec3 di = gp - vec3(wh / 2, 4);
	di.xy *= 2 / min(width, height);
	float d = length(di);
	float vPow = min(0.5, 0.1 / (d*d*0.6));

	vec3 norm = v_norm / depth;

  vec3 pos = v_pos / depth;
  vec2 hc = (abs(norm.x) > abs(norm.z)) ? pos.yz : pos.xy;
  float hd = hex(getHex(hc).xy) * 1.8;
  float fac = max(0., -5 + 6*hd) * 8;
  fac += max(0., 1-6*abs(hd - mod(iTime * 0.4 - 0.1 * (pos.x+pos.z+pos.y), 1.6) + 0.4)) * 0.3;
  vPow *= fac;


    vec3 light = vPow + (LInt + LDir + norm) * 0.001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}