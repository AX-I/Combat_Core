#version 330

//in vec3 v_pos;
//in vec3 v_color;
uniform vec3 LDir;
uniform vec3 LInt;

out vec3 f_color;

in vec3 v_norm;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

void main() {
	vec3 LDir2 = -normalize(vec3(1,-1,1));
	vec3 norm = v_norm / depth;

    vec3 light = LInt * max(0., dot(norm, LDir));
    light += vec3(0.3,0.3,0.3) * max(0., dot(norm, LDir2));

    vec3 rgb = texture(tex1, v_UV / depth).rgb * light;
    f_color = rgb;
}