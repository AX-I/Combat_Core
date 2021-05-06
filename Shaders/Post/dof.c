// DoF
#define MAXCOC 4.f

__kernel void dof(__global ushort *Ro, __global ushort *Go, __global ushort *Bo,
				  __global ushort *R2, __global ushort *G2, __global ushort *B2,
			      __global float *F, const float focus,
                  const int wF, const int hF, const int BS) {

    int bx = get_group_id(0);
    int by = get_group_id(1);
    int tx = get_local_id(0);
    int ty = get_local_id(1);

    float cx = by*BS + ty + 0.5f;
    float cy = bx*BS + tx + 0.5f;

	//float fpoint = 1.f; // focal length
	float apeture = 4.f;

	float d = F[wF*(int)cy + (int)cx];

	//float coc = fabs(apeture * fpoint * (focus-d) / d / (focus-fpoint));
	//float coc = 3.f;
	float coc = apeture * fabs(d-focus) / focus / d;
	//float coc = apeture * fpoint * fabs(d - focus) / d / (focus - fpoint);

	float dofR = 0;
	float dofG = 0;
	float dofB = 0;

	float nsamples = 0;
	float cover;
	float radius = min(MAXCOC, coc);

	for (int sy = floor(cy - radius); sy < ceil(cy + radius); sy ++) {
		for (int sx = floor(cx - radius); sx < ceil(cx + radius); sx ++) {
			cover = (1.f - max(cx - radius - sx, 0.f)) * (1.f - max(cy - radius - sy, 0.f));
			cover *= min(cx + radius - sx, 1.f) * min(cy + radius - sy, 1.f);

			if ((sx < 0) || (sx >= wF) || (sy < 0) || (sy >= hF)) cover = 0;

			else {
			float ecoc = F[wF*sy + sx];
			ecoc = apeture * fabs(ecoc-focus) / focus / ecoc;
			ecoc = min(MAXCOC, ecoc);

			if (radius > ecoc) cover *= ecoc / radius;
			//if (F[wF*sy + sx] < focus*min(coc-0.2f, 1.f)) cover = 0;

			dofR += Ro[wF*sy + sx] * cover;
			dofG += Go[wF*sy + sx] * cover;
			dofB += Bo[wF*sy + sx] * cover;
			nsamples += cover;
			}
		}
	}


	//float nsamples = (radius*2+1)*(radius*2+1);
	dofR /= nsamples;
	dofG /= nsamples;
	dofB /= nsamples;

	R2[wF*(int)cy + (int)cx] = dofR;
	G2[wF*(int)cy + (int)cx] = dofG;
	B2[wF*(int)cy + (int)cx] = dofB;

}
