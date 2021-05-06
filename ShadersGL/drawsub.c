#version 330

out vec4 f_color;

uniform vec3 LDir;
uniform vec3 LInt;

uniform float emPow;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	vec3 norm = v_norm / depth;

    vec3 light = emPow + (LInt + LDir + norm) * 0.001;

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = vec4(rgb * 0.0001, emPow * 0.6);
}