"""color adjustment

"""

import vapoursynth as vs
from vapoursynth import core
import math

__all__ = [
	"PEQ",
	"PEQ_SAT", "PEQ_HUE", "PEQ_CONT", "PEQ_BRI", "PEQ_TEMP", "PEQ_GAMMA"
]


def _Expr(clips, expr):
	try:
		return core.akarin.Expr(clips, expr)
	except AttributeError:
		return core.std.Expr(clips, expr)


# ============================== Matrix Constants ==============================

# BT.709 luma coefficients
_BT709_Kr = 0.2126
_BT709_Kg = 0.7152
_BT709_Kb = 0.0722

# BT.709 primaries (CIE xy)
_BT709_PRIMARIES = {
	"red":   (0.640, 0.330),
	"green": (0.300, 0.600),
	"blue":  (0.150, 0.060),
	"white": (0.3127, 0.3290),   # D65
}

# CAT16 matrix (CIECAM16 linear von Kries adaptation)
_CAT16 = [
	[ 0.401288,  0.650173, -0.051461],
	[-0.250268,  1.204414,  0.045854],
	[-0.002079,  0.048952,  0.953127],
]

# BT.709 full-range float YCbCr↔RGB matrices (precomputed)
_M_YCBCR2RGB = [
	[1.0,  0.0,                                              2.0 * (1.0 - _BT709_Kr)],
	[1.0, -2.0 * _BT709_Kb * (1.0 - _BT709_Kb) / _BT709_Kg, -2.0 * _BT709_Kr * (1.0 - _BT709_Kr) / _BT709_Kg],
	[1.0,  2.0 * (1.0 - _BT709_Kb),                          0.0],
]
_M_RGB2YCBCR = [
	[_BT709_Kr,                              _BT709_Kg,                              _BT709_Kb],
	[-_BT709_Kr / (2.0 * (1.0 - _BT709_Kb)), -_BT709_Kg / (2.0 * (1.0 - _BT709_Kb)), 0.5],
	[0.5,                                    -_BT709_Kg / (2.0 * (1.0 - _BT709_Kr)), -_BT709_Kb / (2.0 * (1.0 - _BT709_Kr))],
]

# Matrix name → VapourSynth matrix_s string mapping
_MATRIX_ID_TO_S = {
	0: "rgb",
	1: "709",
	2: "unspec",   # will fallback to 709
	4: "fcc",
	5: "470bg",
	6: "170m",
	7: "240m",
	8: "ycgco",
	9: "2020ncl",
	10: "2020cl",
	12: "chromancl",
	13: "chromacl",
	14: "ictcp",
}


# ============================== 3×3 Matrix Utils ==============================

def _mat3_identity():
	return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

def _mat3_mul(a, b):
	"""A := A * B  (returns new matrix = A * B)"""
	out = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
	for i in range(3):
		for j in range(3):
			out[i][j] = sum(a[i][k] * b[k][j] for k in range(3))
	return out

def _mat3_invert(m):
	"""Invert a 3×3 matrix using adjugate method (matching libplacebo)."""
	m00, m01, m02 = m[0]
	m10, m11, m12 = m[1]
	m20, m21, m22 = m[2]

	a00 =  (m11 * m22 - m21 * m12)
	a01 = -(m01 * m22 - m21 * m02)
	a02 =  (m01 * m12 - m11 * m02)
	a10 = -(m10 * m22 - m20 * m12)
	a11 =  (m00 * m22 - m20 * m02)
	a12 = -(m00 * m12 - m10 * m02)
	a20 =  (m10 * m21 - m20 * m11)
	a21 = -(m00 * m21 - m20 * m01)
	a22 =  (m00 * m11 - m10 * m01)

	det = m00 * a00 + m10 * a01 + m20 * a02
	if abs(det) < 1e-10:
		raise ValueError("Matrix is singular, cannot invert")
	inv_det = 1.0 / det

	return [
		[inv_det * a00, inv_det * a01, inv_det * a02],
		[inv_det * a10, inv_det * a11, inv_det * a12],
		[inv_det * a20, inv_det * a21, inv_det * a22],
	]

def _mat3_apply(m, v):
	"""Apply 3×3 matrix to a 3-element vector."""
	return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


# ============================= CIE Chroma Helpers =============================

def _cie_X(xy):
	"""Recover X/Y from CIE xy. Assumes Y=1."""
	return xy[0] / xy[1]

def _cie_Z(xy):
	"""Recover Z/Y from CIE xy. Assumes Y=1."""
	return (1.0 - xy[0] - xy[1]) / xy[1]


# ============================= Color Temp Models ==============================

def _blackbody_from_temp(temp):
	"""McCamy's approximation of Planck's law → CIE xy.
	Valid range: 1667K–25000K."""
	temp = max(1667.0, min(25000.0, temp))
	ti = 1000.0 / temp
	ti2 = ti * ti
	ti3 = ti2 * ti

	if temp <= 4000:
		x = -0.2661239 * ti3 - 0.2343580 * ti2 + 0.8776956 * ti + 0.179910
	else:
		x = -3.0258469 * ti3 + 2.1070379 * ti2 + 0.2226347 * ti + 0.240390

	x2 = x * x
	x3 = x2 * x
	if temp <= 2222:
		y = -1.1063814 * x3 - 1.34811020 * x2 + 2.18555832 * x - 0.20219683
	elif temp <= 4000:
		y = -0.9549476 * x3 - 1.37418593 * x2 + 2.09137015 * x - 0.16748867
	else:
		y =  3.0817580 * x3 - 5.87338670 * x2 + 3.75112997 * x - 0.37001483

	return (x, y)

def _daylight_from_temp(temp):
	"""CIE standard daylight illuminant → CIE xy.
	Valid range: 1000K–25000K."""
	temp = max(1000.0, min(25000.0, temp))
	ti = 1000.0 / temp
	ti2 = ti * ti
	ti3 = ti2 * ti

	if temp <= 7000:
		x = -4.6070 * ti3 + 2.9678 * ti2 + 0.09911 * ti + 0.244063
	else:
		x = -2.0064 * ti3 + 1.9018 * ti2 + 0.24748 * ti + 0.237040

	y = -3.0 * (x * x) + 2.87 * x - 0.275
	return (x, y)

def _white_from_temp(temp):
	"""Blended blackbody/daylight white point → CIE xy.
	- T < 2500K: pure blackbody
	- 2500K–4000K: linear blend
	- T > 4000K: pure daylight"""
	a = _blackbody_from_temp(temp)
	b = _daylight_from_temp(temp)
	f = (temp - 2500.0) / (4000.0 - 2500.0)
	f = max(0.0, min(1.0, f))
	return (
		(1.0 - f) * a[0] + f * b[0],
		(1.0 - f) * a[1] + f * b[1],
	)


# ======================== RGB↔XYZ Matrix Construction ========================

def _get_rgb2xyz_matrix(primaries):
	"""Compute RGB→XYZ matrix from CIE xy primaries.
	Port of pl_get_rgb2xyz_matrix()."""
	r, g, b, w = primaries["red"], primaries["green"], primaries["blue"], primaries["white"]
	X = [_cie_X(r), _cie_X(g), _cie_X(b), _cie_X(w)]
	Z = [_cie_Z(r), _cie_Z(g), _cie_Z(b), _cie_Z(w)]

	m = [
		[X[0], X[1], X[2]],
		[1.0,  1.0,  1.0],
		[Z[0], Z[1], Z[2]],
	]
	m_inv = _mat3_invert(m)

	# S = M^-1 * W
	S = [
		m_inv[i][0] * X[3] + m_inv[i][1] * 1.0 + m_inv[i][2] * Z[3]
		for i in range(3)
	]

	# M[i][j] = S[j] * XYZ[i][j]
	return [
		[S[0] * X[0], S[1] * X[1], S[2] * X[2]],
		[S[0] * 1.0,  S[1] * 1.0,  S[2] * 1.0],
		[S[0] * Z[0], S[1] * Z[1], S[2] * Z[2]],
	]


# ========================= Chroma Adaptation (CAT16) ==========================

def _apply_chromatic_adaptation(src_xy, dst_xy):
	"""Compute CAT16 chromatic adaptation matrix from src→dst white point.
	Port of apply_chromatic_adaptation(). Returns 3×3 matrix."""
	if abs(src_xy[0] - dst_xy[0]) < 1e-6 and abs(src_xy[1] - dst_xy[1]) < 1e-6:
		return _mat3_identity()
	src_XYZ = [_cie_X(src_xy), 1.0, _cie_Z(src_xy)]
	dst_XYZ = [_cie_X(dst_xy), 1.0, _cie_Z(dst_xy)]
	C_src = [sum(_CAT16[i][j] * src_XYZ[j] for j in range(3)) for i in range(3)]
	C_dst = [sum(_CAT16[i][j] * dst_XYZ[j] for j in range(3)) for i in range(3)]
	diag = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
	for i in range(3):
		diag[i][i] = C_dst[i] / C_src[i]
	tmp = _mat3_mul(diag, _CAT16)
	cat16_inv = _mat3_invert(_CAT16)
	return _mat3_mul(cat16_inv, tmp)

def _get_adaptation_matrix(src_xy, dst_xy):
	"""Compute full RGB adaptation matrix for white point shift.
	Port of pl_get_adaptation_matrix().
	Uses BT.709 primaries as RGB reference space."""
	prim = dict(_BT709_PRIMARIES)
	prim["white"] = src_xy
	rgb2xyz = _get_rgb2xyz_matrix(prim)
	xyz2rgb = _mat3_invert(rgb2xyz)
	adapt = _apply_chromatic_adaptation(src_xy, dst_xy)
	adapted_xyz2rgb = _mat3_mul(xyz2rgb, adapt)
	return _mat3_mul(adapted_xyz2rgb, rgb2xyz)

def _compute_temp_matrix(temperature):
	"""Compute the 3×3 RGB color temperature adaptation matrix.
	temperature: target color temperature in Kelvin (default neutral = 6500K).
	Returns a 3×3 matrix to apply in linear RGB (BT.709) space."""
	src_xy = _white_from_temp(6500.0)
	dst_xy = _white_from_temp(float(temperature))
	return _get_adaptation_matrix(src_xy, dst_xy)


# ============================== Format Helpers ================================

def _get_matrix_s(clip, matrix):
	if matrix is not None:
		if isinstance(matrix, int):
			s = _MATRIX_ID_TO_S.get(matrix, "709")
		else:
			s = str(matrix)
	else:
		# Try to read from first frame's properties
		try:
			frame = clip.get_frame(0)
			mat_id = frame.props.get("_Matrix", 2)
			s = _MATRIX_ID_TO_S.get(mat_id, "709")
		except Exception:
			s = "709"
	# "unspec" and "rgb" are not usable conversion matrices — fall back to BT.709
	return s if s not in ("unspec", "rgb") else "709"

def _is_rgb(clip):
	return clip.format.color_family == vs.RGB

def _is_yuv(clip):
	return clip.format.color_family == vs.YUV

def _is_gray(clip):
	return clip.format.color_family == vs.GRAY

def _get_range(clip):
	"""0 (full) or 1 (limited), or None."""
	try:
		frame = clip.get_frame(0)
		return frame.props.get("_ColorRange", None)
	except Exception:
		return None

def _to_yuv444ps(clip, matrix):
	mat_s = _get_matrix_s(clip, matrix)
	if clip.format.id == vs.YUV444PS:
		return clip
	if _is_rgb(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PS, matrix_s=mat_s)
	if _is_yuv(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PS)
	if _is_gray(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PS)
	return core.resize.Bilinear(clip, format=vs.YUV444PS)

def _to_yuv444ph(clip, matrix):
	mat_s = _get_matrix_s(clip, matrix)
	if clip.format.id == vs.YUV444PH:
		return clip
	if _is_rgb(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PH, matrix_s=mat_s)
	if _is_yuv(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PH)
	if _is_gray(clip):
		return core.resize.Bilinear(clip, format=vs.YUV444PH)
	return core.resize.Bilinear(clip, format=vs.YUV444PH)

def _to_rgbs(clip, matrix):
	mat_s = _get_matrix_s(clip, matrix)
	if clip.format.id == vs.RGBS:
		return clip
	if _is_yuv(clip) or _is_gray(clip):
		return core.resize.Bilinear(clip, format=vs.RGBS, matrix_in_s=mat_s)
	if _is_rgb(clip):
		return core.resize.Bilinear(clip, format=vs.RGBS)
	return core.resize.Bilinear(clip, format=vs.RGBS)

def _to_rgbh(clip, matrix):
	mat_s = _get_matrix_s(clip, matrix)
	if clip.format.id == vs.RGBH:
		return clip
	if _is_yuv(clip) or _is_gray(clip):
		return core.resize.Bilinear(clip, format=vs.RGBH, matrix_in_s=mat_s)
	if _is_rgb(clip):
		return core.resize.Bilinear(clip, format=vs.RGBH)
	return core.resize.Bilinear(clip, format=vs.RGBH)

def _restore_format(clip, orig_format, matrix, range_val=None):
	if clip.format.id == orig_format.id:
		return clip
	mat_s = _get_matrix_s(clip, matrix)
	src_is_rgb = _is_rgb(clip)
	dst_is_rgb = (orig_format.color_family == vs.RGB)
	dst_is_yuv = (orig_format.color_family == vs.YUV)

	kwargs = {}
	if range_val is not None and orig_format.sample_type == vs.INTEGER and not dst_is_rgb:
		kwargs['range'] = range_val

	if src_is_rgb and dst_is_yuv:
		return core.resize.Bilinear(clip, format=orig_format.id, matrix_s=mat_s, **kwargs)
	if not src_is_rgb and dst_is_rgb:
		return core.resize.Bilinear(clip, format=orig_format.id, matrix_in_s=mat_s, **kwargs)
	return core.resize.Bilinear(clip, format=orig_format.id, **kwargs)

def _to_float_native(clip):
	fmt = clip.format
	if fmt.sample_type == vs.FLOAT and fmt.bits_per_sample == 32:
		return clip
	target = core.query_video_format(fmt.color_family, vs.FLOAT, 32, fmt.subsampling_w, fmt.subsampling_h)
	return core.resize.Point(clip, format=target.id)

def _from_float_native(clip, orig_format):
	if clip.format.id == orig_format.id:
		return clip
	return core.resize.Point(clip, format=orig_format.id)


# ==============================================================================

def PEQ_BRI(
	clip,
	brightness=0.0,
	matrix=None,
	clamp=False
):
	"""亮度调整 (Brightness)

	- YUV 输入：仅对 Y 平面加偏移，色度不变
	- RGB 输入：直接对 R/G/B 三个通道加偏移
	- GRAY 输入：对单通道加偏移

	Args:
		brightness: 亮度偏移量。-1.0 = 纯黑, 0.0 = 不变, 1.0 = 纯白。默认 0.0
		matrix:     色彩矩阵覆盖 (int / str / None)。None 时自动从帧属性 ``_Matrix`` 检测，回退 BT.709
		clamp:      是否将输出钳位到合法范围 (float: 0~1)。默认 False

	Returns:
		保持原始格式
	"""
	if brightness == 0.0:
		return clip

	fmt = clip.format
	if fmt.sample_type == vs.INTEGER:
		peak = (1 << fmt.bits_per_sample) - 1
		offset = brightness * peak
		expr = f"x {offset} +"
		if clamp:
			expr += f" 0 max {peak} min"
	else:
		expr = f"x {brightness} +"
		if clamp:
			expr += " 0 max 1 min"
	if _is_yuv(clip):
		return _Expr(clip, [expr, "", ""])
	return _Expr(clip, [expr] * fmt.num_planes)

def PEQ_CONT(
	clip,
	contrast=1.0,
	matrix=None,
	clamp=False
):
	"""对比度调整 (Contrast)

	- YUV 输入：Y, U, V 三平面均乘以 contrast
	- RGB 输入：直接对 R/G/B 三通道乘以 contrast
	- GRAY 输入：对单通道乘以 contrast

	Args:
		contrast: 对比度乘数。0.0 = 纯黑, 1.0 = 不变, >1.0 = 增强。默认 1.0
		matrix:   色彩矩阵覆盖 (int / str / None)。默认 None (自动检测)
		clamp:    是否钳位输出。默认 False

	Returns:
		保持原始格式
	"""
	if contrast == 1.0:
		return clip

	fmt = clip.format
	expr_y = f"x {contrast} *"

	if _is_yuv(clip):
		if fmt.sample_type == vs.INTEGER:
			gray = 1 << (fmt.bits_per_sample - 1)
			peak = (1 << fmt.bits_per_sample) - 1
			expr_c = f"x {gray} - {contrast} * {gray} +"
			if clamp:
				expr_y += f" 0 max {peak} min"
				expr_c += f" 0 max {peak} min"
		else:
			expr_c = f"x {contrast} *"
			if clamp:
				expr_y += " 0 max 1 min"
				expr_c += " -0.5 max 0.5 min"
		return _Expr(clip, [expr_y, expr_c, expr_c])

	# RGB or GRAY
	if clamp:
		if fmt.sample_type == vs.INTEGER:
			peak = (1 << fmt.bits_per_sample) - 1
			expr_y += f" 0 max {peak} min"
		else:
			expr_y += " 0 max 1 min"
	return _Expr(clip, [expr_y] * fmt.num_planes)

def PEQ_SAT(
	clip,
	saturation=1.0,
	matrix=None,
	clamp=False
):
	"""饱和度调整 (Saturation)

	- YUV 输入：仅对 U, V 色度平面乘以 saturation，Y 不变
	- RGB 输入：自动转 YUV444PS → 调整 → 转回原格式
	- GRAY 输入：无色度可调，直接返回

	Args:
		saturation: 饱和度乘数。0.0 = 灰阶, 1.0 = 不变, >1.0 = 增强。默认 1.0
		matrix:     色彩矩阵覆盖。默认 None (自动检测)
		clamp:      是否钳位色度到 [-0.5, 0.5]。默认 False

	Returns:
		保持原始格式。
	"""
	if saturation == 1.0:
		return clip

	if _is_gray(clip):
		return clip  # no chroma to adjust

	fmt = clip.format

	if _is_rgb(clip):
		orig_format = fmt
		work = _to_yuv444ph(clip, matrix)
		expr_c = f"x {saturation} *"
		if clamp:
			expr_c += " -0.5 max 0.5 min"
		work = _Expr(work, ["", expr_c, expr_c])
		return _restore_format(work, orig_format, matrix)

	# YUV: operate directly on native format
	if fmt.sample_type == vs.INTEGER:
		gray = 1 << (fmt.bits_per_sample - 1)
		peak = (1 << fmt.bits_per_sample) - 1
		expr_c = f"x {gray} - {saturation} * {gray} +"
		if clamp:
			expr_c += f" 0 max {peak} min"
	else:
		expr_c = f"x {saturation} *"
		if clamp:
			expr_c += " -0.5 max 0.5 min"
	return _Expr(clip, ["", expr_c, expr_c])

def PEQ_HUE(
	clip,
	hue=0.0,
	matrix=None,
	clamp=False
):
	"""色相旋转 (Hue)

	- YUV 输入：提取 U, V 平面，旋转后重组，Y 不变
	- RGB 输入：自动转 YUV444PS → 旋转 → 转回原格式
	- GRAY 输入：无色度可旋转，直接返回

	Args:
		hue:    色相旋转角度 (度)。0 = 不变, 180 = 反色, 360 = 回到原点。默认 0.0
		matrix: 色彩矩阵覆盖。默认 None (自动检测)
		clamp:  是否钳位色度到 [-0.5, 0.5]。默认 False

	Returns:
		保持原始格式。
	"""
	hue = hue % 360.0
	if hue == 0.0:
		return clip

	if _is_gray(clip):
		return clip  # no chroma to rotate

	hue_rad = math.radians(hue)
	cos_h = math.cos(hue_rad)
	sin_h = math.sin(hue_rad)

	fmt = clip.format

	if _is_rgb(clip):
		orig_format = fmt
		work = _to_yuv444ph(clip, matrix)
		u = core.std.ShufflePlanes(work, planes=1, colorfamily=vs.GRAY)
		v = core.std.ShufflePlanes(work, planes=2, colorfamily=vs.GRAY)
		expr_u = f"x {cos_h} * y {sin_h} * +"
		expr_v = f"y {cos_h} * x {sin_h} * -"
		if clamp:
			expr_u += " -0.5 max 0.5 min"
			expr_v += " -0.5 max 0.5 min"
		new_u = _Expr([u, v], expr_u)
		new_v = _Expr([u, v], expr_v)
		y = core.std.ShufflePlanes(work, planes=0, colorfamily=vs.GRAY)
		work = core.std.ShufflePlanes([y, new_u, new_v], planes=[0, 0, 0], colorfamily=vs.YUV)
		return _restore_format(work, orig_format, matrix)

	# YUV: operate directly on native format, no conversion
	u = core.std.ShufflePlanes(clip, planes=1, colorfamily=vs.GRAY)
	v = core.std.ShufflePlanes(clip, planes=2, colorfamily=vs.GRAY)

	if fmt.sample_type == vs.INTEGER:
		gray = 1 << (fmt.bits_per_sample - 1)
		peak = (1 << fmt.bits_per_sample) - 1
		expr_u = f"x {gray} - {cos_h} * y {gray} - {sin_h} * + {gray} +"
		expr_v = f"y {gray} - {cos_h} * x {gray} - {sin_h} * - {gray} +"
		if clamp:
			expr_u += f" 0 max {peak} min"
			expr_v += f" 0 max {peak} min"
	else:
		expr_u = f"x {cos_h} * y {sin_h} * +"
		expr_v = f"y {cos_h} * x {sin_h} * -"
		if clamp:
			expr_u += " -0.5 max 0.5 min"
			expr_v += " -0.5 max 0.5 min"

	new_u = _Expr([u, v], expr_u)
	new_v = _Expr([u, v], expr_v)
	return core.std.ShufflePlanes([clip, new_u, new_v], planes=[0, 0, 0], colorfamily=fmt.color_family)

def PEQ_GAMMA(
	clip,
	gamma=1.0,
	matrix=None,
	clamp=False
):
	"""伽马调整 (Gamma)。

	- 任意输入格式(YUV / RGB / GRAY)均自动转 RGBH (16-bit half-float RGB) 处理后转回。
	- gamma = 0 为特殊情况：输出纯黑（避免除零，匹配 libplacebo）。

	Args:
		gamma:  伽马指数。0 = 纯黑, 1.0 = 不变, >1.0 = 提亮暗部, <1.0 = 压暗。默认 1.0
		matrix: 色彩矩阵覆盖。默认 None (自动检测)
		clamp:  是否钳位输出到 [0, 1]。默认 False

	Returns:
		保持原始格式。
	"""
	if gamma == 1.0:
		return clip
	if gamma == 0.0:
		# Avoid division by zero — solid black
		if _is_rgb(clip):
			return _Expr(clip, ["0"] * 3)
		elif _is_yuv(clip):
			fmt = clip.format
			if fmt.sample_type == vs.INTEGER:
				gray = str(1 << (fmt.bits_per_sample - 1))
				return _Expr(clip, ["0", gray, gray])
			else:
				return _Expr(clip, ["0", "0", "0"])
		else:
			return _Expr(clip, ["0"])

	inv_gamma = 1.0 / gamma
	orig_format = clip.format
	fmt = clip.format

	# Integer RGB/GRAY: normalize within Expr, avoid format conversion
	if fmt.sample_type == vs.INTEGER and not _is_yuv(clip):
		peak = (1 << fmt.bits_per_sample) - 1
		inv_peak = 1.0 / peak
		expr = f"x {inv_peak} * 1e-6 max {inv_gamma} pow {peak} * x 0 > *"
		if clamp:
			expr += f" 0 max {peak} min"
		return _Expr(clip, [expr] * fmt.num_planes)

	range_val = _get_range(clip) if _is_yuv(clip) and fmt.sample_type == vs.INTEGER else None
	work = _to_rgbh(clip, matrix)

	expr = f"x 0 max 1e-6 max {inv_gamma} pow x 0 > *"
	if clamp:
		expr += " 0 max 1 min"
	work = _Expr(work, [expr] * 3)

	return _restore_format(work, orig_format, matrix, range_val)

def PEQ_TEMP(clip, temperature=6500, matrix=None, clamp=False):
	"""色温调整 (Color Temperature)。

	- 任意输入格式(YUV / RGB / GRAY)均自动转 RGBH 处理后转回。
	- 低于 6500K = 偏暖 (红增/蓝减), 高于 6500K = 偏冷 (红减/蓝增)。

	Args:
		temperature: 目标色温 (开尔文)。1667~25000, 6500 = D65 中性。默认 6500
		matrix:      色彩矩阵覆盖。默认 None (自动检测)
		clamp:       是否钳位输出到 [0, 1]。默认 False

	Returns:
		保持原始格式。
	"""
	if temperature == 6500:
		return clip

	temperature = max(1667.0, min(25000.0, float(temperature)))

	# Precompute the 3×3 adaptation matrix
	m = _compute_temp_matrix(temperature)

	orig_format = clip.format
	range_val = _get_range(clip) if _is_yuv(clip) and clip.format.sample_type == vs.INTEGER else None

	# Integer RGB: apply matrix directly (linear, no normalization needed)
	if _is_rgb(clip) and clip.format.sample_type == vs.INTEGER:
		peak = (1 << clip.format.bits_per_sample) - 1
		r = core.std.ShufflePlanes(clip, planes=0, colorfamily=vs.GRAY)
		g = core.std.ShufflePlanes(clip, planes=1, colorfamily=vs.GRAY)
		b = core.std.ShufflePlanes(clip, planes=2, colorfamily=vs.GRAY)

		exprs = []
		for i in range(3):
			e = f"x {m[i][0]} * y {m[i][1]} * + z {m[i][2]} * +"
			if clamp:
				e += f" 0 max {peak} min"
			exprs.append(_Expr([r, g, b], e))

		return core.std.ShufflePlanes(exprs, planes=[0, 0, 0], colorfamily=vs.RGB)

	work = _to_rgbh(clip, matrix)

	r = core.std.ShufflePlanes(work, planes=0, colorfamily=vs.GRAY)
	g = core.std.ShufflePlanes(work, planes=1, colorfamily=vs.GRAY)
	b = core.std.ShufflePlanes(work, planes=2, colorfamily=vs.GRAY)

	# Apply 3×3 matrix: out[i] = m[i][0]*R + m[i][1]*G + m[i][2]*B
	expr_r = f"x {m[0][0]} * y {m[0][1]} * + z {m[0][2]} * +"
	expr_g = f"x {m[1][0]} * y {m[1][1]} * + z {m[1][2]} * +"
	expr_b = f"x {m[2][0]} * y {m[2][1]} * + z {m[2][2]} * +"
	if clamp:
		expr_r += " 0 max 1 min"
		expr_g += " 0 max 1 min"
		expr_b += " 0 max 1 min"

	new_r = _Expr([r, g, b], expr_r)
	new_g = _Expr([r, g, b], expr_g)
	new_b = _Expr([r, g, b], expr_b)

	work = core.std.ShufflePlanes([new_r, new_g, new_b], planes=[0, 0, 0], colorfamily=vs.RGB)

	return _restore_format(work, orig_format, matrix, range_val)


# ==============================================================================

def PEQ(
	input : vs.VideoNode,
	saturation : float =1.0,
	hue : float =0.0,
	contrast : float =1.0,
	brightness : float =0.0,
	temperature : float =6500,
	gamma : float =1.0,
	matrix = None,
	clamp : bool =False
) -> vs.VideoNode :
	"""组合色彩调整

	Args:
		input:       输入 (YUV / RGB / GRAY)
		saturation:  饱和度乘数。0.0+ (0=灰阶), 默认 1.0 (不变)
		hue:         色相旋转角度 (度)。默认 0.0 (不变)
		contrast:    对比度乘数。0.0+ , 默认 1.0 (不变)
		brightness:  亮度偏移。-1.0 ~ 1.0, 默认 0.0 (不变)
		temperature: 色温 (开尔文)。1667~25000, 默认 6500 (D65 中性)
		gamma:       伽马指数。0.0+ (0=纯黑), 默认 1.0 (不变)
		matrix:      色彩矩阵覆盖 (int / str / None)。默认 None (自动检测，回退 BT.709)
		clamp:       是否将输出钳位到合法范围。默认 False

	Returns:
		保持原始格式。
	"""
	hue = hue % 360.0
	has_adj = (saturation != 1.0 or hue != 0.0 or contrast != 1.0)
	has_bri = (brightness != 0.0)
	has_temp = (temperature != 6500)
	has_gamma = (gamma != 1.0)

	clip = input

	if not has_adj and not has_bri and not has_temp and not has_gamma:
		return clip

	orig_format = clip.format

	# gamma=0 special case: solid black
	if gamma == 0.0:
		if _is_rgb(clip):
			return _Expr(clip, ["0"] * 3)
		elif _is_gray(clip):
			return _Expr(clip, ["0"])
		else:
			fmt = clip.format
			if fmt.sample_type == vs.INTEGER:
				gray = str(1 << (fmt.bits_per_sample - 1))
				return _Expr(clip, ["0", gray, gray])
			else:
				return _Expr(clip, ["0", "0", "0"])

	# Precompute hue/sat coefficients
	hue_rad = math.radians(hue)
	huecos = saturation * math.cos(hue_rad)
	huesin = saturation * math.sin(hue_rad)
	need_rgb = (has_temp or has_gamma)

	# ── Native fast path: no temp/gamma, YUV or GRAY input ──
	if not need_rgb and not _is_rgb(clip):
		if _is_gray(clip):
			fmt = clip.format
			expr = "x"
			if contrast != 1.0:
				expr = f"x {contrast} *"
			if has_bri:
				if fmt.sample_type == vs.INTEGER:
					expr += f" {brightness * ((1 << fmt.bits_per_sample) - 1)} +"
				else:
					expr += f" {brightness} +"
			if clamp:
				if fmt.sample_type == vs.INTEGER:
					expr += f" 0 max {(1 << fmt.bits_per_sample) - 1} min"
				else:
					expr += " 0 max 1 min"
			return _Expr(clip, [expr]) if expr != "x" else clip

		# YUV: apply sat/hue/contrast/brightness directly in native format
		fmt = clip.format
		is_int = (fmt.sample_type == vs.INTEGER)
		c_huecos = contrast * huecos
		c_huesin = contrast * huesin

		if is_int:
			peak = (1 << fmt.bits_per_sample) - 1
			gray = 1 << (fmt.bits_per_sample - 1)

		# Y expression
		expr_y = "x"
		if contrast != 1.0:
			expr_y = f"x {contrast} *"
		if has_bri:
			bri_val = brightness * peak if is_int else brightness
			expr_y += f" {bri_val} +"

		has_chroma_adj = (saturation != 1.0 or hue != 0.0)

		if has_chroma_adj:
			u = core.std.ShufflePlanes(clip, planes=1, colorfamily=vs.GRAY)
			v = core.std.ShufflePlanes(clip, planes=2, colorfamily=vs.GRAY)

			if is_int:
				expr_u = f"x {gray} - {c_huecos} * y {gray} - {c_huesin} * + {gray} +"
				expr_v = f"y {gray} - {c_huecos} * x {gray} - {c_huesin} * - {gray} +"
			else:
				expr_u = f"x {c_huecos} * y {c_huesin} * +"
				expr_v = f"y {c_huecos} * x {c_huesin} * -"

			if clamp:
				if is_int:
					expr_y += f" 0 max {peak} min"
					expr_u += f" 0 max {peak} min"
					expr_v += f" 0 max {peak} min"
				else:
					expr_y += " 0 max 1 min"
					expr_u += " -0.5 max 0.5 min"
					expr_v += " -0.5 max 0.5 min"

			new_u = _Expr([u, v], expr_u)
			new_v = _Expr([u, v], expr_v)
			y_plane = core.std.ShufflePlanes(clip, planes=0, colorfamily=vs.GRAY)
			if expr_y != "x":
				y_plane = _Expr(y_plane, expr_y)
			return core.std.ShufflePlanes([y_plane, new_u, new_v],
			                              planes=[0, 0, 0], colorfamily=fmt.color_family)
		else:
			# Only contrast and/or brightness, no sat/hue
			if is_int:
				expr_c = f"x {gray} - {contrast} * {gray} +" if contrast != 1.0 else ""
			else:
				expr_c = f"x {contrast} *" if contrast != 1.0 else ""
			if clamp:
				if is_int:
					if expr_y != "x":
						expr_y += f" 0 max {peak} min"
					if expr_c:
						expr_c += f" 0 max {peak} min"
				else:
					if expr_y != "x":
						expr_y += " 0 max 1 min"
					if expr_c:
						expr_c += " -0.5 max 0.5 min"
			return _Expr(clip, [expr_y if expr_y != "x" else "",
			                            expr_c, expr_c])

	# ── RGBH path: temp/gamma needed, or RGB input ──
	range_val = _get_range(clip) if orig_format.sample_type == vs.INTEGER and not _is_rgb(clip) else None
	mat_s = _get_matrix_s(clip, matrix)

	# Build combined 3×3 matrix + offset in RGB space
	m_adj = [
		[contrast,  0.0,                  0.0],
		[0.0,       contrast * huecos,    contrast * huesin],
		[0.0,      -contrast * huesin,    contrast * huecos],
	]
	m_combined = _mat3_mul(_mat3_mul(_M_YCBCR2RGB, m_adj), _M_RGB2YCBCR)

	if has_temp:
		temp_m = _compute_temp_matrix(temperature)
		m_final = _mat3_mul(temp_m, m_combined)
	else:
		m_final = m_combined

	offset = [brightness, brightness, brightness]
	is_scalar = (saturation == 1.0 and hue == 0.0 and not has_temp)

	if clip.format.id == vs.RGBH:
		work = clip
	elif _is_yuv(clip) or _is_gray(clip):
		work = core.resize.Bilinear(clip, format=vs.RGBH, matrix_in_s=mat_s)
	else:
		work = core.resize.Bilinear(clip, format=vs.RGBH)

	# Build suffix: gamma + clamp
	suffix = ""
	if has_gamma:
		suffix += f" dup 0 max 1e-6 max {1.0 / gamma} pow swap 0 > *"
	if clamp:
		suffix += " 0 max 1 min"

	# Apply combined expression
	if is_scalar:
		expr = "x"
		if contrast != 1.0:
			expr = f"x {contrast} *"
		if has_bri:
			expr = f"{expr} {brightness} +" if expr != "x" else f"x {brightness} +"
		expr += suffix
		if expr != "x":
			work = _Expr(work, [expr] * 3)
	else:
		r = core.std.ShufflePlanes(work, planes=0, colorfamily=vs.GRAY)
		g = core.std.ShufflePlanes(work, planes=1, colorfamily=vs.GRAY)
		b = core.std.ShufflePlanes(work, planes=2, colorfamily=vs.GRAY)

		planes = []
		for i in range(3):
			e = f"x {m_final[i][0]} * y {m_final[i][1]} * + z {m_final[i][2]} * +"
			if offset[i] != 0.0:
				e += f" {offset[i]} +"
			e += suffix
			planes.append(_Expr([r, g, b], e))

		work = core.std.ShufflePlanes(planes, planes=[0, 0, 0], colorfamily=vs.RGB)

	if work.format.id == orig_format.id:
		return work
	dst_is_yuv = (orig_format.color_family == vs.YUV)
	dst_is_gray = (orig_format.color_family == vs.GRAY)
	kwargs = {}
	if range_val is not None and orig_format.sample_type == vs.INTEGER:
		kwargs['range'] = range_val
	if dst_is_yuv or dst_is_gray:
		return core.resize.Bilinear(work, format=orig_format.id, matrix_s=mat_s, **kwargs)
	return core.resize.Bilinear(work, format=orig_format.id, **kwargs)

