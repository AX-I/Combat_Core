
__kernel void g(__global ushort *Ro, __global ushort *Go, __global ushort *Bo,
                const float exposure,
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
            ushort3 i = (ushort3)(Ro[wF * cy + cx], Go[wF * cy + cx], Bo[wF * cy + cx]);
            float3 j = sqrt(8*exposure*convert_float3(i)) / 1.1f;
            float m = max(j.x, max(j.y, j.z)) / 255.f;
            if (m > 1.f) {
              j = j / sqrt(m);
            }
            Ro[wF * cy + cx] = (ushort)min(255.f, j.x);
            Go[wF * cy + cx] = (ushort)min(255.f, j.y);
            Bo[wF * cy + cx] = (ushort)min(255.f, j.z);
        }
    }
}
