__kernel void blurH(__global ushort3 *r2,
                    __global ushort3 *Rt,
                    __global ushort3 *Ro,
                    int wF, int hF, const int BS,
                    int stepW, float stepH) {

    int bx = get_group_id(0);
    int by = get_group_id(1);
    int tx = get_local_id(0);
    int ty = get_local_id(1);

    int ci = bx * BS + tx;
    int cj = by * BS + ty;

    int h1 = stepH * cj;
    int h2 = stepH * (cj+1);

    wF = wF/2; hF = hF/2; stepH = stepH/2;
    h1 = stepH * cj;
    h2 = stepH * (cj+1);

    for (int cy = h1; cy < min(h2, hF-2); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
          int y1 = min(wF*(hF-1)*4, wF*cy*4+1);
          int x1 = min(wF*2-1, cx*2+1);
          float3 cr = convert_float3(r2[wF*cy*4 + cx*2]/4 + r2[y1 + cx*2]/4 + r2[wF*cy*4 + x1]/4 + r2[y1 + x1]/4);
          float lum = dot((float3)(0.3626f, 0.5152f, 0.1222f), cr);
          Ro[wF * cy + cx] = convert_ushort3(cr*lum/256/256);
        }
    }

    barrier(CLK_GLOBAL_MEM_FENCE);

    for (int cy = h1; cy < min(h2, hF-1); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
            float3 a = (float3)0;
                a = (cx<=8) ? a : a + 0.00816f*convert_float3(Ro[wF * cy + cx-9]);
                a = (cx<=7) ? a : a + 0.01384f*convert_float3(Ro[wF * cy + cx-8]);
                a = (cx<=6) ? a : a + 0.02207f*convert_float3(Ro[wF * cy + cx-7]);
                a = (cx<=5) ? a : a + 0.03306f*convert_float3(Ro[wF * cy + cx-6]);
                a = (cx<=4) ? a : a + 0.04654f*convert_float3(Ro[wF * cy + cx-5]);
                a = (cx<=3) ? a : a + 0.06157f*convert_float3(Ro[wF * cy + cx-4]);
                a = (cx<=2) ? a : a + 0.07654f*convert_float3(Ro[wF * cy + cx-3]);
                a = (cx<=1) ? a : a + 0.08941f*convert_float3(Ro[wF * cy + cx-2]);
                a = (cx<=0) ? a : a + 0.09815f*convert_float3(Ro[wF * cy + cx-1]);
                a += 0.10125f*convert_float3(Ro[wF * cy + cx]);
                a = (cx>=(wF-1)) ? a : a + 0.09815f*convert_float3(Ro[wF * cy + cx+1]);
                a = (cx>=(wF-2)) ? a : a + 0.08941f*convert_float3(Ro[wF * cy + cx+2]);
                a = (cx>=(wF-3)) ? a : a + 0.07654f*convert_float3(Ro[wF * cy + cx+3]);
                a = (cx>=(wF-4)) ? a : a + 0.06157f*convert_float3(Ro[wF * cy + cx+4]);
                a = (cx>=(wF-5)) ? a : a + 0.04654f*convert_float3(Ro[wF * cy + cx+5]);
                a = (cx>=(wF-6)) ? a : a + 0.03306f*convert_float3(Ro[wF * cy + cx+6]);
                a = (cx>=(wF-7)) ? a : a + 0.02207f*convert_float3(Ro[wF * cy + cx+7]);
                a = (cx>=(wF-8)) ? a : a + 0.01384f*convert_float3(Ro[wF * cy + cx+8]);
                a = (cx>=(wF-9)) ? a : a + 0.00816f*convert_float3(Ro[wF * cy + cx+9]);
                a /= 0.9f;

                Rt[wF * cy + cx] = convert_ushort3_sat(a);
        }
    }
}
