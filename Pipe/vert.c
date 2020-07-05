// Vertex functions

__kernel void transform(__global float3 *XYZ,
                        __global float3 *VN,
                        __constant float3 *OldR,
                        __constant float3 *RR,
                        __constant float *O,
                        const int lStart, const int lEnd) {
    // Block index
    int ix = get_global_id(0);

    if (ix < (lEnd-lStart)) {
     float3 p = XYZ[ix+lStart];
     float3 n = VN[ix+lStart];

     float3 origin = (float3)(O[0], O[1], O[2]);
     p -= origin;
     float3 q = (float3)(dot(p, OldR[0]), dot(p, OldR[1]), dot(p, OldR[2]));
     float3 r = (float3)(dot(q, RR[0]), dot(q, RR[1]), dot(q, RR[2]));
     r += origin;

     float3 m = (float3)(dot(n, OldR[0]), dot(n, OldR[1]), dot(n, OldR[2]));
     float3 l = (float3)(dot(m, RR[0]), dot(m, RR[1]), dot(m, RR[2]));

     XYZ[ix+lStart] = r;
     VN[ix+lStart] = l;
    }
}
__kernel void Ttranslate(__global float3 *XYZ,
                         const float ox, const float oy, const float oz,
                         const int lStart, const int lEnd) {
    int ix = get_global_id(0);
    if (ix < (lEnd-lStart)) {
     float3 p = XYZ[ix+lStart] + (float3)(ox, oy, oz);
     XYZ[ix+lStart] = p;
    }
}

__kernel void Tscale(__global float3 *XYZ, __constant float *O, const float scale,
                        const int lStart, const int lEnd) {
    int ix = get_global_id(0);
    float3 origin = (float3)(O[0], O[1], O[2]);
    if (ix < (lEnd-lStart)) {
     float3 p = XYZ[ix+lStart] - origin;
     XYZ[ix+lStart] = scale * p + origin;
    }
}

__kernel void vertL(__global float3 *XYZ,
                    __global float3 *VN,
                    __global float3 *I,
                    __constant float3 *LInt, __constant float3 *LDir, // Directional
                    __constant float3 *PInt, __constant float3 *PPos, // Point
                    __global float3 *SInt, __global float3 *SDir, __global float3 *SPos,
                    const float ambLight,
                    const char lenD, const short lenP, const int lenS,
                    const int lenV) {

    // Block index
    int bx = get_group_id(0);
    int tx = get_local_id(0);

    if ((bx * BLOCK_SIZE + tx) < lenV) {
     int ci = bx * BLOCK_SIZE + tx;
     float3 x = XYZ[ci];
     float3 norm = VN[ci];
     float3 light = 0.f;
     for (char i = 1; i < lenD; i++) {
       //light += max(0.f, dot(norm, LDir[i])) * LInt[i];
       light += max(0.f, dot(norm, LDir[i]) + 0.5f) * 0.66f * LInt[i];
     }
     for (short i = 0; i < lenP; i++) {
       float3 pl = x - PPos[i];
       if ((dot(norm, pl) > 0.f)) { // && (fast_length(pl) < 16.f)) {
         light += dot(norm, fast_normalize(pl)) / (1.f + fast_length(pl)*fast_length(pl)) * PInt[i];
       }
     }
     for (int i = 0; i < lenS; i++) {
       float3 pl = x - SPos[i];
       // For global illumination
       if ((dot(SDir[i], pl) > 0.f) && (dot(norm, pl) > 0.f) /* ) { */ && (fast_length(pl) < 16.f)) {
         light += dot(norm, fast_normalize(pl)) * dot(fast_normalize(pl), SDir[i]) /
                  (1.5f + fast_length(pl)*fast_length(pl)) * SInt[i];
       }

       // For actual spot lights
       /*float3 dirx = SDir[i];
       float angle = 0.9f;
       if (dot(fast_normalize(pl), dirx) > angle) {
         light += max(0.f, dot(norm, fast_normalize(pl)) * fast_length(pl) /
                  (1.f + fast_length(pl)*fast_length(pl))) * SInt[i];
       }*/
     }
     //light = max(light, ambLight);
     I[ci] = light; //min(light, 1.5f);
    }
}

