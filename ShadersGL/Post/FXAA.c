// https://github.com/dolphin-emu/dolphin/blob/master/Data/Sys/Shaders/FXAA.glsl

#version 330

#define FXAA_REDUCE_MIN		(1.0/ 128.0)
#define FXAA_REDUCE_MUL		(1.0 / 8.0)
#define FXAA_SPAN_MAX		8.0

uniform sampler2D tex1;

out vec3 f_color;

uniform float width;
uniform float height;

vec3 SampleLocation(vec2 p) {
	return texture(tex1, p).rgb;
}

vec4 applyFXAA(vec2 fragCoord)
{
	vec4 color;
	vec2 inverseVP = 1 / vec2(width, height);

	vec3 rgbNW = SampleLocation((fragCoord + vec2(-1.0, -1.0)) * inverseVP).xyz;
	vec3 rgbNE = SampleLocation((fragCoord + vec2(1.0, -1.0)) * inverseVP).xyz;
	vec3 rgbSW = SampleLocation((fragCoord + vec2(-1.0, 1.0)) * inverseVP).xyz;
	vec3 rgbSE = SampleLocation((fragCoord + vec2(1.0, 1.0)) * inverseVP).xyz;
	vec3 rgbM  = SampleLocation(fragCoord  * inverseVP).xyz;
	vec3 luma = vec3(0.299, 0.587, 0.114);
	float lumaNW = dot(rgbNW, luma);
	float lumaNE = dot(rgbNE, luma);
	float lumaSW = dot(rgbSW, luma);
	float lumaSE = dot(rgbSE, luma);
	float lumaM  = dot(rgbM,  luma);
	float lumaMin = min(lumaM, min(min(lumaNW, lumaNE), min(lumaSW, lumaSE)));
	float lumaMax = max(lumaM, max(max(lumaNW, lumaNE), max(lumaSW, lumaSE)));

	vec2 dir;
	dir.x = -((lumaNW + lumaNE) - (lumaSW + lumaSE));
	dir.y =  ((lumaNW + lumaSW) - (lumaNE + lumaSE));

	float dirReduce = max((lumaNW + lumaNE + lumaSW + lumaSE) *
						(0.25 * FXAA_REDUCE_MUL), FXAA_REDUCE_MIN);

	float rcpDirMin = 1.0 / (min(abs(dir.x), abs(dir.y)) + dirReduce);
	dir = min(vec2(FXAA_SPAN_MAX, FXAA_SPAN_MAX),
			max(vec2(-FXAA_SPAN_MAX, -FXAA_SPAN_MAX),
			dir * rcpDirMin)) * inverseVP;

	vec3 rgbA = 0.5 * (
		SampleLocation(fragCoord * inverseVP + dir * (1.0 / 3.0 - 0.5)).xyz +
		SampleLocation(fragCoord * inverseVP + dir * (2.0 / 3.0 - 0.5)).xyz);
	vec3 rgbB = rgbA * 0.5 + 0.25 * (
		SampleLocation(fragCoord * inverseVP + dir * -0.5).xyz +
		SampleLocation(fragCoord * inverseVP + dir * 0.5).xyz);

	float lumaB = dot(rgbB, luma);
	if ((lumaB < lumaMin) || (lumaB > lumaMax))
		color = vec4(rgbA, 1.0);
	else
		color = vec4(rgbB, 1.0);
	return color;
}

void main()
{
	f_color = applyFXAA(gl_FragCoord.xy).rgb;
}
