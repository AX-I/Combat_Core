// Test perspective correct

#version 420

#define NEAR 0.1

#include UBO_VMP

//uniform float far;

in vec3 in_vert;

in vec2 in_UV;
in vec3 in_norm;

uniform vec2 uv_lo;
uniform vec2 uv_hi;
uniform vec2 uv_offset;


#include UBO_LIGHTS
out vec3 vertLight;

uniform int stage;



out VS_OUT_NORM {
  float v_depth;
  vec3 v_pos;
  vec2 v_UV;
  vec3 v_norm;
  vec3 vertLight;
} vout_norm;


void main() {

    vec3 pos = vmat*(in_vert-vpos);

    vec2 tmp_UV = in_UV;
	if ((tmp_UV.x >= uv_lo.x) && (tmp_UV.x <= uv_hi.x) &&
	    (tmp_UV.y >= uv_lo.y) && (tmp_UV.y <= uv_hi.y)) {
	  tmp_UV += uv_offset;
	}

	float depth = 1.0 / pos.z;

    vout_norm.v_depth = depth;
    vout_norm.v_pos = in_vert * depth;

    vout_norm.v_UV = tmp_UV * depth;
    vout_norm.v_norm = in_norm * depth;
	  //v_norm = in_norm * depth;

    pos.xy /= abs(pos.z);
    if (pos.z < 0) pos.z /= 1000.;

    pos.z = 1.0 - NEAR / pos.z;

    pos.x *= aspect;
    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);


    vec3 light = vec3(0);
    for (int i = 0; i < lenSL; i++) {
	  vec3 pl = in_vert - SLPos[i];
	  if ((dot(in_norm, pl) > 0.0) && (dot(SLDir[i], pl) > 0.0)) {
	    light += dot(in_norm, normalize(pl)) * dot(SLDir[i], normalize(pl))
			     / (1.0 + dot(pl, pl)) * SLInt[i];
	  }
    }


    if (stage == 1) {
	  // Window
      float atriumbgx = 42.;
      float atriumLight = 2 * max(0, (18 + in_vert.x - atriumbgx)) / 18;

      atriumLight *= (0.5 + dot(-in_norm, vec3(1,0,0))) / 1.5;
      light += max(0.f, min(1.2f, atriumLight));

      // Lights
	  float rd = 5 - in_vert.y;
      if (rd < 0) rd = (in_vert.y - 5) * 10;
      light += 1.1 * max(0, 0.5 + dot(-in_norm, vec3(0,1,0))) / 1.5 / (0.8 + rd);
    }


    vertLight = light;
    vout_norm.vertLight = light;

}