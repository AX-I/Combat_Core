#version 330

in float depth;
out float color;

void main() {
	color = 1.0 / depth;
}