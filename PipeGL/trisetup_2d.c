// For postprocess

#version 330

in vec3 in_vert;

void main() {
    gl_Position = vec4(in_vert, 1.0);
}