
__kernel void draw(__global int *TO,
                   __global float *F, __global int2 *P, __global float *Z,
                   int wF, int hF, int lenP) {

    // F => depth buffer, P => screenpoints, Z => 1/depths

    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if ((bx * BLOCK_SIZE + tx) < lenP) {
    int txd = TO[bx*BLOCK_SIZE + tx];
    //printf("tx %d txd %d \n", tx, txd);
    int ci = txd * 3;
    
    float z1 = Z[ci];
    float z2 = Z[ci+1];
    float z3 = Z[ci+2];
    
    int2 xy1 = P[ci];
    int2 xy2 = P[ci+1];
    int2 xy3 = P[ci+2];
    //printf("tx %d z %f %f %f \n", tx, z1, z2, z3);
    //printf("tx %d xy %d %d %d %d %d %d \n", tx, xy1.x, xy1.y, xy2.x, xy2.y, xy3.x, xy3.y);
    int ytemp; int xtemp;
    float zt;
    int x1 = xy1.x; int x2 = xy2.x; int x3 = xy3.x;
    int y1 = xy1.y; int y2 = xy2.y; int y3 = xy3.y;

    // sort y1<y2<y3
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; zt = z1;
      y1 = y2; x1 = x2; z1 = z2;
      y2 = ytemp; x2 = xtemp; z2 = zt;
    }
    if (y2 > y3) {
      ytemp = y2; xtemp = x2; zt = z2;
      y2 = y3; x2 = x3; z2 = z3;
      y3 = ytemp; x3 = xtemp; z3 = zt;
    }
    if (y1 > y2) {
      ytemp = y1; xtemp = x1; zt = z1;
      y1 = y2; x1 = x2; z1 = z2;
      y2 = ytemp; x2 = xtemp; z2 = zt;
    }

    if ((y1 < hF) && (y3 >= 0)) {

    int x4 = (int)(x1 + ((float)(y2 - y1)/(float)(y3-y1)) * (x3-x1));
    int y4 = y2;
    float z4 = z1 + (float)(y2 - y1)/(float)(y3-y1) * (z3 - z1);

    // fill bottom flat triangle
    float slope1 = (float)(x2-x1) / (float)(y2-y1);
    float slope2 = (float)(x4-x1) / (float)(y4-y1);
    float slopez1 = (z2-z1) / (float)(y2-y1);
    float slopez2 = (z4-z1) / (float)(y4-y1);
    float cx1 = x1; float cx2 = x1;
    float cz1 = z1; float cz2 = z1;
    
    float slopet;
    if (slope1 < slope2) {
      slopet = slope1; zt = slopez1;
      slope1 = slope2; slopez1 = slopez2;
      slope2 = slopet; slopez2 = zt;
    }
    
    for (int cy = y1; cy <= y2; cy++) {
        for (int ax = (int)cx2; ax <= (int)cx1; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max((float)0., min((float)1., t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                F[wF * cy + ax] = tz;
              }
            }
        }
        cx1 += slope1;
        cx2 += slope2;
        cz1 += slopez1;
        cz2 += slopez2;
    }

    // fill top flat triangle
    slope1 = (float)(x3-x2) / (float)(y3-y2);
    slope2 = (float)(x3-x4) / (float)(y3-y4);
    slopez1 = (z3-z2) / (float)(y3-y2);
    slopez2 = (z3-z4) / (float)(y3-y4);
    cx1 = x3; cx2 = x3;
    cz1 = z3; cz2 = z3;
    
    if (slope1 < slope2) {
      slopet = slope1; zt = slopez1;
      slope1 = slope2; slopez1 = slopez2;
      slope2 = slopet; slopez2 = zt;
    }
    
    for (int cy = y3; cy > y2; cy--) {
        for (int ax = (int)cx1; ax <= (int)cx2; ax++) {
            if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
              float t = (ax-cx2)/(cx1-cx2);
              t = max((float)0., min((float)1., t));
              float tz = 1 / ((1-t)*cz2 + t*cz1);
              if (F[wF * cy + ax] > tz) {
                F[wF * cy + ax] = tz;
              }
            }
        }
        cx1 -= slope1;
        cx2 -= slope2;
        cz1 -= slopez1;
        cz2 -= slopez2;
    }
    }
    }
}
