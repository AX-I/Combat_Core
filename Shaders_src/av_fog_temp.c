// Raymarch fog with 2-lobe HG phase function

#define NSAMPLES 4
#define DIST 1.f
#define LIGHT 2048.f
#define ABSORB 0.06f
#define G 0.5f
#define GBACK -0.25f

!shader_args

__constant float *Vpos, __constant float3 *VV, const float vScale,

__constant float3 *LInt,
__constant float3 *LDir,

__global float *SD, const int wS, const float sScale,
__constant float3 *SV, __constant float *SPos,

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
!

!shader_core

float maxZ = F[wF * cy + ax];

	float3 rayDir = fast_normalize(VVd + (-VVx * (ax - wF/2) + VVy * (cy - hF/2)) / vScale);
	float3 pos = VP + rayDir * (0.5f + 0.25f * (ax & 1) + 0.125f * (!(cy & 1)));

	float light = 0.f;
	float rn = 0;
	float currDepth = dot(pos - VP, VVd);
	float transmit = 1.f;

	float inscatter = 0.f;
	float RdotL = -dot(rayDir, LDir[0]);
	float phase = 0.5f * (1.f - G*G) / (4.f*3.14f* half_powr(1.f + G*G - 2.f*G * RdotL, 1.5f));
	phase += 0.5f * (1.f - GBACK*GBACK) / (4.f*3.14f* half_powr(1.f + GBACK*GBACK - 2.f*GBACK * RdotL, 1.5f));

	for (rn = 0; (rn < NSAMPLES) && (currDepth < maxZ); rn += 1.f) {
		float depth = dot(pos - SP, SVd);
		int sx = (int)(dot(pos - SP, SVx) * sScale) + wS;
		int sy = (int)(dot(pos - SP, SVy) * -sScale) + wS;

		float scatter = half_exp(- ABSORB * currDepth);

		if ((sx >= 0) && (sx < 2*wS-1) && (sy >= 0) && (sy < 2*wS-1)) {
			if (SD[2*wS * sy + sx] >= depth) light += LIGHT * scatter * phase;
			else light += LIGHT * inscatter * scatter;
		}
		pos += rayDir * DIST;
		currDepth = dot(pos - VP, VVd);
	}

	light += (- 1.f / ABSORB) * (half_exp(-ABSORB * maxZ) - half_exp(-ABSORB * currDepth)) * LIGHT * phase;
	transmit = half_exp(- ABSORB * maxZ);

	float3 dl = LInt[0];

	Ro[wF * cy + ax] = light * dl.x + transmit * Ro[wF * cy + ax];
	Go[wF * cy + ax] = light * dl.y + transmit * Go[wF * cy + ax];
	Bo[wF * cy + ax] = light * dl.z + transmit * Bo[wF * cy + ax];

!