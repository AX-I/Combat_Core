#define EXPOSURE 0.25f
#define SAMPLES 8.f

__kernel void blur(
	__global ushort *Ro, __global ushort *Go, __global ushort *Bo, __global float *F,
    __global ushort *R2, __global ushort *G2, __global ushort *B2,

    __constant float *Vpos,
    __constant float3 *VV, const float sScale,
    const float3 oldPos,
    const float3 oldVV, const float3 oldVX, const float3 oldVY,

    const int wF, const int hF, const int BS,
    const int stepW, const int stepH) {

    int bx = get_group_id(0);
    int by = get_group_id(1);
    int tx = get_local_id(0);
    int ty = get_local_id(1);

    int ci = bx * BS + tx;
    int cj = by * BS + ty;

    int h1 = stepH * cj;
    int h2 = stepH * (cj+1);

    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
	float3 Vd = VV[0];
	float3 Vx = VV[1];
    float3 Vy = VV[2];


    for (int cy = h1; cy < min(h2, hF); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {

			float d = F[wF*cy + cx];
	        float3 worldPos = vp - oldPos + d * (Vd - (cx-wF/2)/sScale * Vx + (cy-hF/2)/sScale * Vy);

	        float oldZ = dot(worldPos, oldVV);
	        float oldX = (dot(worldPos, oldVX) / oldZ) * -sScale + wF/2;
	        float oldY = (dot(worldPos, oldVY) / oldZ) * sScale + hF/2;

	        float outR = 0;
	        float outG = 0;
	        float outB = 0;
	        float dy = oldY - cy;
	        float dx = oldX - cx;
	        for (float i=0; i <= SAMPLES; i+= 1) {
			    int sy = clamp(cy + i/SAMPLES*EXPOSURE * dy, 0.f, (float)hF-1);
			    int sx = clamp(cx + i/SAMPLES*EXPOSURE * dx, 0.f, (float)wF-1);
			    outR += Ro[wF * sy + sx];
			    outG += Go[wF * sy + sx];
			    outB += Bo[wF * sy + sx];

			}

			R2[wF * cy + cx] = outR / SAMPLES;
			G2[wF * cy + cx] = outG / SAMPLES;
			B2[wF * cy + cx] = outB / SAMPLES;

            //R2[wF * cy + cx] = Ro[wF * targY + targX];
            //G2[wF * cy + cx] = Go[wF * targY + targX];
            //B2[wF * cy + cx] = Bo[wF * targY + targX];


        }
    }
}
