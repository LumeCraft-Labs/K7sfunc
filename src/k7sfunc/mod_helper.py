"""辅助函数模块

"""

import vapoursynth as vs
import typing
import math
from ._internal import (
	_validate_input_clip,
	_validate_bool,
	_check_plugin,
	_check_script,
	core,
)

__all__ = [
	"COLOR_P3W_FIX",
	"FMT2YUV_SP",
	"DCF",
	"EQ",
	"LAYER_HIGH",
	"LINE_MASK",
	"PLANE_EXTR",
	"RANGE_CHANGE",
	"ONNX_ANZ",
	"PIX_CLP",
	"SCENE_DETECT",
	"SCDetect2",
]

##################################################
## https://github.com/mpv-player/mpv/issues/11460
## 修复p3错误转换后的白点 # helper
##################################################

def COLOR_P3W_FIX(
	input : vs.VideoNode,
	linear : bool = False,
) -> vs.VideoNode :

	func_name = "COLOR_P3W_FIX"

	_check_plugin(func_name, "fmtc")

	colorlv = input.get_frame(0).props._ColorRange

	cut = core.resize.Bilinear(clip=input, format=vs.RGB48, matrix_in_s="709")
	if linear :
		cut = core.fmtc.transfer(clip=cut, transs="1886", transd="linear")
	cut = core.fmtc.primaries(clip=cut, prims="p3d65", primd="p3dci", wconv=True)
	if linear :
		cut = core.fmtc.transfer(clip=cut, transs="linear", transd="1886")

	output = core.resize.Bilinear(clip=cut, format=vs.YUV420P8, matrix_s="709", range=1 if colorlv==0 else None)

	return output

##################################################
## 格式转换 特殊
##################################################

def FMT2YUV_SP(
	input : vs.VideoNode,
) -> tuple[vs.VideoNode, vs.VideoNode] :

	fmt_in = input.format.id
	clip = input
	if fmt_in == vs.YUV420P8 :
		clip8 = clip
	elif fmt_in == vs.YUV420P10 :
		clip8 = core.resize.Bilinear(clip=clip, format=vs.YUV420P8)
	else :
		clip = core.resize.Bilinear(clip=clip, format=vs.YUV420P10)
		clip8 = core.resize.Bilinear(clip=clip, format=vs.YUV420P8)
	return clip, clip8

##################################################
## idea FM chaiNNer (9e8b53888215df850d8e237598baf9b1eb6006a8)
## 分频色彩修复
##################################################

def DCF(
	input : vs.VideoNode,
	ref : vs.VideoNode,
	rad : int = 5,
	bp : int = 4,
	fast : bool = True,
) -> vs.VideoNode :

	func_name = "DCF"

	_check_plugin(func_name, "vszip")

	fmt_in = input.format.id
	fmt_ref = ref.format.id
	w_in, h_in = input.width, input.height
	w_ref, h_ref = ref.width, ref.height

	# 仅考虑输入为RGBH或RGBS的情况
	clip = core.resize.Point(clip=input, format=vs.RGBS) if fmt_in != vs.RGBS else input
	ref = core.resize.Point(clip=ref, format=vs.RGBS) if fmt_ref != vs.RGBS else ref
	clip_orig = clip
	need_resize = w_ref != w_in or h_ref != h_in

	if need_resize :
		if fast :
			clip = core.resize.Bilinear(clip=clip, width=w_ref, height=h_ref)
		else :
			ref = core.resize.Bilinear(clip=ref, width=w_in, height=h_in)

	planes = [0, 1, 2]
	blur_in = core.vszip.BoxBlur(clip=clip, planes=planes, hradius=rad, hpasses=bp, vradius=rad, vpasses=bp)
	blur_ref = core.vszip.BoxBlur(clip=ref, planes=planes, hradius=rad, hpasses=bp, vradius=rad, vpasses=bp)

	diff = core.std.MakeDiff(clipa=blur_ref, clipb=blur_in, planes=planes)
	if fast and need_resize :
		diff = core.resize.Bilinear(clip=diff, width=w_in, height=h_in)

	output = core.std.MergeDiff(clipa=clip_orig if fast else clip, clipb=diff, planes=planes)

	return output

##################################################
## PORT adjust (a3af7cb57cb37747b0667346375536e65b1fed17)
## 均衡器
##################################################

def EQ(
	input : vs.VideoNode,
	hue : typing.Optional[float] = None,
	sat : typing.Optional[float] = None,
	bri : typing.Optional[float] = None,
	cont : typing.Optional[float] = None,
	coring : bool = True,
) -> vs.VideoNode :

	fmt_src = input.format
	fmt_cf_in = fmt_src.color_family
	fmt_bit_in = fmt_src.bits_per_sample

	clip = input

	if hue is not None or sat is not None :
		hue = 0.0 if hue is None else hue
		sat = 1.0 if sat is None else sat
		hue = hue * math.pi / 180.0
		hue_sin = math.sin(hue)
		hue_cos = math.cos(hue)
		gray = 128 << (fmt_bit_in - 8)
		chroma_min = 0
		chroma_max = (2 ** fmt_bit_in) - 1
		if coring:
			chroma_min = 16 << (fmt_bit_in - 8)
			chroma_max = 240 << (fmt_bit_in - 8)
		expr_u = "x {} - {} * y {} - {} * + {} + {} max {} min".format(
			gray, hue_cos * sat, gray, hue_sin * sat, gray, chroma_min, chroma_max)
		expr_v = "y {} - {} * x {} - {} * - {} + {} max {} min".format(
			gray, hue_cos * sat, gray, hue_sin * sat, gray, chroma_min, chroma_max)
		src_u = core.std.ShufflePlanes(clips=clip, planes=1, colorfamily=vs.GRAY)
		src_v = core.std.ShufflePlanes(clips=clip, planes=2, colorfamily=vs.GRAY)
		dst_u = core.std.Expr(clips=[src_u, src_v], expr=expr_u)
		dst_v = core.std.Expr(clips=[src_u, src_v], expr=expr_v)

		clip = core.std.ShufflePlanes(clips=[clip, dst_u, dst_v], planes=[0, 0, 0], colorfamily=fmt_cf_in)

	if bri is not None or cont is not None :
		bri = 0.0 if bri is None else bri
		cont = 1.0 if cont is None else cont
		luma_lut = []
		luma_min = 0
		luma_max = (2 ** fmt_bit_in) - 1
		if coring :
			luma_min = 16 << (fmt_bit_in - 8)
			luma_max = 235 << (fmt_bit_in - 8)
		for i in range(2 ** fmt_bit_in) :
			val = int((i - luma_min) * cont + bri + luma_min + 0.5)
			luma_lut.append(min(max(val, luma_min), luma_max))

		clip = core.std.Lut(clip=clip, planes=0, lut=luma_lut)

	return clip

##################################################
## 提取高频层
##################################################

def LAYER_HIGH(
	input : vs.VideoNode,
	blur_m : typing.Literal[0, 1, 2] = 2,
) -> tuple[vs.VideoNode, vs.VideoNode] :

	fmt_in = input.format.id

	if fmt_in == vs.YUV444P16 :
		cut0 = input
	else :
		cut0 = core.resize.Bilinear(clip=input, format=vs.YUV444P16)
	if blur_m == 0 :
		output_blur = cut0
		output_diff = None
	elif blur_m == 1 :
		blur = core.zsmooth.RemoveGrain(clip=cut0, mode=20)
		blur = core.zsmooth.RemoveGrain(clip=blur, mode=20)
		output_blur = core.zsmooth.RemoveGrain(clip=blur, mode=20)
	elif blur_m == 2 :
		blur = core.std.Convolution(clip=cut0, matrix=[1, 1, 1, 1, 1, 1, 1, 1, 1])
		blur = core.std.Convolution(clip=blur, matrix=[1, 1, 1, 1, 1, 1, 1, 1, 1])
		output_blur = core.std.Convolution(clip=blur, matrix=[1, 1, 1, 1, 1, 1, 1, 1, 1])

	if blur_m :
		output_diff = core.std.MakeDiff(clipa=cut0, clipb=blur)

	return output_blur, output_diff

##################################################
## 提取线条
##################################################

def LINE_MASK(
	input : vs.VideoNode,
	cpu : bool = True,
	gpu : typing.Literal[-1, 0, 1, 2] = -1,
	plane : typing.List[int] = [0],
) -> vs.VideoNode :

	if cpu : # r13+
		output = core.tcanny.TCanny(clip=input, sigma=1.5, t_h=8.0, t_l=1.0,
									mode=0, op=1, planes=plane)
	else : # r12
		output = core.tcanny.TCannyCL(clip=input, sigma=1.5, t_h=8.0, t_l=1.0,
									  mode=0, op=1, device=gpu, planes=plane)

	return output

##################################################
## 分离平面
##################################################

def PLANE_EXTR(
	input : vs.VideoNode,
) -> vs.VideoNode :

	''' obs
	output = []
	for plane in range(input.format.num_planes) :
		clips = core.std.ShufflePlanes(clips=input, planes=plane, colorfamily=vs.GRAY)
		output.append(clips)
	'''

	output = core.std.SplitPlanes(clip=input)

	return output

##################################################
## 动态范围修正
##################################################

def RANGE_CHANGE(
	input : vs.VideoNode,
	l2f : bool = True,
) -> vs.VideoNode :

	fmt_in = input.format.id

	cut0 = input
	if fmt_in in [vs.YUV420P8, vs.YUV422P8, vs.YUV410P8, vs.YUV411P8, vs.YUV440P8, vs.YUV444P8] :
		lv_val_pre = 0
	elif fmt_in in [vs.YUV420P10, vs.YUV422P10, vs.YUV444P10] :
		lv_val_pre = 1
	elif fmt_in in [vs.YUV420P16, vs.YUV422P16, vs.YUV444P16] :
		lv_val_pre = 2
	else :
		cut0 = core.resize.Bilinear(clip=cut0, format=vs.YUV444P16)
		lv_val_pre = 2

	lv_val1 = [16, 64, 4096][lv_val_pre]
	lv_val2 = [235, 940, 60160][lv_val_pre]
	lv_val2_alt = [240, 960, 61440][lv_val_pre]
	lv_val3 = 0
	lv_val4 = [255, 1023, 65535][lv_val_pre]
	if l2f :
		cut1 = core.std.Levels(clip=cut0, min_in=lv_val1, max_in=lv_val2,
							   min_out=lv_val3, max_out=lv_val4, planes=0)
		output = core.std.Levels(clip=cut1, min_in=lv_val1, max_in=lv_val2_alt,
								 min_out=lv_val3, max_out=lv_val4, planes=[1,2])
	else :
		cut1 = core.std.Levels(clip=cut0, min_in=lv_val3, max_in=lv_val4,
							   min_out=lv_val1, max_out=lv_val2, planes=0)
		output = core.std.Levels(clip=cut1, min_in=lv_val3, max_in=lv_val4,
								 min_out=lv_val1, max_out=lv_val2_alt, planes=[1,2])

	return output

##################################################
## 解析ONNX
##################################################

def ONNX_ANZ(
	input : str = "",
	loose : typing.Literal[0, 1, 2] = 1,
) -> dict :
	"""解析ONNX模型信息
	Args:
		loose:
			0 - 严格模式：维度必须为 [-1/1, 1/3, -1, -1] + 结构检查
			1 - 标准模式：维度必须为 [-1/1, 1/3, -1, -1]
			2 - 宽松模式：允许静态维度，但通道数必须为 1 或 3
	Returns:
		dict: 包含 valid, elem_type, elem_type_name, shape, error
	"""

	func_name = "ONNX_ANZ"
	onnx = _check_script(func_name, "onnx")
	from onnx import TensorProto

	result = {
		"valid": False,
		"elem_type": None,
		"elem_type_name": None,
		"shape": None,
		"error": None,
	}

	model_path = input

	try:
		model = onnx.load(model_path)

		if loose == 0 :
			from onnx.checker import ValidationError
			try:
				onnx.checker.check_model(model)
			except ValidationError as e:
				result["error"] = f"模型无效，错误信息: {e}"
				return result

		input_info = model.graph.input[0]
		tensor_type = input_info.type.tensor_type

		## 10➡️FP16 或 1➡️FP32
		elem_type = tensor_type.elem_type
		result["elem_type"] = elem_type

		if elem_type == TensorProto.FLOAT :
			result["elem_type_name"] = "fp32"
		elif elem_type == TensorProto.FLOAT16 :
			result["elem_type_name"] = "fp16"
		else :
			result["error"] = f"不支持的数据类型: {elem_type}，仅支持 fp16(10) 或 fp32(1)"
			return result

		shape = []
		for dim in tensor_type.shape.dim :
			if dim.dim_param :
				shape.append(-1)
			else :
				shape.append(dim.dim_value if dim.dim_value > 0 else -1)
		result["shape"] = shape

		## NCHW
		if len(shape) != 4 :
			result["error"] = f"输入维度数量错误: 期望 4 维 (NCHW)，实际 {len(shape)} 维"
			return result

		if shape[1] not in [1, 3] :
			result["error"] = f"输入通道数错误: 期望 1 或 3 通道，实际 {shape[1]} 通道"
			return result

		if loose in [0, 1] :
			if shape[0] not in [-1, 1] or shape[2] != -1 or shape[3] != -1 :
				expected_shape = f"[-1/1, {shape[1]}, -1, -1]"
				result["error"] = f"输入维度格式错误: 期望 {expected_shape}，实际 {shape}"
				return result

		result["valid"] = True

	except Exception as e:
		result["error"] = f"解析模型失败: {e}"

	return result

##################################################
## 像素值限制
##################################################

def PIX_CLP(
	input : vs.VideoNode,
) -> vs.VideoNode :

	func_name = "PIX_CLP"
	_check_plugin(func_name, "akarin")

	output = core.akarin.Expr(clips=input, expr="x 0 1 clamp")

	return output

##################################################
## 场景检测
##################################################

def PROP_HISTDIFF(
	input : vs.VideoNode,
	sample_step : typing.Literal[1, 2] = 1,
) -> vs.VideoNode :
	"""
	为每帧添加直方图差异属性
	"""

	import numpy as np

	clip = input
	if sample_step not in (1, 2) :
		raise ValueError("PROP_HISTDIFF: sample_step must be one of (1, 2)")
	if clip.format.color_family != vs.GRAY :
		clip = clip.std.ShufflePlanes(planes=0, colorfamily=vs.GRAY)
	if clip.format.bits_per_sample != 8 or clip.format.sample_type != vs.INTEGER :
		clip = clip.resize.Point(format=vs.GRAY8)

	clip_next = clip.std.Trim(first=1) + clip.std.Trim(first=clip.num_frames - 1)

	def _calc_hist_diff(n, f) :
		fout = f[0].copy()
		curr_data = np.asarray(f[0][0])
		next_data = np.asarray(f[1][0])

		if sample_step > 1 :
			curr_flat = curr_data[::sample_step, ::sample_step].ravel()
			next_flat = next_data[::sample_step, ::sample_step].ravel()
		else :
			curr_flat = curr_data.ravel()
			next_flat = next_data.ravel()

		hist1 = np.bincount(curr_flat, minlength=256)
		hist2 = np.bincount(next_flat, minlength=256)
		norm = float(curr_flat.size) * 2.0
		diff = float(np.abs(hist1 - hist2).sum()) / norm if norm else 0.0

		fout.props['SCPlaneStatsDiff'] = float(diff)
		return fout

	return clip.std.ModifyFrame(clips=[clip, clip_next], selector=_calc_hist_diff)

def SCDetect2(
	input : vs.VideoNode,
	algo : int = 1,
	threshold : float = 0.1,
	max_size : int = 2304000,
	hist_sstep : int = 1,
	) -> vs.VideoNode :
	"""
	场景切换检测++

	参数:
		algo : 检测算法
			1 MAE （默认，速度最快） 2 边缘MAE （对亮度变化不敏感）
			3 直方图 （对整体亮度变化不敏感） 4 直方图&边缘MAE
		threshold : 场景切换阈值 (0.0-1.0) 。建议值范围：
			algo=1: 0.10 ... 0.15
			algo=2: 0.05 ... 0.10
			algo=3: 0.20 ... 0.40
			algo=4: 0.10 ... 0.15
		max_size : 最大帧面积阈值，默认 2304000 （不建议低于 518400 ），超过则预降采样， 0 则禁用
		hist_sstep : 直方图采样步长，默认 1 （全采样）
	"""

	if threshold < 0.0 or threshold > 1.0 :
		raise ValueError("SCDetect2: threshold must be between 0 and 1")
	if input.num_frames == 1 :
		raise ValueError("SCDetect2: input must have more than one frame")
	if algo not in (1, 2, 3, 4) :
		raise ValueError("SCDetect2: unsupported algo value")
	if hist_sstep not in (1, 2) :
		raise ValueError("SCDetect2: hist_sstep must be one of (1, 2)")

	clip = input
	clip_orig = clip

	if clip.format.color_family == vs.RGB :
		clip = clip.resize.Point(format=vs.GRAY8 if clip.format.bits_per_sample == 8 else vs.GRAY16,
								 matrix_s="709")

	if max_size > 0 :
		size = clip.width * clip.height
		if size > max_size :
			scale_factor = (max_size / size) ** 0.5
			width_n = int(clip.width * scale_factor)
			height_n = int(clip.height * scale_factor)
			width_n = width_n - (width_n % 2)
			height_n = height_n - (height_n % 2)
			clip = clip.resize.Bilinear(width_n, height_n)

	if algo == 1 :
		trimmed = clip.std.Trim(first=1)
		compared = clip.std.PlaneStats(trimmed, prop="SCPlaneStats", plane=0)

	elif algo == 2 :
		clip = clip.std.Sobel()
		trimmed = clip.std.Trim(first=1)
		compared = clip.std.PlaneStats(trimmed, prop="SCPlaneStats", plane=0)

	elif algo == 3 :
		compared = PROP_HISTDIFF(clip, sample_step=hist_sstep)

	elif algo == 4 :
		hist_compared = PROP_HISTDIFF(clip, sample_step=hist_sstep)
		edge_clip = clip.std.Sobel()
		trimmed = edge_clip.std.Trim(first=1)
		edge_compared = edge_clip.std.PlaneStats(trimmed, prop="SCPlaneStats", plane=0)
		hist_compared_prev = hist_compared.std.DuplicateFrames([0])[:-1]
		edge_compared_prev = edge_compared.std.DuplicateFrames([0])[:-1]

		def _set_scene_change_combined(n, f) :
			fout = f[0].copy()
			# f[1], f[2]: hist_compared 的前一帧和当前帧
			# f[3], f[4]: edge_compared 的前一帧和当前帧
			hist_prev = f[1].props.get('SCPlaneStatsDiff', 0.0)
			hist_next = f[2].props.get('SCPlaneStatsDiff', 0.0)
			edge_prev = f[3].props.get('SCPlaneStatsDiff', 0.0)
			edge_next = f[4].props.get('SCPlaneStatsDiff', 0.0)
			fout.props['_SceneChangePrev'] = int((hist_prev > threshold) and (edge_prev > threshold))
			fout.props['_SceneChangeNext'] = int((hist_next > threshold) and (edge_next > threshold))
			return fout

		return clip_orig.std.ModifyFrame(
			clips=[clip_orig, hist_compared_prev, hist_compared, edge_compared_prev, edge_compared],
			selector=_set_scene_change_combined
		)

	# algo 1/2/3 共用阈值判定与属性写入逻辑
	compared_prev = compared.std.DuplicateFrames([0])[:-1]

	def _set_scene_change(n, f) :
		fout = f[0].copy()
		prev_diff = f[1].props.get('SCPlaneStatsDiff', 0.0)
		next_diff = f[2].props.get('SCPlaneStatsDiff', 0.0)
		fout.props['_SceneChangePrev'] = int(prev_diff > threshold)
		fout.props['_SceneChangeNext'] = int(next_diff > threshold)
		return fout

	return clip_orig.std.ModifyFrame(clips=[clip_orig, compared_prev, compared],
									 selector=_set_scene_change)

def SCENE_DETECT(
	input : vs.VideoNode,
	sc_mode : typing.Literal[0, 1, 2] = 1,
	thr : float = 0.15,
	thd1 : int = 240,
	thd2 : int = 130,
) -> vs.VideoNode :

	if sc_mode == 0 :
		output = input
	elif sc_mode == 1 :
		output = SCDetect2(input, threshold=thr)
	elif sc_mode == 2 :
		sup = core.mv.Super(clip=input, pel=1)
		vec = core.mv.Analyse(super=sup, isb=True)
		output = core.mv.SCDetection(clip=input, vectors=vec, thscd1=thd1, thscd2=thd2)

	return output
