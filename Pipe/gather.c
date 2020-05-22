// 2: Gathering

__kernel void setup(__global int *TI,  // Indices in
                    __global int *TN,  // number of tris
                    __global int *TO,  // Indices out
                    __global int *AL,  // Final sum
                    const int tn,
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
    if ((bx == (numBlocks-1)) && (tx == 0)) AL[tn] = gStart + gSize;
}
