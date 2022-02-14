// Particles

#version 330

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

uniform float aspect;
uniform float size;

out vec2 v_UV;

in VS_OUT {
  float depth;
} gs_in[];

void main() {
    float dimy = size * gs_in[0].depth;
    float dimx = dimy * aspect;

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
