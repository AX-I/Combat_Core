// SSAO

#define radius 1.f
#define bias 0.002f
#define nsamples 16

uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

__kernel void ao(__global ushort *Ro, __global ushort *Go, __global ushort *Bo,
			     __global float *F, const float sScale,
			     __constant float *R,
                 const int wF, const int hF, const int BS) {

    int bx = get_group_id(0);
    int by = get_group_id(1);
    int tx = get_local_id(0);
    int ty = get_local_id(1);

    int cx = by*BS + ty;
    int cy = bx*BS + tx;

	float ao = 0.f;

	uint rng_state = (uint)(cy * hF + cx);

	float d = F[wF*cy + cx];

	float3 pos = d * (float3)((cx+0.5f-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);

	float dx = F[wF*cy + (cx+1)];
	float dy = F[wF*(cy+1) + cx];

	int rx = 1;
	int ry = 1;

	/*if (cx < wF/2) {
		dx = F[wF*cy + (cx-1)];
		rx = -1;
	} if (cy < hF/2) {
		dx = F[wF*(cy-1) + cx];
		ry = -1;
	}*/
	// This does not work for some reason
	/*float dx2 = F[wF*cy + (cx-1)];
	if (cx&1) {//(fabs(d-dx) > 1.f) {
		dx = dx2;
		rx = -1;
	}
	float dy2 = F[wF*(cy-1) + cx];
	if (cy&1) {//(fabs(d-dy) > 1.f) {
		dy = dy2;
		ry = -1;
	}*/

	float3 px = dx * (float3)((cx+0.5f+rx-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);
	float3 py = dy * (float3)((cx+0.5f-wF/2)/sScale, -(cy+0.5f+ry-hF/2)/sScale, 1);
	float3 norm = rx*ry*fast_normalize(cross(pos-px, pos-py));

	for (char i = 0; i < nsamples; i++) {
		int rid1 = rand_xorshift(rng_state) & 63;
		rng_state = rand_xorshift(rng_state);
		int rid2 = rand_xorshift(rng_state) & 63;
		rng_state = rand_xorshift(rng_state);
		int rid3 = rand_xorshift(rng_state) & 63;
		rng_state = rand_xorshift(rng_state);

		float3 svec = (float3)(R[rid1], R[rid2], R[rid3]) * 2.f - 1.f;

		svec = fast_normalize(svec);

		if (dot(svec, norm) < 0) svec = svec - 2*norm*dot(svec, norm);

		rid1 = rand_xorshift(rng_state) & 63;
		rng_state = rand_xorshift(rng_state);

		float rlen = R[rid1];
		svec *= rlen*rlen * radius;

		svec += pos;

		float sz = svec.z;
		float sx = (svec.x/sz*sScale) + wF/2;
		float sy = (-svec.y/sz*sScale) + hF/2;

		if ((sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF)) {

			float sampd = F[wF*(int)sy + (int)sx];

			float disct = clamp(2.f - (d-sampd), 0.f, 1.f);
		    ao += disct * ((sampd < sz - bias) ? 1.f : 0.f);

   	    }
	}
	ao /= nsamples;

	if (d > 6000) ao = 0;

	ao = clamp(ao*1.25f, 0.f, 1.f);

	/*Ro[wF * cy + cx] = (1-ao) * 8192;
	Go[wF * cy + cx] = (1-ao) * 8192;
	Bo[wF * cy + cx] = (1-ao) * 8192;*/
	Ro[wF * cy + cx] = (1-ao) * Ro[wF * cy + cx];
	Go[wF * cy + cx] = (1-ao) * Go[wF * cy + cx];
	Bo[wF * cy + cx] = (1-ao) * Bo[wF * cy + cx];

}
