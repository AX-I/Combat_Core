# ======== ========
# Copyright (C) 2019, 2020 Louis Zhang
# Copyright (C) 2019, 2020 AgentX Industries
#
# This file (Templates.py) is part of AXI Visualizer and AXI Combat.
#
# AXI Combat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# AXI Combat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AXI Combat. If not, see <https://www.gnu.org/licenses/>.
# ======== ========

# AXI Visualizer Shader Templates
# v0.2

template_func = """
#define TILE_SIZE 16.f
#define TILE_BUF 128
#define TILE_AREA 256

__kernel void draw(__global int *TO, __global int *TN,
                   __global ushort *Ro, __global ushort *Go, __global ushort *Bo,
                   __global float *F, __global float2 *P, __global float *Z,
                   [SHADER_ARGS]
                   const int wF, const int hF) {
"""

template_setup = """
    int bx = get_group_id(0);
    int tx = get_local_id(0);

    __local float ZBuf[TILE_AREA];
    __local int ZAccess[TILE_AREA];

    int tileX = bx % (int)(wF / TILE_SIZE);
    int tileY = bx / (wF / TILE_SIZE);

    float xMin = (tileX) * TILE_SIZE;
    float xMax = (tileX+1.f) * TILE_SIZE - 1.f;
    float yMin = (tileY) * TILE_SIZE;
    float yMax = (tileY+1.f) * TILE_SIZE - 1.f;

    if (tx < TILE_SIZE) {
        for (int i=0; i < (TILE_SIZE); i++) {
            ZBuf[(int)(tx * TILE_SIZE + i)] = F[(int)(wF * (yMin + tx) + xMin + i)];
            ZAccess[(int)(tx * TILE_SIZE + i)] = 0;
        }
    }

  if (TN[bx] > tx) {

    int txd = TO[bx * TILE_BUF + tx];

    int ci = txd * 3;

    float z1 = Z[ci];
    float z2 = Z[ci+1];
    float z3 = Z[ci+2];

    float2 xy1 = P[ci];
    float2 xy2 = P[ci+1];
    float2 xy3 = P[ci+2];

    [SHADER_SETUP_RETRIEVE]

    float x1 = floor(xy1.x); float x2 = floor(xy2.x); float x3 = floor(xy3.x);
    float y1 = floor(xy1.y); float y2 = floor(xy2.y); float y3 = floor(xy3.y);
    
    float ytemp; float xtemp;
    float zt;

    [SHADER_SETUP_TEMP]

    // sort y1<y2<y3
    [SHADER_SETUP_SORT]
    
    float ydiff1 = (y2-y1)/(y3-y1);
    float x4 = x1 + ydiff1 * (x3 - x1);
    float y4 = y2;
    float z4 = z1 + ydiff1 * (z3 - z1);

    [SHADER_SETUP_4TH]

"""

template_depth_compare = """

ZAccess[localCoord] = 0;
//barrier(CLK_LOCAL_MEM_FENCE);

int zId = atomic_inc(&ZAccess[localCoord]);

//barrier(CLK_LOCAL_MEM_FENCE);
int maxZid = ZAccess[localCoord];

for (int zr = 0; zr < maxZid; zr++) {
    if (zr == zId) {
        if (ZBuf[localCoord] > tz) ZBuf[localCoord] = tz;
        //barrier(CLK_LOCAL_MEM_FENCE);
    }
}
"""

template_draw = """
    // fill bottom flat triangle
    ydiff1 = 1 / (y2-y1);
    float slope1 = (x2-x1) * ydiff1;
    float slope2 = (x4-x1) * ydiff1;
    float slopez1 = (z2-z1) * ydiff1;
    float slopez2 = (z4-z1) * ydiff1;
    
    [SHADER_DRAW_CALC_SLOPE]
    
    float cx1 = x1; float cx2 = x1;
    float cz1 = z1; float cz2 = z1;

    [SHADER_DRAW_INIT_SCAN]
    
    float slopet;
    if (slope1 < slope2) {
      [SHADER_DRAW_SWITCH_SLOPE]
    }

    int cy = clamp(y1, yMin, yMax);

    cx1 = x1 + (cy-y1) * slope1;
    cx2 = x1 + (cy-y1) * slope2;
    cz1 = z1 + (cy-y1) * slopez1;
    cz2 = z1 + (cy-y1) * slopez2;

    [SHADER_DRAW_CLAMP_TILE]

    if (y2 > yMin) {
      for (; cy <= clamp(y2, yMin, yMax); cy++) {
        if ((cx2 < xMax) && (cx1 > xMin)) {
          for (int ax = clamp(cx2, xMin, xMax); ax <= clamp(cx1, xMin, xMax); ax++) {
            float t = (ax-cx2)/(cx1-cx2);
            t = max(0.f, min(1.f, t));
            float tz = 1 / ((1-t)*cz2 + t*cz1);
            int localCoord = TILE_SIZE * (cy - yMin) + ax - xMin;
            
            [SHADER_CORE]

          }
        }
        cx1 += slope1; cx2 += slope2;
        cz1 += slopez1; cz2 += slopez2;
        [SHADER_DRAW_INC]
      }
    }

    // fill top flat triangle
    ydiff1 = 1 / (y3-y2);
    slope1 = (x3-x2) * ydiff1;
    slope2 = (x3-x4) * ydiff1;
    slopez1 = (z3-z2) * ydiff1;
    slopez2 = (z3-z4) * ydiff1;

    [SHADER_DRAW_CALC_SLOPE 1]
    
    cx1 = x3; cx2 = x3;
    cz1 = z3; cz2 = z3;

    [SHADER_DRAW_INIT_SCAN 1]

    if (slope1 < slope2) {
      [SHADER_DRAW_SWITCH_SLOPE]
    }

    cy = clamp(y3, yMin, yMax);
    cx1 = x3 + (cy-y3) * slope1;
    cx2 = x3 + (cy-y3) * slope2;
    cz1 = z3 + (cy-y3) * slopez1;
    cz2 = z3 + (cy-y3) * slopez2;

    [SHADER_DRAW_CLAMP_TILE 1]

    if (y2 < yMax) {
      for (; cy >= clamp(y2, yMin, yMax); cy--) {
        if ((cx1 < xMax) && (cx2 > xMin)) {
          for (int ax = clamp(cx1, xMin, xMax); ax <= clamp(cx2, xMin, xMax); ax++) {
            float t = (ax-cx2)/(cx1-cx2);
            t = max(0.f, min(1.f, t));
            float tz = 1 / ((1-t)*cz2 + t*cz1);
            int localCoord = TILE_SIZE * (cy - yMin) + ax - xMin;
            
            [SHADER_CORE]
            
          }
        }
        cx1 -= slope1; cx2 -= slope2;
        cz1 -= slopez1; cz2 -= slopez2;
        [SHADER_DRAW_DEC]
      }
    }
  
  } // if (TN[bx] > tx)
"""

template_end = """
  if (tx == 0) TN[bx] = 0;
  if (tx < TILE_BUF) TO[bx * TILE_BUF + tx] = -1;

} // __kernel void draw()"""


# ======== ======== ======== ========
#
# Direct rasterize for small triangles
#
# ======== ======== ======== ========

template_func_small = """

__kernel void drawSmall(__global int *TO,
                        __global ushort *Ro, __global ushort *Go, __global ushort *Bo,
                        __global float *F, __global float2 *P, __global float *Z,
                        [SHADER_ARGS]
                        const int wF, const int hF, const int lenP) {
"""


template_setup_small = """
    int bx = get_group_id(0);
    int tx = get_local_id(0);

  if ((bx * BLOCK_SIZE + tx) < lenP) {

    int txd = TO[bx * BLOCK_SIZE + tx];

    int ci = txd * 3;

    float z1 = Z[ci];
    float z2 = Z[ci+1];
    float z3 = Z[ci+2];

    float2 xy1 = P[ci];
    float2 xy2 = P[ci+1];
    float2 xy3 = P[ci+2];

    [SHADER_SETUP_RETRIEVE]

    int x1 = xy1.x; int x2 = xy2.x; int x3 = xy3.x;
    int y1 = xy1.y; int y2 = xy2.y; int y3 = xy3.y;
    
    int ytemp; int xtemp;
    float zt;

    [SHADER_SETUP_TEMP]

    // sort y1<y2<y3
    [SHADER_SETUP_SORT]
    
    float ydiff1 = (y2-y1)/(float)(y3-y1);
    float x4 = x1 + ydiff1 * (x3 - x1);
    float y4 = y2;
    float z4 = z1 + ydiff1 * (z3 - z1);

    [SHADER_SETUP_4TH]
"""


template_draw_small = """
    // fill bottom flat triangle
    ydiff1 = 1 / (float)(y2-y1);
    float slope1 = (x2-x1) * ydiff1;
    float slope2 = (x4-x1) * ydiff1;
    float slopez1 = (z2-z1) * ydiff1;
    float slopez2 = (z4-z1) * ydiff1;
    
    [SHADER_DRAW_CALC_SLOPE]
    
    float cx1 = x1; float cx2 = x1;
    float cz1 = z1; float cz2 = z1;

    [SHADER_DRAW_INIT_SCAN]
    
    float slopet;
    if (slope1 < slope2) {
      [SHADER_DRAW_SWITCH_SLOPE]
    }

    int cy = y1;

    for (; cy <= y2; cy++) {
        for (int ax = cx2; ax <= cx1; ax++) {
          if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
            float t = (ax-cx2)/(cx1-cx2);
            t = max(0.f, min(1.f, t));
            float tz = 1 / ((1-t)*cz2 + t*cz1);
            
            [SHADER_CORE]
          }
        }
        cx1 += slope1; cx2 += slope2;
        cz1 += slopez1; cz2 += slopez2;
        [SHADER_DRAW_INC]
    }

    // fill top flat triangle
    ydiff1 = 1 / (float)(y3-y2);
    slope1 = (x3-x2) * ydiff1;
    slope2 = (x3-x4) * ydiff1;
    slopez1 = (z3-z2) * ydiff1;
    slopez2 = (z3-z4) * ydiff1;

    [SHADER_DRAW_CALC_SLOPE 1]
    
    cx1 = x3; cx2 = x3;
    cz1 = z3; cz2 = z3;

    [SHADER_DRAW_INIT_SCAN 1]

    if (slope1 < slope2) {
      [SHADER_DRAW_SWITCH_SLOPE]
    }

    cy = y3;
    
    for (; cy >= y2; cy--) {
        for (int ax = cx1; ax <= cx2; ax++) {
          if ((cy >= 0) && (cy < hF) && (ax >= 0) && (ax < wF)) {
            float t = (ax-cx2)/(cx1-cx2);
            t = max(0.f, min(1.f, t));
            float tz = 1 / ((1-t)*cz2 + t*cz1);
            
            [SHADER_CORE]
          }
        }
        cx1 -= slope1; cx2 -= slope2;
        cz1 -= slopez1; cz2 -= slopez2;
        [SHADER_DRAW_DEC]
    }
  
  } // if ((bx * BLOCK_SIZE + tx) < lenP)
"""

template_end_small = """
} // __kernel void drawSmall()"""
