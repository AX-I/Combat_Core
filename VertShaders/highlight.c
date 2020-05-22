// Highlight

__kernel void highlight(__global float3 *I, float hr, float hg, float hb, const int lenV) {
    int ix = get_global_id(0);
    if (ix < lenV) {
       I[ix] = (float3)(hr, hg, hb);
    }
}
