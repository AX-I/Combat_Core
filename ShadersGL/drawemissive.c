#version 330

out vec3 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float vPow;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	vec3 norm = v_norm / depth;

    vec3 light = vPow + (LInt + LDir + norm) * 0.001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}