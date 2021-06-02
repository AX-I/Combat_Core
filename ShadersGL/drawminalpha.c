#version 330

out float color;

in vec2 v_UV;
uniform sampler2D TA;

void main() {
	float alpha = texture(TA, v_UV).r;
	if (alpha < 0.5) discard;

	color = gl_FragCoord.z;
    gl_FragDepth = gl_FragCoord.z;
}