__kernel void blurV(__global ushort3 *Ro,
                    __global ushort3 *Rt,
                    __global ushort3 *r2,
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

    for (int cy = h1; cy < min(h2, hF-1); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
            float3 a = (float3)0;
              a = (cy<=8) ? a : a + 0.00816f*convert_float3(Ro[wF * (cy-9) + cx]);
              a = (cy<=7) ? a : a + 0.01384f*convert_float3(Ro[wF * (cy-8) + cx]);
              a = (cy<=6) ? a : a + 0.02207f*convert_float3(Ro[wF * (cy-7) + cx]);
              a = (cy<=5) ? a : a + 0.03306f*convert_float3(Ro[wF * (cy-6) + cx]);
              a = (cy<=4) ? a : a + 0.04654f*convert_float3(Ro[wF * (cy-5) + cx]);
              a = (cy<=3) ? a : a + 0.06157f*convert_float3(Ro[wF * (cy-4) + cx]);
              a = (cy<=2) ? a : a + 0.07654f*convert_float3(Ro[wF * (cy-3) + cx]);
              a = (cy<=1) ? a : a + 0.08941f*convert_float3(Ro[wF * (cy-2) + cx]);
              a = (cy<=0) ? a : a + 0.09815f*convert_float3(Ro[wF * (cy-1) + cx]);
              a += 0.10125f*convert_float3(Ro[wF * cy + cx]);
              a = (cy>=(wF-1)) ? a : a + 0.09815f*convert_float3(Ro[wF * (cy+1) + cx]);
              a = (cy>=(wF-2)) ? a : a + 0.08941f*convert_float3(Ro[wF * (cy+2) + cx]);
              a = (cy>=(wF-3)) ? a : a + 0.07654f*convert_float3(Ro[wF * (cy+3) + cx]);
              a = (cy>=(wF-4)) ? a : a + 0.06157f*convert_float3(Ro[wF * (cy+4) + cx]);
              a = (cy>=(wF-5)) ? a : a + 0.04654f*convert_float3(Ro[wF * (cy+5) + cx]);
              a = (cy>=(wF-6)) ? a : a + 0.03306f*convert_float3(Ro[wF * (cy+6) + cx]);
              a = (cy>=(wF-7)) ? a : a + 0.02207f*convert_float3(Ro[wF * (cy+7) + cx]);
              a = (cy>=(wF-8)) ? a : a + 0.01384f*convert_float3(Ro[wF * (cy+8) + cx]);
              a = (cy>=(wF-9)) ? a : a + 0.00816f*convert_float3(Ro[wF * (cy+9) + cx]);
              a /= 0.9f;

              Rt[wF * cy + cx] = convert_ushort3_sat(a);
        }
    }

    barrier(CLK_GLOBAL_MEM_FENCE);

    wF = wF*2; hF = hF*2; stepH = stepH*2;
    h1 = stepH * cj;
    h2 = stepH * (cj+1);
    int lenT = wF/2;

    for (int cy = h1; cy < min(h2, hF); cy++) {
        for (int cx = ci; cx < wF; cx += stepW) {
                float texr1 = cx/2.f;
                int tex1 = (int)texr1;
                texr1 -= tex1;
                float texr2 = cy/2.f;
                int tex2 = (int)texr2;
                texr2 -= tex2;

                int tex = tex1 + lenT*tex2;
                int tex10 = min(tex1+1, lenT-1) + lenT*tex2;
                int tex01 = tex1 + lenT*min(tex2+1, hF/2-2);
                int tex11 = min(tex1+1, lenT-1) + lenT*min(tex2+1, hF/2-2);
                float texi1 = 1-texr1;
                float texi2 = 1-texr2;

          r2[wF * cy + cx] = convert_ushort3_sat(
            convert_float3(r2[wF * cy + cx]) + (
              texi1*texi2*convert_float3(Rt[tex]) +
              texr1*texi2*convert_float3(Rt[tex10]) +
              texi1*texr2*convert_float3(Rt[tex01]) +
              texr1*texr2*convert_float3(Rt[tex11]))
          );
        }
    }
}
