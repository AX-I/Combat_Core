
__kernel void clearFrame(__global float *F,
                         __global ushort *Ro, __global ushort *Go, __global ushort *Bo,
                         __global char *FT,
                         int Ri, int Gi, int Bi,
                         const int wF, const int hF, const int BS, const int lenP) {

    int bx = get_group_id(0);
    int by = get_group_id(1);
    int tx = get_local_id(0);
    int ty = get_local_id(1);

    int ci = bx * BS + tx;
    int cj = by * BS + ty;

    int w1 = wF / lenP * ci;
    int w2 = wF / lenP * (ci+1);
    int h1 = hF / lenP * cj;
    int h2 = hF / lenP * (cj+1);

    for (int cy = h1; cy < h2; cy++) {
        for (int cx = w1; cx < w2; cx++) {
            F[wF * cy + cx] = 65535.f;
            //Ro[wF * cy + cx] = Ri;
            //Go[wF * cy + cx] = Gi;
            //Bo[wF * cy + cx] = Bi;
            FT[wF * cy + cx] = 0;
        }
    }
}
