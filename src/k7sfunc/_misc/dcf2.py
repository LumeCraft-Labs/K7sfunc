"""color fix

"""

import vapoursynth as vs
from vapoursynth import core

__all__ = [
	"DCF2"
]

def _box_blur(clip, planes, hradius, hpasses, vradius, vpasses):
	return core.vszip.BoxBlur(clip, planes=planes, hradius=hradius, hpasses=hpasses, vradius=vradius, vpasses=vpasses)

def _temporal_median(clip, radius, planes):
	return core.zsmooth.TemporalMedian(clip, radius=radius, planes=planes)

def _expr(clips, expr):
	return core.akarin.Expr(clips, expr)

def DCF2(
	input : vs.VideoNode,
	ref : vs.VideoNode = None,
	sdf : bool = True,
	tdf : bool = True,
	sdf_br : int = 10,
	sdf_bp : int = 5,
	tdf_str : float = 1.0,
	tdf_rad : int = 1,
	tdf_br : int = 24,
	tdf_bp : int = 3,
	fast : bool = True,
) -> vs.VideoNode :
	"""
	针对单图超分的快速色彩一致性修复。

	参数：
	  input             超分辨率输出
	  ref               超分前的参考clip。sdf=True 时必填。
	  sdf               启用 DCF 空域色彩校正
	  tdf               启用低频时域稳定
	  tdf_str           <0.0~1.0> 时域稳定化强度
	  sdf_br            DCF 空域色彩校正的 BoxBlur 半径
	  sdf_bp            DCF 空域色彩校正的 BoxBlur 遍数
	  tdf_rad           TemporalMedian 半径。1=3帧，2=5帧
	  tdf_br            频率分离的 BoxBlur 半径。较大值稳定更多频段， 但在快速运动时可能导致模糊。
	  tdf_bp            频率分离的 BoxBlur 遍数
	  fast              True：空域色彩校正时将 input 缩小到 ref 尺寸后模糊再放大，时域处理分辨率优先使用 ref 尺寸，无 ref 时按 2x 下采样。
	                    False：空域色彩校正时将 ref 放大到 input 尺寸处理，时域处理在全分辨率进行。
	"""

	clip = input
	fmt_in = clip.format.id
	w_in, h_in = clip.width, clip.height
	w_ref = h_ref = None
	if fmt_in != vs.RGBS :
		clip = core.resize.Point(clip=clip, format=vs.RGBS)
	clip_orig = clip
	planes = [0, 1, 2]

	# --- DCF 空域色彩校正 ---
	if sdf :
		if ref is None :
			raise ValueError("DCF2: 启用 sdf 时必须提供 ref 输入")
		fmt_ref = ref.format.id
		if fmt_ref != vs.RGBS :
			ref = core.resize.Point(clip=ref, format=vs.RGBS)
		w_ref, h_ref = ref.width, ref.height
		need_resize = w_ref != w_in or h_ref != h_in

		if need_resize :
			if fast :
				clip = core.resize.Bilinear(clip=clip, width=w_ref, height=h_ref)
			else :
				ref = core.resize.Bilinear(clip=ref, width=w_in, height=h_in)

		blur_in  = _box_blur(clip, planes, sdf_br, sdf_bp, sdf_br, sdf_bp)
		blur_ref = _box_blur(ref,  planes, sdf_br, sdf_bp, sdf_br, sdf_bp)
		color_diff = core.std.MakeDiff(clipa=blur_ref, clipb=blur_in, planes=planes)

		if fast and need_resize :
			color_diff = core.resize.Bilinear(clip=color_diff, width=w_in, height=h_in)

		clip = core.std.MergeDiff(clipa=clip_orig if fast else clip, clipb=color_diff, planes=planes)

	# --- 低频时域稳定化 ---
	if tdf and tdf_str > 0 and tdf_rad > 0 :
		# 时域下采样目标分辨率优先级：ref 尺寸 > fast 2x下采样 > 全分辨率
		if w_ref is not None :
			sw, sh = w_ref, h_ref
		elif fast :
			sw = w_in // 2
			sh = h_in // 2
		else :
			sw, sh = w_in, h_in
		small = core.resize.Bilinear(clip, width=sw, height=sh)

		adj_radius = max(tdf_br * sw // w_in, 1)
		small_low = _box_blur(small, planes, adj_radius, tdf_bp, adj_radius, tdf_bp)

		small_low_stable = _temporal_median(small_low, tdf_rad, planes)
		correction = core.std.MakeDiff(clipa=small_low_stable, clipb=small_low, planes=planes)
		correction = core.resize.Bilinear(correction, width=w_in, height=h_in)

		if tdf_str == 1.0 :
			clip = core.std.MergeDiff(clipa=clip, clipb=correction, planes=planes)
		else :
			clip = _expr([clip, correction],
				["x y {s} * +".format(s=tdf_str)] * 3)

	return clip
