// Eye tracking

#version 330

#define NEAR 0.1

uniform mat3 vmat;
uniform vec3 vpos;
uniform float vscale;

uniform float aspect;

uniform mat4 RR[32];
uniform vec3 bOrigin[32];

in vec3 in_vert;
out vec3 v_pos;

in vec2 in_UV;
out vec2 v_UV;
in vec3 in_norm;
out vec3 v_norm;

uniform vec2 uv_lo;
uniform vec2 uv_hi;
uniform vec2 uv_offset;


uniform vec3 SLInt[128];
uniform vec3 SLPos[128];
uniform vec3 SLDir[128];
uniform int lenSL;
out vec3 vertLight;


in float boneNum;

uniform int off;

uniform int stage;

out float depth;

out VS_OUT_NORM {
  float v_depth;
  vec3 v_pos;
  vec2 v_UV;
  vec3 v_norm;
  vec3 vertLight;
} vout_norm;

void main() {

    vec3 p = in_vert;
    vec3 n = in_norm;

    int bone = int(boneNum) - off;

    vec3 b_vert = (RR[bone] * vec4(p - bOrigin[bone], 1)).xyz; // Transformed position
    vec3 b_norm = (RR[bone] * vec4(n, 0)).xyz; // Transformed normal

    vec3 pos = vmat*(b_vert-vpos);

    vec2 tmp_UV = in_UV;
    if ((tmp_UV.x >= uv_lo.x) && (tmp_UV.x <= uv_hi.x) &&
        (tmp_UV.y >= uv_lo.y) && (tmp_UV.y <= uv_hi.y)) {
		tmp_UV += uv_offset;
	}

	depth = 1.0 / pos.z;
    v_pos = b_vert * depth;
    v_UV = tmp_UV * depth;
	v_norm = b_norm * depth;

  vout_norm.v_pos = b_vert * depth;
  vout_norm.v_UV = tmp_UV * depth;
  vout_norm.v_norm = b_norm * depth;
  vout_norm.v_depth = depth;

    pos.xy /= abs(pos.z);
    if (pos.z < 0) pos.z /= 1000.;

    pos.z = 1.0 - NEAR / pos.z;

    pos.x *= aspect;
    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);


    vec3 light = vec3(0);
	for (int i = 0; i < lenSL; i++) {
	  vec3 pl = b_vert - SLPos[i];
	  if ((dot(b_norm, pl) > 0.0) && (dot(SLDir[i], pl) > 0.0)) {
		light += dot(b_norm, normalize(pl)) * dot(SLDir[i], normalize(pl))
				 / (1.0 + dot(pl, pl)) * SLInt[i];
	  }
	}


	if (stage == 1) {
	  // Window
	  float atriumbgx = 42.;
	  float atriumLight = 1.2 * max(0, (18 + b_vert.x - atriumbgx)) / 18;

	  atriumLight *= (0.33 + dot(-b_norm, vec3(1,0,0))) / 1.33;
      light += max(0.f, min(1.2f, atriumLight));

      // Lights
      float rd = 5 - b_vert.y;
      if (rd < 0) rd = (b_vert.y - 5) * 10;
      light += 0.6 * max(0, 0.5 + dot(-b_norm, vec3(0,1,0))) / 1.5 / (0.8 + rd);
    }


    vertLight = light;
    vout_norm.vertLight = light;

}