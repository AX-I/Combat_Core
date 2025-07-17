// Test perspective correct

#version 330

#define NEAR 0.1

#include UBO_VMP

//uniform float far;

in vec3 in_vert;
out vec3 v_pos;

in vec2 in_UV;
out vec2 v_UV;
in vec3 in_norm;
out vec3 v_norm;

out vec3 vertLight;

out float depth;


// Wave parameters
uniform vec3 origin;
uniform vec2 wDir1;
uniform vec2 wDir2;
uniform float pScale;
uniform float pTime;
uniform float wLen[6];
uniform float wAmp[6];
uniform float wSpd[6];
uniform int lenW;
uniform int lenW2;


void main() {

    vec3 w_vert = in_vert;
    vec3 w_norm = in_norm;

    w_vert = (w_vert - origin)/pScale;

    vec2 wxz = w_vert.xz;

    float py = 0;
	float derivx = 0;
	float derivz = 0;
	for (int i = 0; i < lenW; i++) {
	  float frq = 2.f / wLen[i];
	  float dist = dot(wDir1, wxz) * frq + pTime * wSpd[i];
	  py += wAmp[i] * sin(dist);
	  derivx += wAmp[i] * wDir1.x * cos(dist);
	  derivz += wAmp[i] * wDir1.y * cos(dist);
	}
	for (int i = 0; i < lenW2; i++) {
	  float frq = 2.f / wLen[lenW + i];
	  float dist = dot(wDir2, wxz) * frq + pTime * wSpd[lenW + i];
	  py += wAmp[lenW + i] * sin(dist);
	  derivx += wAmp[lenW + i] * wDir2.x * cos(dist);
	  derivz += wAmp[lenW + i] * wDir2.y * cos(dist);
	}

	w_vert = vec3(wxz.x, py, wxz.y);
	if (in_norm.x != 0.1) {
	  w_norm = vec3(derivx, -1, derivz);
    }
	w_norm = normalize(w_norm);

	w_vert = w_vert * pScale + origin + vec3(0, in_vert.y, 0);



    vec3 pos = vmat*(w_vert-vpos);

	depth = 1.0 / pos.z;
    v_pos = w_vert * depth;
    v_UV = in_UV * depth;
	v_norm = w_norm * depth;

    pos.xy /= abs(pos.z);
    if (pos.z < 0) pos.z /= 1000.;

    pos.z = 1.0 - NEAR / pos.z;

    pos.x *= aspect;
    pos.xy *= vscale;
    gl_Position = vec4(pos, 1.0);


    vec3 light = vec3(0.5);
    vertLight = light;

}