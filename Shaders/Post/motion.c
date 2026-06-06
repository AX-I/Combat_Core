#define EXPOSURE 0.25f
#define SAMPLES 16.f
#define SSKIP 4.f

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

	        float outR = Ro[wF * cy + cx] * 0.0001f;
	        float outG = Go[wF * cy + cx] * 0.0001f;
	        float outB = Bo[wF * cy + cx] * 0.0001f;
	        float accum = 1.f * 0.0001;

	        float dy = oldY - cy;
	        float dx = oldX - cx;

          float offset = ((cx&1)^(cy&1))*0.5f + (cx&1) * 0.25f;

			for (float i=offset*SSKIP; i <= SAMPLES; i+= SSKIP) {
			    int sy = clamp(cy + i/SAMPLES*EXPOSURE * dy, 0.f, (float)hF-1);
			    int sx = clamp(cx + i/SAMPLES*EXPOSURE * dx, 0.f, (float)wF-1);
			    outR += Ro[wF * sy + sx];
			    outG += Go[wF * sy + sx];
			    outB += Bo[wF * sy + sx];
          accum += 1.f;

			}

			R2[wF * cy + cx] = outR / accum;
			G2[wF * cy + cx] = outG / accum;
			B2[wF * cy + cx] = outB / accum;

            //R2[wF * cy + cx] = Ro[wF * targY + targX];
            //G2[wF * cy + cx] = Go[wF * targY + targX];
            //B2[wF * cy + cx] = Bo[wF * targY + targX];


        }
    }
}
