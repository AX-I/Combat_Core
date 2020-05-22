// Outputs to normal buffer for Global Illumination.
// Could be precursor to deferred rendering.

__kernel void draw(__global int *TO,
                   __global ushort *Ro, __global ushort *Go, __global ushort *Bo,
                   __global float3 *No,
                   __global float *F, __global int2 *P, __global float *Z,
                   __global float2 *UV,
                   __global float3 *N,
                   __global ushort *TR, __global ushort *TG, __global ushort *TB,
                   const int wF, const int hF, const int lenP, const int lenT) {

    // Block index
    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if ((bx * BLOCK_SIZE + tx) < lenP) {

    // Index
    int txd = TO[bx*BLOCK_SIZE + tx];
    int ci = txd * 3;

    // get points
    float z1 = Z[ci];
    float z2 = Z[ci+1];
    float z3 = Z[ci+2];

    int2 xy1 = P[ci];
    int2 xy2 = P[ci+1];
    int2 xy3 = P[ci+2];
    float2 uv1 = UV[ci] * z1;
    float2 uv2 = UV[ci+1] * z2;
    float2 uv3 = UV[ci+2] * z3;
    float3 n1 = N[ci] * z1;
    float3 n2 = N[ci+1] * z2;
    float3 n3 = N[ci+2] * z3;

    int ytemp; int xtemp;
    float2 uvt;
    float3 nt; float zt;

    int x1 = xy1.x; int x2 = xy2.x; int x3 = xy3.x;
    int y1 = xy1.y; int y2 = xy2.y; int y3 = xy3.y;

    // bubble sort y1<y2<y3
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; uvt = uv1; nt = n1; zt = z1;
      y1 = y2; x1 = x2; uv1 = uv2; n1 = n2; z1 = z2;
      y2 = ytemp; x2 = xtemp; uv2 = uvt; n2 = nt; z2 = zt;
    }
    if (y2 > y3) {
      ytemp = y2; xtemp = x2; uvt = uv2; nt = n2; zt = z2;
      y2 = y3; x2 = x3; uv2 = uv3; n2 = n3; z2 = z3;
      y3 = ytemp; x3 = xtemp; uv3 = uvt; n3 = nt; z3 = zt;
    }
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; uvt = uv1; nt = n1; zt = z1;
      y1 = y2; x1 = x2; uv1 = uv2; n1 = n2; z1 = z2;
      y2 = ytemp; x2 = xtemp; uv2 = uvt; n2 = nt; z2 = zt;
    }


    if ((y1 < hF) && (y3 >= 0)) {

    float u1 = uv1.x; float u2 = uv2.x; float u3 = uv3.x;
    float v1 = uv1.y; float v2 = uv2.y; float v3 = uv3.y;

    float ydiff1 = (float)(y2 - y1)/(float)(y3-y1);
    int x4 = (int)(x1 + ydiff1 * (x3 - x1));
    int y4 = y2;
    float u4 = u1 + ydiff1 * (u3 - u1);
    float v4 = v1 + ydiff1 * (v3 - v1);
    float3 n4 = n1 + ydiff1 * (n3 - n1);
    float z4 = z1 + ydiff1 * (z3 - z1);

    // fill bottom flat triangle
    ydiff1 = 1 / (float)(y2-y1);
    float slope1 = (float)(x2-x1) * ydiff1;
    float slopeu1 = (u2-u1) * ydiff1;
    float slopev1 = (v2-v1) * ydiff1;
    float3 slopen1 = (n2-n1) * ydiff1;
    float slopez1 = (z2-z1) * ydiff1;

    ydiff1 = 1 / (float)(y4-y1);
    float slope2 = (float)(x4-x1) * ydiff1;
    float slopeu2 = (u4-u1) * ydiff1;
    float slopev2 = (v4-v1) * ydiff1;
    float3 slopen2 = (n4-n1) * ydiff1;
    float slopez2 = (z4-z1) * ydiff1;

    float cx1 = x1; float cx2 = x1;
    float cu1 = u1; float cv1 = v1;
    float cu2 = u1; float cv2 = v1;
    float3 cn1 = n1; float3 cn2 = n1;
    float cz1 = z1; float cz2 = z1;

    float slopet; float ut; float vt;
    if (slope1 < slope2) {
      slopet = slope1; ut = slopeu1; vt = slopev1; nt = slopen1; zt = slopez1;
      slope1 = slope2; slopeu1 = slopeu2; slopev1 = slopev2; slopen1 = slopen2; slopez1 = slopez2;
      slope2 = slopet; slopeu2 = ut; slopev2 = vt; slopen2 = nt; slopez2 = zt;
    }

    for (int cy = y1; cy <= y2; cy++) {
        for (int ax = (int)cx2; ax <= (int)cx1; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max(0.f, min(1.f, t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                F[wF * cy + ax] = tz;
                float texr1 = ((1-t)*cu2 + t*cu1) * tz * lenT;
                int tex1 = (int)texr1;
                texr1 -= tex1;
                tex1 = abs(tex1) % lenT;
                float texr2 = lenT * ((1-t)*cv2 + t*cv1) * tz;
                int tex2 = (int)texr2;
                texr2 -= tex2;
                tex2 = abs(tex2) % lenT;

                int tex = tex1 + lenT*tex2;
                int tex10 = min(tex1+1, lenT-1) + lenT*tex2;
                int tex01 = tex1 + lenT*min(tex2+1, lenT-1);
                int tex11 = min(tex1+1, lenT-1) + lenT*min(tex2+1, lenT-1);
                float texi1 = 1-texr1;
                float texi2 = 1-texr2;

                Ro[wF * cy + ax] = texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
                                   texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11];
                Go[wF * cy + ax] = texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
                                   texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11];
                Bo[wF * cy + ax] = texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
                                   texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11];

                float3 norm = fast_normalize(((1-t)*cn2 + t*cn1) * tz);
                No[wF * cy + ax] = norm;
              }
            }
        }
        cx1 += slope1;
        cx2 += slope2;
        cu1 += slopeu1;
        cv1 += slopev1;
        cu2 += slopeu2;
        cv2 += slopev2;
        cn1 += slopen1;
        cn2 += slopen2;
        cz1 += slopez1;
        cz2 += slopez2;
    }

    // fill top flat triangle
    ydiff1 = 1 / (float)(y3-y2);
    slope1 = (float)(x3-x2) * ydiff1;
    slopeu1 = (u3-u2) * ydiff1;
    slopev1 = (v3-v2) * ydiff1;
    slopen1 = (n3-n2) * ydiff1;
    slopez1 = (z3-z2) * ydiff1;

    ydiff1 = 1 / (float)(y3-y4);
    slope2 = (float)(x3-x4) * ydiff1;
    slopeu2 = (u3-u4) * ydiff1;
    slopev2 = (v3-v4) * ydiff1;
    slopen2 = (n3-n4) * ydiff1;
    slopez2 = (z3-z4) * ydiff1;

    cx1 = x3; cx2 = x3;
    cu1 = u3; cv1 = v3;
    cu2 = u3; cv2 = v3;
    cn1 = n3; cn2 = n3;
    cz1 = z3; cz2 = z3;

    if (slope1 < slope2) {
      slopet = slope1; ut = slopeu1; vt = slopev1; nt = slopen1; zt = slopez1;
      slope1 = slope2; slopeu1 = slopeu2; slopev1 = slopev2; slopen1 = slopen2; slopez1 = slopez2;
      slope2 = slopet; slopeu2 = ut; slopev2 = vt; slopen2 = nt; slopez2 = zt;
    }

    for (int cy = y3; cy >= y2; cy--) {
        for (int ax = (int)cx1; ax <= (int)cx2; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max(0.f, min(1.f, t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                F[wF * cy + ax] = tz;
                float texr1 = ((1-t)*cu2 + t*cu1) * tz * lenT;
                int tex1 = (int)texr1;
                texr1 -= tex1;
                tex1 = abs(tex1) % lenT;
                float texr2 = lenT * ((1-t)*cv2 + t*cv1) * tz;
                int tex2 = (int)texr2;
                texr2 -= tex2;
                tex2 = abs(tex2) % lenT;

                int tex = tex1 + lenT*tex2;
                int tex10 = min(tex1+1, lenT-1) + lenT*tex2;
                int tex01 = tex1 + lenT*min(tex2+1, lenT-1);
                int tex11 = min(tex1+1, lenT-1) + lenT*min(tex2+1, lenT-1);
                float texi1 = 1-texr1;
                float texi2 = 1-texr2;

                Ro[wF * cy + ax] = texi1*texi2*TR[tex] + texr1*texi2*TR[tex10] +
                                   texi1*texr2*TR[tex01] + texr1*texr2*TR[tex11];
                Go[wF * cy + ax] = texi1*texi2*TG[tex] + texr1*texi2*TG[tex10] +
                                   texi1*texr2*TG[tex01] + texr1*texr2*TG[tex11];
                Bo[wF * cy + ax] = texi1*texi2*TB[tex] + texr1*texi2*TB[tex10] +
                                   texi1*texr2*TB[tex01] + texr1*texr2*TB[tex11];

                float3 norm = fast_normalize(((1-t)*cn2 + t*cn1) * tz);
                No[wF * cy + ax] = norm;
              }
            }
        }
        cx1 -= slope1;
        cx2 -= slope2;
        cu1 -= slopeu1;
        cv1 -= slopev1;
        cu2 -= slopeu2;
        cv2 -= slopev2;
        cn1 -= slopen1;
        cn2 -= slopen2;
        cz1 -= slopez1;
        cz2 -= slopez2;
    }
    }
    }
}
