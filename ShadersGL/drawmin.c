#version 330

out float color;

void main() {
	color = gl_FragCoord.z;
    gl_FragDepth = gl_FragCoord.z;
}