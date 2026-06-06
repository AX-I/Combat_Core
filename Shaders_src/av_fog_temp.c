// Raymarch fog with 2-lobe HG phase function

#define NSAMPLES 4
#define G 0.5f
#define GBACK -0.25f

!shader_args

__constant float *Vpos, __constant float3 *VV, const float vScale,

__constant float3 *LInt,
__constant float3 *LDir,

__global float *SD, const int wS, const float sScale,
__constant float3 *SV, __constant float *SPos,

const float fogAbsorb,
const float fogLight,
const float fogDist,
const float fogScatter,
!

!shader_setup
    float3 VP = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    float3 VVd = VV[0];
	float3 VVx = VV[1];
    float3 VVy = VV[2];

    float3 SP = (float3)(SPos[0], SPos[1], SPos[2]);
    float3 SVd = SV[0];
    float3 SVx = SV[1];
    float3 SVy = SV[2];

	float LIGHT = .2f;
	if (fogLight != 0) LIGHT = fogLight / 8.f;
  LIGHT *= 16.f*2048.f;

	float ABSORB = 0.06f;
	if (fogAbsorb != 0) ABSORB = fogAbsorb;

	float inscatter = 0.f;
	if (fogScatter != 0) inscatter = fogScatter;

  float ambient = LIGHT * inscatter;
!

!shader_core

float maxZ = F[wF * cy + ax];

	float3 rayDir = fast_normalize(VVd + (-VVx * (ax - wF/2) + VVy * (cy - hF/2)) / vScale);
	float3 pos = VP + rayDir * (0.5f + 0.25f * (ax & 1) + 0.125f * (!(cy & 1)));

  float stepDist = 1.f;
  if (fogDist != 0) {
    stepDist = min(maxZ, min(40.f, fogDist))/NSAMPLES;
  }

	float light = 0.f;
	float rn = 0;
	float currDepth = dot(pos - VP, VVd);
	float transmit = 1.f;

	float RdotL = -dot(rayDir, LDir[0]);
	float phase = 0.5f * (1.f - G*G) / (4.f*3.14f* half_powr(1.f + G*G - 2.f*G * RdotL, 1.5f));
	phase += 0.5f * (1.f - GBACK*GBACK) / (4.f*3.14f* half_powr(1.f + GBACK*GBACK - 2.f*GBACK * RdotL, 1.5f));

	float totDensity = 0.f;
	for (rn = 0; (rn < NSAMPLES) && (currDepth < maxZ); rn += 1.f) {
		float depth = dot(pos - SP, SVd);
		int sx = (int)(dot(pos - SP, SVx) * sScale) + wS;
		int sy = (int)(dot(pos - SP, SVy) * -sScale) + wS;

    totDensity += stepDist;

		float scatter = 1/ABSORB * (half_exp(- ABSORB * currDepth) - half_exp(- ABSORB * (currDepth + stepDist)));

		if ((sx >= 0) && (sx < 2*wS-1) && (sy >= 0) && (sy < 2*wS-1)) {
			if (SD[2*wS * sy + sx] >= depth) light += LIGHT * scatter * phase;
			else light += ambient * scatter * phase;
		} else light += LIGHT * scatter * phase;
		pos += rayDir * stepDist;
		currDepth = dot(pos - VP, VVd);
	}

	light += (- 1.f / ABSORB) * (half_exp(-ABSORB * maxZ) - half_exp(-ABSORB * currDepth)) * ambient * phase;
	transmit = half_exp(- ABSORB * totDensity);

	float3 dl = LInt[0];

	Ro[wF * cy + ax] = light * dl.x + transmit * Ro[wF * cy + ax];
	Go[wF * cy + ax] = light * dl.y + transmit * Go[wF * cy + ax];
	Bo[wF * cy + ax] = light * dl.z + transmit * Bo[wF * cy + ax];

!