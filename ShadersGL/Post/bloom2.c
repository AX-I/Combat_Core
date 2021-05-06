#version 330

uniform sampler2D tex1;
out vec3 f_color;
uniform float width;
uniform float height;
uniform int axis;

void main() {
	vec2 wh = 1 / vec2(width, height);
	vec2 tc = gl_FragCoord.xy;

    int cx = int(tc.x);
    int cy = int(tc.y);
    int hF = int(height);

    vec3 a = vec3(0);

    float off = 1.32;
    vec2 offset = vec2(0, off);
    if (axis == 1) offset = vec2(off, 0);

	a = (cy<9) ? a : a + 0.00816f * texture(tex1, (tc - 9*offset) * wh).rgb;
	a = (cy<8) ? a : a + 0.01384f * texture(tex1, (tc - 8*offset) * wh).rgb;
	  a = (cy<7) ? a : a + 0.02207f * texture(tex1, (tc - 7*offset) * wh).rgb;
	  a = (cy<6) ? a : a + 0.03306f * texture(tex1, (tc - 6*offset) * wh).rgb;
	  a = (cy<5) ? a : a + 0.04654f * texture(tex1, (tc - 5*offset) * wh).rgb;
	  a = (cy<4) ? a : a + 0.06157f * texture(tex1, (tc - 4*offset) * wh).rgb;
	  a = (cy<3) ? a : a + 0.07654f * texture(tex1, (tc - 3*offset) * wh).rgb;
	  a = (cy<2) ? a : a + 0.08941f * texture(tex1, (tc - 2*offset) * wh).rgb;
	  a = (cy<1) ? a : a + 0.09815f * texture(tex1, (tc - offset) * wh).rgb;
	  a += 0.10125f * texture(tex1, tc * wh).rgb;
	  a = (cy>=(hF-1)) ? a : a + 0.09815f * texture(tex1, (tc + offset) * wh).rgb;
	  a = (cy>=(hF-2)) ? a : a + 0.08941f * texture(tex1, (tc + 2*offset) * wh).rgb;
	  a = (cy>=(hF-3)) ? a : a + 0.07654f * texture(tex1, (tc + 3*offset) * wh).rgb;
	  a = (cy>=(hF-4)) ? a : a + 0.06157f * texture(tex1, (tc + 4*offset) * wh).rgb;
	  a = (cy>=(hF-5)) ? a : a + 0.04654f * texture(tex1, (tc + 5*offset) * wh).rgb;
	  a = (cy>=(hF-6)) ? a : a + 0.03306f * texture(tex1, (tc + 6*offset) * wh).rgb;
	  a = (cy>=(hF-7)) ? a : a + 0.02207f * texture(tex1, (tc + 7*offset) * wh).rgb;
	  //a /= 0.856f;
	a = (cy>=(hF-8)) ? a : a + 0.01384f * texture(tex1, (tc + 8*offset) * wh).rgb;
	a = (cy>=(hF-9)) ? a : a + 0.00816f * texture(tex1, (tc + 9*offset) * wh).rgb;
	a /= 0.9f;

    f_color = a;
}


