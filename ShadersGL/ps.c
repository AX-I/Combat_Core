// Particles

#version 330

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

uniform float size;

void main() {
	float dim = size
    gl_Position = gl_in[0].gl_Position + vec4(-dim, -dim, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( dim, -dim, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4(-dim, dim, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( dim, dim, 0.0, 0.0);
    EmitVertex();

    EndPrimitive();
}




    if ((dd > 0) && (fabs(dx) < cAX) && (fabs(dy) < cAY)) {
      dx = dx * -sScale + wF/2;
      dy = dy * sScale + hF/2;
      int dix = (int)(dx);
      int diy = (int)(dy);
      int vsize = max(2.f, min(12.f, size / dd));
      float vopacity = opacity; //min(1.f, opacity / dd);
      for (int ay = max(0, diy-vsize); ay < min(hF-1, diy+vsize); ay++) {
        for (int ax = max(0, dix-vsize); ax < min(wF-1, dix+vsize); ax++) {
          if (F[wF * ay + ax] > dd) {
            //Ro[wF * ay + ax] = convert_ushort_sat(Ro[wF * ay + ax] + 256 * vopacity * col.x);
            //Go[wF * ay + ax] = convert_ushort_sat(Go[wF * ay + ax] + 256 * vopacity * col.y);
            //Bo[wF * ay + ax] = convert_ushort_sat(Bo[wF * ay + ax] + 256 * vopacity * col.z);
            Ro[wF * ay + ax] *= (1.f-vopacity);
            Go[wF * ay + ax] *= (1.f-vopacity);
            Bo[wF * ay + ax] *= (1.f-vopacity);
          }
        }
      }
    }
    }
}
