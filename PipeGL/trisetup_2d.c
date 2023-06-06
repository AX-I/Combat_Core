// For postprocess

#version 330

in vec3 in_vert;

in vec3 in_norm;
in vec2 in_UV;

out vec3 v_norm;
out vec2 v_UV;

out float depth;

void main() {
    gl_Position = vec4(in_vert, 1.0);
    depth = 1;
    v_norm = in_norm;
    v_UV = in_UV;
}