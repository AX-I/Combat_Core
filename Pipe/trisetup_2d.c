// Coordinates from 0 to 1

#define TILE_SIZE 16
#define SMALL_THRESH 4

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

    float3 dx = (float3)(x1.x, x2.x, x3.x);
    float3 dy = (float3)(x1.y, x2.y, x3.y);
    float3 dd = 1.f / (float3)(x1.z, x2.z, x3.z);

    float yes = true;

    dx = dx * wF;
    dy = dy * hF;
    int3 dix = convert_int3(dx);
    int3 diy = convert_int3(dy);
    int maxX = max(dix.x, max(dix.y, dix.z));
    int minX = min(dix.x, min(dix.y, dix.z));
    int dimx = maxX - minX;
    int maxY = max(diy.x, max(diy.y, diy.z));
    int minY = min(diy.x, min(diy.y, diy.z));
    int dimy = maxY - minY;

    float small = false;
    if (max(dimx, dimy) < SMALL_THRESH*TILE_SIZE) small = true;

    if (yes) {
      XY[(bx*BLOCK_SIZE + tx)*3] = (float2)(dx.s0, dy.s0);
      XY[(bx*BLOCK_SIZE + tx)*3+1] = (float2)(dx.s1, dy.s1);
      XY[(bx*BLOCK_SIZE + tx)*3+2] = (float2)(dx.s2, dy.s2);
      ZZ[(bx*BLOCK_SIZE + tx)*3] = dd.s0;
      ZZ[(bx*BLOCK_SIZE + tx)*3+1] = dd.s1;
      ZZ[(bx*BLOCK_SIZE + tx)*3+2] = dd.s2;

	  if (small) {
		int nextI = atomic_inc(&TNA[bx]);
        TIA[bx*BLOCK_SIZE + nextI] = bx * BLOCK_SIZE + tx;
	  } else {
        int nextI = atomic_inc(&TNB[bx]);
        TIB[bx*BLOCK_SIZE + nextI] = bx * BLOCK_SIZE + tx;
	  }
    }
  }
}
