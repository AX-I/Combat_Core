// Select

__kernel void highlight(__global float3 *XYZ, __global char *BN,
                     __global float *I, float lc, float hc, float hl,
                     char b, float ox, float oy, float oz, float sr,
                     char commit, char showAll,
                     const int lenV) {
    int ix = get_global_id(0);
    
    if (ix < lenV) {
      if (showAll == 1) {
       I[ix] = lc;
      }
      float3 p = XYZ[ix];
      if (BN[ix] == b) {
       I[ix] = hc;
      }
      else if (all(fabs(p - (float3)(ox, oy, oz)) < sr)) {
       I[ix] = hl;
       if (commit == 1) {
        BN[ix] = b;
       }
      }
    }
}
