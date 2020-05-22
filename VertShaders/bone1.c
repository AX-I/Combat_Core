// Skeletal animation

__kernel void transform(__global float3 *XYZ,
                        __global float3 *VN,
                        __global char *BN,
                        __constant float3 *OldR, // inverted
                        __constant float3 *RR,
                        const int lStart, const int lEnd, const char off) {

    int ix = get_global_id(0);

    if (ix < (lEnd-lStart)) {
     float3 p = XYZ[ix+lStart];
     float3 n = VN[ix+lStart];
     char bone = BN[ix+lStart] - off;
     p += OldR[4*bone+3];
     float3 q = (float3)(dot(p, OldR[4*bone]), dot(p, OldR[4*bone+1]), dot(p, OldR[4*bone+2]));
     float3 r = (float3)(dot(q, RR[4*bone]), dot(q, RR[4*bone+1]), dot(q, RR[4*bone+2]));
     r += RR[4*bone+3];

     float3 m = (float3)(dot(n, OldR[4*bone]), dot(n, OldR[4*bone+1]), dot(n, OldR[4*bone+2]));
     float3 l = (float3)(dot(m, RR[4*bone]), dot(m, RR[4*bone+1]), dot(m, RR[4*bone+2]));

     XYZ[ix+lStart] = r;
     VN[ix+lStart] = l;
    }
}

__kernel void offset(__global float3 *XYZ, __global char *BN,
                     char b, float ox, float oy, float oz,
                     const int lenV) {
    int ix = get_global_id(0);

    if (ix < lenV) {
     if (BN[ix] == b) {
      float3 p = XYZ[ix];
      p -= (float3)(ox, oy, oz);
      XYZ[ix] = p;
     }
    }
}
