// Triangle setup for shadow map

__kernel void setup(__global float3 *XYZ,
                    __global int *TI,  // Indices out
                    __global int *TN,  // number of tris
                    __global int2 *XY,   // Screen coords out
                    __global float *ZZ,  // Depths out
                    __constant float *Vpos, __constant float3 *VV,
                    const float shBias,
                    const float sScale, const int wF, const int hF,
                    const float cAX, const float cAY, const int lenP) {
    
    // Block index
    int bx = get_group_id(0);
    int tx = get_local_id(0);
    
    if (tx == 0) TN[bx] = 0;
    barrier(CLK_GLOBAL_MEM_FENCE);

    if ((bx * BLOCK_SIZE + tx) < lenP) {
    int ci = (bx * BLOCK_SIZE + tx) * 3;
    float3 x1 = XYZ[ci];
    float3 x2 = XYZ[ci+1];
    float3 x3 = XYZ[ci+2];
    
    float3 vp = (float3)(Vpos[0], Vpos[1], Vpos[2]);
    x1 -= vp; x2 -= vp; x3 -= vp;
    float3 SVd = VV[0];
    float3 SVx = VV[1];
    float3 SVy = VV[2];
    float3 dd = (float3)(dot(x1, SVd), dot(x2, SVd), dot(x3, SVd));
    float3 dx = (float3)(dot(x1, SVx), dot(x2, SVx), dot(x3, SVx));
    float3 dy = (float3)(dot(x1, SVy), dot(x2, SVy), dot(x3, SVy));
    dd += shBias;
    dd = 1 / dd;
      dx = dx * sScale + wF/2;
      dy = dy * -sScale + hF/2;
      int3 dix = convert_int3(dx);
      int3 diy = convert_int3(dy);
    float yes = false;
    if (all(dd > 0) && all(dix >= -120) && all(dix < (wF+120)) && all(diy >= -120) && all(diy < (hF+120))) {
    // && all(fabs(dx) < cAX) && all(fabs(dy) < cAY)) {
      yes = true;
    }
    //if (tx == 0) printf("svd %f %f %f \n svx %f %f %f \n",
    //                    SVd.x, SVd.y, SVd.z, SVx.x, SVx.y, SVx.z);
                        
    if (yes) {
      //printf("tx %d xyz: %f %f %f \n", tx, x1.x, x1.y, x1.z);
      //printf("tx %d x: %d %d %d y: %d %d %d \n", tx, dix.x, dix.y, dix.z, diy.x, diy.y, diy.z);
      int nextI = atomic_inc(&TN[bx]);
      XY[(bx*BLOCK_SIZE + tx)*3] = (int2)(dix.s0, diy.s0);
      XY[(bx*BLOCK_SIZE + tx)*3+1] = (int2)(dix.s1, diy.s1);
      XY[(bx*BLOCK_SIZE + tx)*3+2] = (int2)(dix.s2, diy.s2);
      ZZ[(bx*BLOCK_SIZE + tx)*3] = dd.s0;
      ZZ[(bx*BLOCK_SIZE + tx)*3+1] = dd.s1;
      ZZ[(bx*BLOCK_SIZE + tx)*3+2] = dd.s2;
      TI[bx*BLOCK_SIZE + nextI] = bx * BLOCK_SIZE + tx;
    }
    }
}
