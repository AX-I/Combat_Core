
float3 rtt_and_odt_fit(float3 v) {
  float3 a = v * (v + 0.0245786f) - 0.000090537f;
  float3 b = v * (0.983729f * v + 0.4329510f) + 0.238081f;
  return a / b;
}

float3 acesMat(float3 px) {
  float3 j = (float3)(
    dot(px, (float3)(0.59719f, 0.35458f, 0.04823f)),
    dot(px, (float3)(0.07600f, 0.90834f, 0.01566f)),
    dot(px, (float3)(0.02840f, 0.13383f, 0.83777f))
  );
  j = rtt_and_odt_fit(j+0.001f);
  j = (float3)(
    dot(j, (float3)( 1.60475f, -0.53108f, -0.07367f)),
    dot(j, (float3)(-0.10208f,  1.10813f, -0.00605f)),
    dot(j, (float3)(-0.00327f, -0.07276f,  1.07602f))
  );
  j = sqrt(j);
  return j;
}

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
            float3 j = 8 * exposure * (float3)(Ro[wF * cy + cx], Go[wF * cy + cx], Bo[wF * cy + cx]);

           /*
            j = sqrt(j) / 1.1f;
            float m = max(j.x, max(j.y, j.z)) / 255.f;
            if (m > 1.f) {
              j = j / sqrt(m);
            }
           */
            j = max((float3)0.f, acesMat(j / 65535.f) * 255.f);

            Ro[wF * cy + cx] = (ushort)min(255.f, j.x);
            Go[wF * cy + cx] = (ushort)min(255.f, j.y);
            Bo[wF * cy + cx] = (ushort)min(255.f, j.z);
        }
    }
}
