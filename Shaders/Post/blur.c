__kernel void blurH(__global ushort *r2, __global ushort *g2, __global ushort *b2,
                    __global ushort *Rt, __global ushort *Gt, __global ushort *Bt,
                    __global ushort *Ro, __global ushort *Go, __global ushort *Bo,
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
          float cr = r2[wF*cy*4 + cx*2]/4 + r2[y1 + cx*2]/4 + r2[wF*cy*4 + x1]/4 + r2[y1 + x1]/4;
          float cg = g2[wF*cy*4 + cx*2]/4 + g2[y1 + cx*2]/4 + g2[wF*cy*4 + x1]/4 + g2[y1 + x1]/4;
          float cb = b2[wF*cy*4 + cx*2]/4 + b2[y1 + cx*2]/4 + b2[wF*cy*4 + x1]/4 + b2[y1 + x1]/4;
          float lum = 0.3626*cr + 0.5152*cg + 0.1222*cb;
          Ro[wF * cy + cx] = cr*lum/256/256;
          Go[wF * cy + cx] = cg*lum/256/256;
          Bo[wF * cy + cx] = cb*lum/256/256;
        }
    }

    barrier(CLK_GLOBAL_MEM_FENCE);

    for (int cy = h1; cy < min(h2, hF-1); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
            float3 a = (float3)0;
                a = (cx<=8) ? a : a + 0.00816f*(float3)(Ro[wF * cy + cx-9], Go[wF * cy + cx-9], Bo[wF * cy + cx-9]);
                a = (cx<=7) ? a : a + 0.01384f*(float3)(Ro[wF * cy + cx-8], Go[wF * cy + cx-8], Bo[wF * cy + cx-8]);
                a = (cx<=6) ? a : a + 0.02207f*(float3)(Ro[wF * cy + cx-7], Go[wF * cy + cx-7], Bo[wF * cy + cx-7]);
                a = (cx<=5) ? a : a + 0.03306f*(float3)(Ro[wF * cy + cx-6], Go[wF * cy + cx-6], Bo[wF * cy + cx-6]);
                a = (cx<=4) ? a : a + 0.04654f*(float3)(Ro[wF * cy + cx-5], Go[wF * cy + cx-5], Bo[wF * cy + cx-5]);
                a = (cx<=3) ? a : a + 0.06157f*(float3)(Ro[wF * cy + cx-4], Go[wF * cy + cx-4], Bo[wF * cy + cx-4]);
                a = (cx<=2) ? a : a + 0.07654f*(float3)(Ro[wF * cy + cx-3], Go[wF * cy + cx-3], Bo[wF * cy + cx-3]);
                a = (cx<=1) ? a : a + 0.08941f*(float3)(Ro[wF * cy + cx-2], Go[wF * cy + cx-2], Bo[wF * cy + cx-2]);
                a = (cx<=0) ? a : a + 0.09815f*(float3)(Ro[wF * cy + cx-1], Go[wF * cy + cx-1], Bo[wF * cy + cx-1]);
                a += 0.10125f*(float3)(Ro[wF * cy + cx], Go[wF * cy + cx], Bo[wF * cy + cx]);
                a = (cx>=(wF-1)) ? a : a + 0.09815f*(float3)(Ro[wF * cy + cx+1], Go[wF * cy + cx+1], Bo[wF * cy + cx+1]);
                a = (cx>=(wF-2)) ? a : a + 0.08941f*(float3)(Ro[wF * cy + cx+2], Go[wF * cy + cx+2], Bo[wF * cy + cx+2]);
                a = (cx>=(wF-3)) ? a : a + 0.07654f*(float3)(Ro[wF * cy + cx+3], Go[wF * cy + cx+3], Bo[wF * cy + cx+3]);
                a = (cx>=(wF-4)) ? a : a + 0.06157f*(float3)(Ro[wF * cy + cx+4], Go[wF * cy + cx+4], Bo[wF * cy + cx+4]);
                a = (cx>=(wF-5)) ? a : a + 0.04654f*(float3)(Ro[wF * cy + cx+5], Go[wF * cy + cx+5], Bo[wF * cy + cx+5]);
                a = (cx>=(wF-6)) ? a : a + 0.03306f*(float3)(Ro[wF * cy + cx+6], Go[wF * cy + cx+6], Bo[wF * cy + cx+6]);
                a = (cx>=(wF-7)) ? a : a + 0.02207f*(float3)(Ro[wF * cy + cx+7], Go[wF * cy + cx+7], Bo[wF * cy + cx+7]);
                a = (cx>=(wF-8)) ? a : a + 0.01384f*(float3)(Ro[wF * cy + cx+8], Go[wF * cy + cx+8], Bo[wF * cy + cx+8]);
                a = (cx>=(wF-9)) ? a : a + 0.00816f*(float3)(Ro[wF * cy + cx+9], Go[wF * cy + cx+9], Bo[wF * cy + cx+9]);
                a /= 0.9f;

                Rt[wF * cy + cx] = convert_ushort_sat(a.x);
                Gt[wF * cy + cx] = convert_ushort_sat(a.y);
                Bt[wF * cy + cx] = convert_ushort_sat(a.z);
        }
    }
}
