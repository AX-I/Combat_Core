// 2: Gathering

__kernel void setup(__global int *TI,  // Indices in
                    __global int *TN,  // number of tris
                    __global int *TO,  // Indices out
                    __global int *AL,  // Final sum (= tnEnd)
                    __global int *tnBlockEnd, // in
                    //__global int *tnEnd, // out
                    const int max_uv,
                    const int numBlocks) {

    __local int gSize;
    __local int gStart;

    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if (tx == 0) {
      gSize = TN[bx];
      gStart = 0;
      for (int i = 0; i < bx; i++) {
        gStart += TN[i];
      }
    }
    barrier(CLK_LOCAL_MEM_FENCE);
    if (tx < gSize) {
      TO[gStart + tx] = TI[bx*BLOCK_SIZE + tx];
    }

    if (tx == 0) {
      int tn = 0;
      for (; tn<max_uv; tn++) {
        if (bx == tnBlockEnd[tn] - 1) break;
      }
      //tnEnd[tn] = gStart + gSize;

      AL[tn] = gStart + gSize;
    }
}
