// Geometry shader: calculate new normals

#version 330

layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

flat out vec3 v_gs_norm;

out float depth;
out vec2 v_UV;
out vec3 v_pos;
out vec3 v_norm;
out vec3 vertLight;

in VS_OUT_NORM {
  float v_depth;
  vec3 v_pos;
  vec2 v_UV;
  vec3 v_norm;
  vec3 vertLight;
} gs[];

void main() {
    vec3 norm = normalize(cross(gs[1].v_pos/gs[1].v_depth - gs[0].v_pos/gs[0].v_depth,
                                gs[2].v_pos/gs[2].v_depth - gs[0].v_pos/gs[0].v_depth));
    v_gs_norm = norm;

    depth = gs[0].v_depth;
    v_UV = gs[0].v_UV;
    v_pos = gs[0].v_pos;
    v_norm = gs[0].v_norm;
    vertLight = gs[0].vertLight;
    gl_Position = gl_in[0].gl_Position;
    EmitVertex();

    depth = gs[1].v_depth;
    v_UV = gs[1].v_UV;
    v_pos = gs[1].v_pos;
    v_norm = gs[1].v_norm;
    vertLight = gs[1].vertLight;
    gl_Position = gl_in[1].gl_Position;
    EmitVertex();

    depth = gs[2].v_depth;
    v_UV = gs[2].v_UV;
    v_pos = gs[2].v_pos;
    v_norm = gs[2].v_norm;
    vertLight = gs[2].vertLight;
    gl_Position = gl_in[2].gl_Position;
    EmitVertex();

    EndPrimitive();
}
