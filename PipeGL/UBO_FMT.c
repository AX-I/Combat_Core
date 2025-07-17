#UBO_VMP
layout (std140, binding = 0) uniform vMatPos {
  mat3 vmat; // 0-2 *4
  vec3 vpos; // 3
  mat3 rawVM; // 4-6
  float vscale; // 7
  float aspect;
};

#UBO_SHM
layout (std140, binding = 1) uniform shArgs {
  vec3 SPos; // 0 *4
  mat3 SV; // 1-3
  float sScale; // 4
  float wS;
  float wS_im;
};

#UBO_SH2
layout (std140, binding = 2) uniform shArgs2 {
  vec3 SPos2; // 0 *4
  mat3 SV2; // 1-3
  float sScale2; // 4
  float wS2;
};

#UBO_LIGHTS
layout (std140, binding = 3) uniform Lights {
  float lenD; // 0 *4
  float lenP;
  float lenSL;
  vec3 DInt[8]; // 1-8
  vec3 DDir[8]; // 9-16
  vec3 PInt[16]; // 17-32
  vec3 PPos[16]; // 33-48
  vec3 SLInt[12]; // 49-60
  vec3 SLPos[12]; // 61-72
  vec3 SLDir[12]; // 73-84
};

#UBO_SMP
layout (std140, binding = 4) uniform sMatPos {
  vec3 vpos; // 0 *4
  mat3 vmat; // 1-3
  float vscale; // 4
  float sbias;
};

#UBO_PRI_LIGHT
layout (std140, binding = 5) uniform PrimaryLight {
  vec3 LInt;
  vec3 LDir;
};
