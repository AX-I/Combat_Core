// Coarse rasterization

#define TILE_SIZE 16.f
#define TILE_BUF 128

__kernel void draw(__global int *TO,
                   __global int *F, __global int *FN,
                   __global float2 *P,
                   int wF, int hF, int lenP) {

  // wF and hF should be divided by tile size
  // F => index buffer, FN => num buffer, P => screenpoints

  int bx = get_group_id(0);
  int tx = get_local_id(0);

  //if (tx == 1) {
  if ((bx * BLOCK_SIZE + tx) < lenP) {
    int txd = TO[bx*BLOCK_SIZE + tx];

    int ci = txd * 3;

    float2 xy1 = P[ci] / TILE_SIZE - 0.5f;
    float2 xy2 = P[ci+1] / TILE_SIZE - 0.5f;
    float2 xy3 = P[ci+2] / TILE_SIZE - 0.5f;

    float ytemp; float xtemp;
    float x1 = xy1.x; float x2 = xy2.x; float x3 = xy3.x;
    float y1 = xy1.y; float y2 = xy2.y; float y3 = xy3.y;

    // sort y1<y2<y3
    if (y1 > y2) {
      ytemp = y1; xtemp = x1;
      y1 = y2; x1 = x2;
      y2 = ytemp; x2 = xtemp;
    }
    if (y2 > y3) {
      ytemp = y2; xtemp = x2;
      y2 = y3; x2 = x3;
      y3 = ytemp; x3 = xtemp;
    }
    if (y1 > y2) {
      ytemp = y1; xtemp = x1;
      y1 = y2; x1 = x2;
      y2 = ytemp; x2 = xtemp;
    }

    float x4 = (x1 + ((y2-y1)/(y3-y1)) * (x3-x1));
    float y4 = y2;

    // fill bottom flat triangle
    float slope1 = (x2-x1) / (y2-y1);
    float slope2 = (x4-x1) / (y4-y1);

    float cx1 = x1; float cx2 = x1;

    float slopet;
    if (slope1 < slope2) {
      slopet = slope1;
      slope1 = slope2;
      slope2 = slopet;
    }

    float mx1, mx2;

    float sbias = 1.f + floor(y1) - y1;

    if (y1 != y2) {
      for (int cy = floor(y1); cy <= ceil(y2); cy++) {

        mx1 = cx1 + sbias * slope1;
        if (slope1 < 0) mx1 -= slope1;

        mx2 = cx2 + sbias * slope2;
        if (slope2 > 0) mx2 -= slope2;

        //mx2 = ((cy == ceil(y2)) && (slope2 < 0)) ? max(mx2, min(x2, x4)) : mx2; // Prevent overdraw

        mx1 = min(mx1, (float)wF - 1);
        mx2 = max(mx2, 0.f);
        if ((cy >= 0) && (cy < hF)) {
            for (int ax = floor(mx2); ax <= ceil(mx1); ax++) {
                int nextI = atomic_inc(&FN[wF * cy + ax]);
                F[(wF * cy + ax) * TILE_BUF + nextI] = txd;
            }
        }
        cx1 += slope1;
        cx2 += slope2;
      }
    }

    // fill top flat triangle
    slope1 = (float)(x3-x2) / (float)(y3-y2);
    slope2 = (float)(x3-x4) / (float)(y3-y4);
    cx1 = x3; cx2 = x3;

    if (slope1 < slope2) {
      slopet = slope1;
      slope1 = slope2;
      slope2 = slopet;
    }

    sbias = y3 - floor(y3);

    if (y2 != y3) {
      for (int cy = ceil(y3); cy >= floor(y2); cy--) {

        mx1 = cx1 - sbias * slope1;
        if (slope1 < 0) mx1 += slope1;

        mx2 = cx2 - sbias * slope2;
        if (slope2 > 0) mx2 += slope2;

        //mx2 = (cy == floor(y2)) ? min(mx2, max(x2, x4)) : mx2; // Prevent overdraw

        mx2 = min(mx2, (float)wF - 1);
        mx1 = max(mx1, 0.f);
        if ((cy >= 0) && (cy < hF)) {
            for (int ax = floor(mx1); ax <= ceil(mx2); ax++) {
                int nextI = atomic_inc(&FN[wF * cy + ax]);
                F[(wF * cy + ax) * TILE_BUF + nextI] = txd;
            }
        }
        cx1 -= slope1;
        cx2 -= slope2;
      }
    }
  } // if ((bx * BLOCK_SIZE + tx) < lenP)
} // __kernel void draw()
