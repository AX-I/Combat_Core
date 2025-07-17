#version 330

out vec3 f_color;

in vec3 v_norm;
in vec3 v_pos;

in float depth;
in vec2 v_UV;
uniform sampler2D tex1;

uniform int isEqui;
uniform float rotY;

void main() {
	vec3 norm = v_norm / depth;

    vec3 light = 1 + (norm) * 0.001;

    vec2 uv = v_UV / depth;

    if (isEqui == 1) {
      vec3 pos = normalize(v_pos / depth);
      uv.x = atan(pos.x, pos.z) / 6.2832 + rotY;
      uv.y = acos(pos.y) / 3.1416;
    }

    vec3 rgb = texture(tex1, uv).rgb * light;
    f_color = rgb;
}