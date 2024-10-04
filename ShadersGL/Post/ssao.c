#version 330

#define DOWNSCALED {DOWNSCALED}


#define SSAO
#define radius 1.f
#define bias 0.002f
#define nsamples 32
#define FALLOFF_DIST 0.5f
#define MAX_CONTINUITY 0.2f


#define SCR_SHADOW
#define SCR_SOFT
#define RAYCAST_LENGTH 128
#define RAYCAST_STEP 4
#define RAYCAST_TARGET_DIST 99.0
#define RAYCAST_SURFACE_DEPTH 0.f
#define RAYCAST_DBIAS 0.2f
#define RAYCAST_FADE_DIST 2.f

uniform sampler2D texd;
uniform float width;
uniform float height;
uniform float vscale;
uniform float R[64];

out vec3 f_color;

uniform vec3 vpos;
uniform mat3 rawVM;

uniform vec3 PInt[16];
uniform vec3 PPos[16];
uniform int lenP;



uint rand_xorshift(uint rng_state) {
    rng_state ^= (rng_state << 13);
    rng_state ^= (rng_state >> 17);
    rng_state ^= (rng_state << 5);
    return rng_state;
}

void main() {
    vec2 wh = 1 / vec2(width, height);
	float wF = width;
	float hF = height;

	vec2 tc = gl_FragCoord.xy * DOWNSCALED;
	float cx = tc.x;
	float cy = tc.y;

	float sScale = vscale * hF/2;


  vec3 pos;
  vec3 px, py, norm;
  float d = texture(texd, tc*wh).r;
  float dx = texture(texd, (tc + vec2(1, 0))*wh).r;
  float dy = texture(texd, (tc + vec2(0, 1))*wh).r;


	float ao = 0.f;

  uint rng_state = rand_xorshift(uint(cy * hF + cx));
  uint rid1 = rng_state & 63u;
  rng_state = rand_xorshift(rng_state);
  uint rid2 = rng_state & 63u;

#ifdef SSAO
	pos = d * vec3((cx+0.5f-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);

	// Use the other side if closer object is in the way
	if (abs(dx - d) > MAX_CONTINUITY) {
		dx = 2*d - texture(texd, (tc + vec2(-1, 0))*wh).r;
	}
	if (abs(dy - d) > MAX_CONTINUITY) {
		dy = 2*d - texture(texd, (tc + vec2(0, -1))*wh).r;
	}

	int rx = 1;
	int ry = 1;


	px = dx * vec3((cx+0.5f+rx-wF/2)/sScale, -(cy+0.5f-hF/2)/sScale, 1);
	py = dy * vec3((cx+0.5f-wF/2)/sScale, -(cy+0.5f+ry-hF/2)/sScale, 1);
	norm = rx*ry*normalize(cross(pos-px, pos-py));

    // Bias to prevent grayness
	int sig_x = norm.x > 0 ? 1 : -1;
	int sig_y = norm.y > 0 ? -1 : 1;

	for (int i = 0; i < nsamples; i++) {
		rid1 = rng_state & 63u;
		rng_state = rand_xorshift(rng_state);
		rid2 = rng_state & 63u;
		rng_state = rand_xorshift(rng_state);
		uint rid3 = rng_state & 63u;
		rng_state = rand_xorshift(rng_state);

		vec3 svec = vec3(R[rid1], R[rid2], R[rid3]) * 2.f - 1.f;

		svec = normalize(svec);

		if (dot(svec, norm) < 0) svec = svec - 2*norm*dot(svec, norm);

		rid1 = rng_state & 63u;
		rng_state = rand_xorshift(rng_state);

		float rlen = R[rid1];
		svec *= rlen*rlen * radius;

		svec += pos;

		float sz = svec.z;
		float sx = (svec.x/sz*sScale) + wF/2;
		float sy = (-svec.y/sz*sScale) + hF/2;

		if ((sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF)) {

			float sampd = texture(texd, vec2(int(sx) + 0.5*sig_x, int(sy) + 0.5*sig_y)*wh).r;

			float disct = clamp(2.f - (d-sampd)/FALLOFF_DIST, 0.f, 1.f);
		    ao += disct * ((sampd < sz - bias) ? 1.f : 0.f);

   	    }
	}
	ao /= nsamples;

	if (d > 200) ao = 0;

	ao = clamp(ao*1.25f, 0.f, 1.f);

#endif




#ifdef SCR_SHADOW
    float sVScale = vscale * hF / 2;
    
    vec3 SVd = rawVM[0];
    vec3 SVx = rawVM[1];
    vec3 SVy = rawVM[2];
    
    pos = vpos + d * (SVd - SVx * (cx+0.5f-wF/2)/sVScale + SVy * (cy+0.5f-hF/2)/sVScale);
    vec3 a = pos - vpos;

    px = vpos + dx * (SVd - SVx * (cx+0.5f+rx-wF/2)/sScale + SVy * (cy+0.5f-hF/2)/sScale);
    py = vpos + dy * (SVd - SVx * (cx+0.5f-wF/2)/sScale + SVy * (cy+0.5f+ry-hF/2)/sScale);
    norm = rx*ry*normalize(-cross(pos-px, pos-py));

    int idP = 0;
    float maxP = 0;
    for (int i = 0; i < lenP; i++) {
      vec3 pl = pos - PPos[i];
      float curP = dot(norm, normalize(pl)) / (1.0 + length(pl)*length(pl)) * dot(PInt[i], vec3(0.2126f, 0.7152f, 0.0722f));
      if (curP > maxP) {
        maxP = curP; idP = i;
      }
    }
  
    vec2 rxy = tc;

    // vec3 PxDir = LDir;
    vec3 PxDir = a - (PPos[idP]-vpos);
    #ifdef SCR_SOFT
      vec3 LDirTG1 = normalize(cross(PxDir, vec3(1,0,0)));
      vec3 LDirTG2 = normalize(cross(PxDir, LDirTG1));
      vec3 LDirSample = normalize(PxDir + 0.2 * LDirTG1 * (R[rid1]-0.5) + 0.2 * LDirTG2 * (R[rid2]-0.5));
    #else
      vec3 LDirSample = normalize(PxDir);
    #endif
    
    vec3 target = a - LDirSample*RAYCAST_TARGET_DIST;
    float rpz = dot(target, SVd);
    if (rpz < 0) { // direction is reversed
      target = a + (-dot(SVd, a) / dot(SVd, LDirSample) * 0.99) * LDirSample;
      rpz = dot(target, SVd);
    }
    vec2 rp = vec2(dot(target, SVx) * -sVScale / rpz + wF/2,
                   dot(target, SVy) * sVScale / rpz + hF/2);

    int hit = 0;
    vec3 hitPos;

    float dt = max(abs(rp.x - rxy.x), abs(rp.y - rxy.y));
    int vx = RAYCAST_STEP;
    float slopex = (rp.x - rxy.x) / dt * vx;
    float slopey = (rp.y - rxy.y) / dt * vx;
    float slopez = (1.f/rpz - 1.0/d) / dt * vx;

    float sy = tc.y;
    float sx = tc.x;
    float sz = 1.0/d;
    float sd = RAYCAST_SURFACE_DEPTH;
    int rn = 0;

    int dither = int(RAYCAST_STEP * 0.5f * ((int(tc.x)^int(tc.y)) & 1) + 0.25f * (1-(int(tc.y) & 1)));
    sx += slopex * dither / vx;
    sy += slopey * dither / vx;
    sz += slopez * dither / vx;

    float currdist;

    for (rn = 0; (hit == 0) && (rn < RAYCAST_LENGTH) &&
                 (sx >= 0) && (sx < wF) && (sy >= 0) && (sy < hF) && (sz > 0);
         rn += vx) {
        currdist = texture(texd, vec2(int(sx)+0.5f, int(sy)+0.5f) * wh).r;
        if ((currdist < 1.f/sz) &&
            (currdist > 1.f/sz - sd)) {

            hit = (rn > 2) ? 1 : 0;
            
            hitPos = currdist * (SVd - vec3((sx-wF/2)/sVScale) * SVx + vec3((sy-hF/2)/sVScale) * SVy);
        }
        sx += slopex;
        sy += slopey;
        sz += slopez;
        sd = abs(1.f/sz - 1.f/(sz - slopez)) + RAYCAST_DBIAS;
    }
    float pxShadow = hit * max(0.0, (1/RAYCAST_FADE_DIST)*(RAYCAST_FADE_DIST - dot(hitPos-a, hitPos-a)));
  #else
    int idP = 0;
    float pxShadow = 0;
  #endif

  f_color = vec3(ao, pxShadow, idP/16.0);
}
