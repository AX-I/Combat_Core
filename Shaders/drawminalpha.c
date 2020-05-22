
__kernel void draw(__global int *TO,
                   __global float *F, __global int2 *P, __global float *Z,
                   __global float2 *UV,
                   __global bool *TA, int lenT,
                   int wF, int hF, int lenP) {

    // F => depth buffer, P => screenpoints, Z => 1/depths

    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if ((bx * BLOCK_SIZE + tx) < lenP) {
    int txd = TO[bx*BLOCK_SIZE + tx];
    int ci = txd * 3;

    float z1 = Z[ci];
    float z2 = Z[ci+1];
    float z3 = Z[ci+2];

    int2 xy1 = P[ci];
    int2 xy2 = P[ci+1];
    int2 xy3 = P[ci+2];
    float2 uv1 = UV[ci] * z1;
    float2 uv2 = UV[ci+1] * z2;
    float2 uv3 = UV[ci+2] * z3;
    int ytemp; int xtemp;
    float zt; float2 uvt; float vt;
    int x1 = xy1.x; int x2 = xy2.x; int x3 = xy3.x;
    int y1 = xy1.y; int y2 = xy2.y; int y3 = xy3.y;

    // sort y1<y2<y3
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; uvt = uv1; zt = z1;
      y1 = y2; x1 = x2; uv1 = uv2; z1 = z2;
      y2 = ytemp; x2 = xtemp; uv2 = uvt; z2 = zt;
    }
    if (y2 > y3) {
      ytemp = y2; xtemp = x2; uvt = uv2; zt = z2;
      y2 = y3; x2 = x3; uv2 = uv3; z2 = z3;
      y3 = ytemp; x3 = xtemp; uv3 = uvt;z3 = zt;
    }
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; uvt = uv1; zt = z1;
      y1 = y2; x1 = x2; uv1 = uv2; z1 = z2;
      y2 = ytemp; x2 = xtemp; uv2 = uvt; z2 = zt;
    }

    if ((y1 < hF) && (y3 >= 0)) {

    float u1 = uv1.x; float u2 = uv2.x; float u3 = uv3.x;
    float v1 = uv1.y; float v2 = uv2.y; float v3 = uv3.y;
    int x4 = (int)(x1 + ((float)(y2 - y1)/(float)(y3-y1)) * (x3-x1));
    int y4 = y2;
    float u4 = u1 + (float)(y2 - y1)/(float)(y3-y1) * (u3 - u1);
    float v4 = v1 + (float)(y2 - y1)/(float)(y3-y1) * (v3 - v1);
    float z4 = z1 + (float)(y2 - y1)/(float)(y3-y1) * (z3 - z1);

    // fill bottom flat triangle
    float slope1 = (float)(x2-x1) / (float)(y2-y1);
    float slope2 = (float)(x4-x1) / (float)(y4-y1);
    float slopeu1 = (u2-u1) / (float)(y2-y1);
    float slopev1 = (v2-v1) / (float)(y2-y1);
    float slopeu2 = (u4-u1) / (float)(y4-y1);
    float slopev2 = (v4-v1) / (float)(y4-y1);
    float slopez1 = (z2-z1) / (float)(y2-y1);
    float slopez2 = (z4-z1) / (float)(y4-y1);
    float cx1 = x1; float cx2 = x1;
    float cu1 = u1; float cv1 = v1;
    float cu2 = u1; float cv2 = v1;
    float cz1 = z1; float cz2 = z1;

    float slopet; float ut; float vt;
    if (slope1 < slope2) {
      slopet = slope1; ut = slopeu1; vt = slopev1; zt = slopez1;
      slope1 = slope2; slopeu1 = slopeu2; slopev1 = slopev2; slopez1 = slopez2;
      slope2 = slopet; slopeu2 = ut; slopev2 = vt; slopez2 = zt;
    }
    for (int cy = y1; cy <= y2; cy++) {
        for (int ax = (int)cx2; ax <= (int)cx1; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max((float)0., min((float)1., t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                int tex1 = (int)(((1-t)*cu2 + t*cu1) * tz * (lenT-1));
                tex1 = abs(tex1) & (lenT - 1);
                int tex2 = (int)((lenT-1) * ((1-t)*cv2 + t*cv1) * tz);
                tex2 = abs(tex2) & (lenT - 1);
                tex2 *= lenT;
                int tex = tex1 + tex2;
                //if ((tex > (lenT * lenT - 1)) || (tex < 0)) printf("t %d l %d \n", tex, lenT);
                //if ((bx == 0) && (tx == 0)) printf("t %d l %d \n", tex, lenT);
                if (TA[tex]) {
                  F[wF * cy + ax] = tz;
                }
              }
            }
        }
        cx1 += slope1;
        cx2 += slope2;
        cz1 += slopez1;
        cz2 += slopez2;
        cu1 += slopeu1;
        cv1 += slopev1;
        cu2 += slopeu2;
        cv2 += slopev2;
    }

    // fill top flat triangle
    slope1 = (float)(x3-x2) / (float)(y3-y2);
    slope2 = (float)(x3-x4) / (float)(y3-y4);
    slopeu1 = (u3-u2) / (float)(y3-y2);
    slopev1 = (v3-v2) / (float)(y3-y2);
    slopeu2 = (u3-u4) / (float)(y3-y4);
    slopev2 = (v3-v4) / (float)(y3-y4);
    slopez1 = (z3-z2) / (float)(y3-y2);
    slopez2 = (z3-z4) / (float)(y3-y4);
    cx1 = x3; cx2 = x3;
    cu1 = u3; cv1 = v3;
    cu2 = u3; cv2 = v3;
    cz1 = z3; cz2 = z3;

    if (slope1 < slope2) {
      slopet = slope1; ut = slopeu1; vt = slopev1; zt = slopez1;
      slope1 = slope2; slopeu1 = slopeu2; slopev1 = slopev2; slopez1 = slopez2;
      slope2 = slopet; slopeu2 = ut; slopev2 = vt; slopez2 = zt;
    }
    for (int cy = y3; cy > y2; cy--) {
        for (int ax = (int)cx1; ax <= (int)cx2; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max((float)0., min((float)1., t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                int tex1 = (int)(((1-t)*cu2 + t*cu1) * tz * (lenT-1));
                tex1 = abs(tex1) & (lenT - 1);
                int tex2 = (int)((lenT-1) * ((1-t)*cv2 + t*cv1) * tz);
                tex2 = abs(tex2) & (lenT - 1);
                tex2 *= lenT;
                int tex = tex1 + tex2;
                //if ((tex > (lenT * lenT - 1)) || (tex < 0)) printf("t %d l %d \n", tex, lenT);
                //if ((bx == 0) && (tx == 0)) printf("t %d l %d \n", tex, lenT);
                if (TA[tex]) {
                  F[wF * cy + ax] = tz;
                }
              }
            }
        }
        cx1 -= slope1;
        cx2 -= slope2;
        cu1 -= slopeu1;
        cv1 -= slopev1;
        cu2 -= slopeu2;
        cv2 -= slopev2;
        cz1 -= slopez1;
        cz2 -= slopez2;
    }
    }
    }
}
