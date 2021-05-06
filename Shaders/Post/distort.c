#define dsize 64.f
#define fade 128
#define fadeZ 4.f

__kernel void distort(
	__global ushort *Ro, __global ushort *Go, __global ushort *Bo, __global float *F,
    __global ushort *R2, __global ushort *G2, __global ushort *B2,
    const float x, const float y, const float z, const float portal, const float strength,
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

    for (int cy = h1; cy < min(h2, hF); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
			float2 offset = (float2)(cx - x*wF, cy - y*hF);
			float dist = fast_length(offset);
			dist = max(0.f, dist - portal) / dsize;


			//float factor = -p * 1 / (1+dist);
			float factor = strength * sin(1/(dist*dist + 0.213f));

			// Fade out
			if ((cx < fade) || (cx >= wF-fade)) {
				factor *= (float)min(cx, wF-cx) / fade;
			} if ((cy < fade) || (cy >= hF-fade)) {
				factor *= (float)min(cy, hF-cy) / fade;
			}

			if (F[wF * cy + cx] < z) {
				factor *= 1.f - min(1.f, (z - F[wF * cy + cx]) / fadeZ);
			}
			if (dist == 0) factor = 0;

			offset = fast_normalize(offset);

			int targX = max(0.f, min(wF-1.f, cx + factor * offset.x));
			int targY = max(0.f, min(hF-1.f, cy + factor * offset.y));

            R2[wF * cy + cx] = Ro[wF * targY + targX];
            G2[wF * cy + cx] = Go[wF * targY + targX];
            B2[wF * cy + cx] = Bo[wF * targY + targX];

        }
    }
}
