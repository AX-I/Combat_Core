// Sky setup

__kernel void setup(__global float3 *XYZ,
                    __global float3 *VN,
                    __global int *TIA,  // Indices out small
                    __global int *TIB,  // Indices out large
                    __global int *TNA,  // number of tris
                    __global int *TNB,  // number of tris
                    __global float2 *XY, // Screen coords out
                    __global float *ZZ,  // Depths out
                    __constant float *Vpos, __constant float3 *VV,
                    const float sScale, const int wF, const int hF,
                    const float cAX, const float cAY, const int lenP) {

    // Block index
    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if (tx == 0) {
		TNA[bx] = 0;
		TNB[bx] = 0;
	}
    barrier(CLK_GLOBAL_MEM_FENCE);

  if ((bx * BLOCK_SIZE + tx) < lenP) {
    int ci = (bx * BLOCK_SIZE + tx) * 3;
    float3 x1 = XYZ[ci];
    float3 x2 = XYZ[ci+1];
    float3 x3 = XYZ[ci+2];

    float3 SVd = VV[0];
    float3 SVx = VV[1];
    float3 SVy = VV[2];
    float3 dd = (float3)(dot(x1, SVd), dot(x2, SVd), dot(x3, SVd));
    float3 dx = (float3)(dot(x1, SVx), dot(x2, SVx), dot(x3, SVx));
    float3 dy = (float3)(dot(x1, SVy), dot(x2, SVy), dot(x3, SVy));
    dd = 1 / dd;
    dx *= dd; dy *= dd;
    float yes = false;
    if (all(dd > 0) && all(fabs(dx) < cAX) && all(fabs(dy) < cAY)) {
      yes = true;
    }

    dx = dx * -sScale + wF/2;
    dy = dy * sScale + hF/2;
    int3 dix = convert_int3(dx);
    int3 diy = convert_int3(dy);
    int maxX = max(dix.x, max(dix.y, dix.z));
    int minX = min(dix.x, min(dix.y, dix.z));
    int dimx = maxX - minX;
    int maxY = max(diy.x, max(diy.y, diy.z));
    int minY = min(diy.x, min(diy.y, diy.z));
    int dimy = maxY - minY;
    if (dimx > wF) yes = false;
    if (dimy > hF) yes = false;
    if ((maxX < 0) || (maxY < 0) || (minX > wF) || (minY > hF)) yes = false;

    if (yes) {
      XY[(bx*BLOCK_SIZE + tx)*3] = (float2)(dx.s0, dy.s0);
      XY[(bx*BLOCK_SIZE + tx)*3+1] = (float2)(dx.s1, dy.s1);
      XY[(bx*BLOCK_SIZE + tx)*3+2] = (float2)(dx.s2, dy.s2);
      ZZ[(bx*BLOCK_SIZE + tx)*3] = dd.s0;
      ZZ[(bx*BLOCK_SIZE + tx)*3+1] = dd.s1;
      ZZ[(bx*BLOCK_SIZE + tx)*3+2] = dd.s2;

      int nextI = atomic_inc(&TNB[bx]);
      TIB[bx*BLOCK_SIZE + nextI] = bx * BLOCK_SIZE + tx;
    }
  }
}
