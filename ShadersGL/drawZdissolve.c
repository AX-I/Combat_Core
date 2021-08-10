#version 330

in float depth;
out float color;

in vec3 v_pos;

uniform vec3 fadeOrigin;
uniform float fadeFact;

void main() {
	float tz = 1.0/depth;
	vec3 worldPos = v_pos*tz;
	float value = length(worldPos - fadeOrigin);
	value += 0.2 * (sin((worldPos.x+worldPos.z)*3) + sin((worldPos.x-worldPos.z)*3));
	if (value > fadeFact) discard;

	color = 1.0 / depth;
    gl_FragDepth = gl_FragCoord.z;
}