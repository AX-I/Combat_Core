// Particles

#version 330

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

uniform float vscale;
uniform float aspect;
uniform float size;

out vec2 v_UV;
out vec3 v_norm;
out float depth;

in VS_OUT {
  float depth;
} gs_in[];

void main() {
    depth = gs_in[0].depth;
    float dimy = size * gs_in[0].depth * vscale;
    float dimx = dimy * aspect;

    v_norm = vec3(1,0,0);

    gl_Position = gl_in[0].gl_Position + vec4(-dimx, -dimy, 0.0, 0.0);
    v_UV = vec2(0,0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( dimx, -dimy, 0.0, 0.0);
    v_UV = vec2(1,0) * gs_in[0].depth;
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4(-dimx, dimy, 0.0, 0.0);
    v_UV = vec2(0,1) * gs_in[0].depth;
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( dimx, dimy, 0.0, 0.0);
    v_UV = vec2(1,1) * gs_in[0].depth;
    EmitVertex();

    EndPrimitive();
}
