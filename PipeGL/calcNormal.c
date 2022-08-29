// Geometry shader: calculate new normals

#version 330

layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

out vec3 v_norm;

in VS_OUT_NORM {
  float depth;
  vec3 v_pos;
} gs[];

void main() {

    //vec3 norm = cross(gs[1].pos/gs[1].depth - gs[0].pos/gs[0].depth, gs[2].pos/gs[2].depth - gs[0].pos/gs[0].depth);

    vec3 norm = normalize(cross(gs[1].v_pos - gs[0].v_pos, gs[2].v_pos - gs[0].v_pos));

    v_norm = norm * gs[0].depth;
    gl_Position = gl_in[0].gl_Position;
    EmitVertex();

    v_norm = norm * gs[1].depth;
    gl_Position = gl_in[1].gl_Position;
    EmitVertex();

    v_norm = norm * gs[2].depth;
    gl_Position = gl_in[2].gl_Position;
    EmitVertex();

    EndPrimitive();
}
