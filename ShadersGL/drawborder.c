#version 330

out vec3 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float width;
uniform float height;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	vec2 wh = vec2(width, height);
	vec3 gp = vec3(gl_FragCoord.xy, 1 / depth);
	vec3 di = gp - vec3(wh / 2, 4);
	di.xy *= 2 / min(width, height);
	float d = length(di);
	float vPow = min(0.5, 0.1 / (d*d*0.6));

	vec3 norm = v_norm / depth;

    vec3 light = vPow + (LInt + LDir + norm) * 0.001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}