// Geometry shader: calculate new normals

#version 330

layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

out vec3 v_gs_norm;
out vec2 v_UV;
out vec3 v_pos;
out float depth;

in VS_OUT_NORM {
  float v_depth;
  vec3 v_pos;
  vec2 v_UV;
} gs[];

void main() {
    vec3 norm = normalize(cross(gs[1].v_pos - gs[0].v_pos, gs[2].v_pos - gs[0].v_pos));

    depth = gs[0].v_depth;
    v_UV = gs[0].v_UV;
    v_pos = gs[0].v_pos;
    v_gs_norm = norm * depth;
    gl_Position = gl_in[0].gl_Position;
    EmitVertex();

    depth = gs[1].v_depth;
    v_UV = gs[1].v_UV;
    v_pos = gs[1].v_pos;
    v_gs_norm = norm * depth;
    gl_Position = gl_in[1].gl_Position;
    EmitVertex();

    depth = gs[2].v_depth;
    v_UV = gs[2].v_UV;
    v_pos = gs[2].v_pos;
    v_gs_norm = norm * depth;
    gl_Position = gl_in[2].gl_Position;
    EmitVertex();

    EndPrimitive();
}
