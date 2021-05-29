#version 330

in float depth;
out float color;

in vec2 v_UV;
uniform sampler2D TA;

void main() {
	float tz = 1.0/depth;
	float alpha = texture(TA, v_UV / depth).r;
	if (alpha < 0.5) discard;

	color = 1.0 / depth;
    gl_FragDepth = gl_FragCoord.z;
}