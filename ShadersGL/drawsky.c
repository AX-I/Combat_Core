#version 330

uniform vec3 LDir;
uniform vec3 LInt;

out vec3 f_color;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	vec3 norm = v_norm / depth;

    vec3 light = 1 + (LInt + LDir + norm) * 0.001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}