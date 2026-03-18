
**当前文档对应的版本 dev **  
_与 mpv-lazy 预捆绑的版本说明发布在[此处](https://github.com/hooke007/mpv_PlayKit/wiki/3_K7sfunc)_

# K7SFUNC

为mpv特向优化的vs包装器

- 主要特点

模块化各vs滤镜 ——  
简化脚本内调用的方式，降低仓库内已公开的vapoursynth滤镜的使用门槛；  
便于在单个vpy脚本中快速合并多个效果，减少串联多个vf产生的多余性能损失。

- 可用模块

大致分为六个组：“格式控制” “超分”(SR) “运动补偿”(MEMC) “去块降噪”(DBLK&NR) “其它”(ETC) “混合”(MIX)。  
每组可用的具体模块说明跳转后方的 👉 [**详细介绍**](https://github.com/hooke007/mpv_PlayKit/wiki/3_K7sfunc#2-%E6%A8%A1%E5%9D%97%E8%AF%B4%E6%98%8E)。

## 1. 使用引导

(1) 安装前置环境 Python + VapourSynth ，<s>此步骤的教程可参考 [mpv通用教程(#vapoursynth)](https://hooke007.github.io/unofficial/mpv_start.html#vapoursynth) / [mpv通用教程补充](https://github.com/hooke007/mpv_PlayKit/discussions/66) / [从零部署](https://gist.github.com/hooke007/e502688c60ef1c5f9ef507cf4db25b34)</s>  
从此处下载快速部署包后解压至mpv.exe的路径 https://github.com/hooke007/dotfiles/releases/tag/mpv_addones  
_（使用 mpv-lazy 可跳过此步）_

(2) 切换到部署包解压后的目录运行终端PowerShell命令 `./python -m pip install -U k7sfunc`  
执行完此步骤即视为“安装完毕”。  
_（使用 mpv-lazy 可跳过此步）_

(3) 依据自己要使用的模块下载对应的依赖，此步骤的教程可参考步骤1  
_（使用 mpv-lazy 则可直接下载release页面的 vsAMD/vsNV 包）_

(4) 根据此包装器编写自己的滤镜组合脚本，然后通过mpv的 [`vf=vapoursynth="X/path/to/test.vpy"`](https://mpv.io/manual/master/#video-filters-vapoursynth) 启用它  
（优先推荐使用快捷键开关 `vf toggle vapoursynth="X/path/to/test.vpy"` ）。  

### 1.1. 创建自定义vpy脚本

简单认识vpy脚本的结构，它大致分为三个部分：（首）导入模块 → （主体）对待处理的对象执行各种操作 → （尾）输出结果  

示例如下 ——
```python
## 开头部分
import vapoursynth as vs                                                   # 行1
from vapoursynth import core                                               # 行2
from k7sfunc import *                                                      # 行3
## 主体部分
step01 = video_in                                                          # 行4
step02 = FMT_CTRL(input=step01, fmt_pix=1)                                 # 行5
step03 = MVT_LQ(input=step02, fps_in=container_fps, fps_out=display_fps)   # 行6
## 结尾部分
step03.set_output()                                                        # 行7
```

- 第1、2行： 几乎所有vpy脚本的开头固定内容（如果你只使用K7sfunc模块内的功能，这甚至可以不写）。  
- 第3行： 导入K7sfunc的所有模块，如果你只想导入指定的模块，则此处改写为（示例）：
  ```python
  from k7sfunc import FMT_CTRL, MVT_LQ
  ```
- 第4行： 将 `video_in` （这是由mpv提供的）即视频，赋值给自己定义的变量 `step01` ;
- 第5行： 使用模块 `FMT_CTRL` （这是由K7sfunc导入的），处理 `step01` ，转换为常规的8位视频，并将结果赋值给 `step02` ;
- 第6行： 使用另一个模块 `MVT_LQ` （这也是由K7sfunc导入的），处理 `step02` ， `container_fps` `display_fps` （也都是由mpv提供的）分别表示源帧率和显示刷新率，即补帧到显示器的等值帧率，并将结果赋值给 `step03` ;
- 第7行： 即输出 `step03` ，如果无误，即正常输出补帧后的视频。输出内容也通常是vpy脚本的最后固定内容

>[!TIP]
>使用完整写法的参数可以改变顺序，即：
>```
>step03 = MVT_LQ(step02, fps_out=display_fps, fps_in=container_fps)
>```

>[!TIP]
>在向模块内传递参数的时候，可以省略为（第6行的示例）：
>```
>step03 = MVT_LQ(step02, container_fps, display_fps)
>```
>>(重要)：简略的前提是顺序要和模块内一一对应，也可以简略和完整混合，即：
>>```
>>step03 = MVT_LQ(step02, fps_in=container_fps, fps_out=display_fps)
>>```

>[!IMPORTANT]
>从减少命名冲突的角度出发，使用另一种“安全方法”导入更好（第3行的示例），不过会影响后续的写法：
>```
>import k7sfunc as k7f
>```
>>👉 如果你使用了“安全方法”进行导入，模块名在使用的时候要修改（第6行的示例）：
>>```
>>step03 = k7f.MVT_LQ(input=step02, fps_in=container_fps, fps_out=display_fps)
>>```

>[!TIP]
>为了进一步方便，会使用同名变量不断更新赋值，即：
>```
>import vapoursynth as vs
>from vapoursynth import core
>from k7sfunc import *
>clip = video_in
>clip = FMT_CTRL(clip, fmt_pix=1)
>clip = MVT_LQ(clip, fps_in=container_fps, fps_out=display_fps)
>clip.set_output()
>```

扩展阅读 [《vpy的设计与优化思路》](https://github.com/hooke007/mpv_PlayKit/discussions/313)

更多示例（如果你不具备相关知识或不熟悉上文，则不建议）参考 [仓库内的vpy脚本](https://github.com/hooke007/mpv_PlayKit/tree/main/portable_config/vs)  

# 2. 模块说明

- _带 `_NV` 后缀的模块为nvidia RTX显卡专用。_

- 各模块的头部代码块表示的是该模块内各个参数的默认值。表格内第二列为各个参数的可用值。

- **各模块的参数 `input` 都是必填项**，它的值是由你定义的待处理的片段，其它见各自的介绍。示例即默认值。

对大部分模块来说，使用它们的前提是都需要下载模块对应的依赖脚本/插件/其它组件。（注意依赖链接的说明里可能会进一步要求你安装更多前置/附属依赖）



## 格式控制

***

### FMT_CHANGE

```python
FMT_CHANGE(input=?, fmtc=False, algo=1, param_a=0.0, param_b=0.0, w_out=0, h_out=0, fmt_pix=-1, dither=0)
```

格式转换

||||
|:---|:---|:---|
| <kbd>fmtc</kbd> | `True`\|`False` ||
| <kbd>algo</kbd> | `1`\|`2`\|`3`\|`4` | 缩放算法，分别对应： bilinear bicubic lanczos spline36 |
| <kbd>param_a</kbd> | 浮点 | 仅当 <kbd>algo</kbd> 为 `2` 或 `3` 时有效 |
| <kbd>param_b</kbd> | 浮点 | 仅当 <kbd>algo</kbd> 为 `2` 时有效 |
| <kbd>w_out</kbd> | 整数 | 输出宽度 |
| <kbd>h_out</kbd> | 整数 | 输出高度 |
| <kbd>fmt_pix</kbd> | `-1`\|`0`\|`1`\|`2`\|`3` | 像素格式，分别对应： 同源 自动 yuv420p8 yuv420p10 yuv444p16 |
| <kbd>dither</kbd> | `0`\|`1`\|`2`\|`3` | 色深抖动算法，分别对应： none ordered random error_diffusion |

***

### FMT_CTRL

```python
FMT_CTRL(input=?, h_max=0, h_ret=False, spl_b=1/3, spl_c=1/3, fmt_pix=0)
```

用于检测或限制尺寸、像素格式。

||||
|:---|:---|:---|
| <kbd>h_max</kbd> | 整数 | 表示检测的最大高度限制 |
| <kbd>h_ret</kbd> | `True`\|`False` | 当为 `True` 时，中断后续执行。否则转换输入源到 `h_max` 指定的高度 |
| <kbd>spl_b</kbd> | 浮点 | 转换时所用的算法为bcspline，此项和下一项分别对应B、C的值 |
| <kbd>spl_c</kbd> | 浮点 ||
| <kbd>fmt_pix</kbd> | `0`\|`1`\|`2`\|`3` | 像素格式， `0` 表示自动，其它几个值分别对应 yuv420p8 yuv420p10 yuv444p16 |

P.S. 简易的使用 `FMT_CTRL(input=?)` 来限制或转换输入源在YUV10位内

***

### FPS_CHANGE

```python
FPS_CHANGE(input=?, fps_in=24.0, fps_out=60.0)
```

用于转换帧率（不支持VFR）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_out</kbd> | 浮点 | 指定输出的帧率 |

***

### FPS_CTRL

```python
FPS_CTRL(input=?, fps_in=23.976, fps_max=32.0, fps_out=None, fps_ret=False)
```

用于检测或限制帧率。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_max</kbd> | 浮点 | 指定检测的最大帧率 |
| <kbd>fps_out</kbd> | （可选）浮点 | 指定输出的帧率 |
| <kbd>fps_ret</kbd> | `True`\|`False` | 当为 `True` 时，中断后续执行。否则转换输入源到 <kbd>fps_out</kbd> 指定的帧率，如果 <kbd>fps_out</kbd> 未填写则使用 <kbd>fps_max</kbd> 的值 |

***

## 超分

***

### ACNET_STD

> 所需依赖：[Anime4KCPP v3](https://vsdb.top/plugins/anime4kcpp)

```python
ACNET_STD(input=?, model=1, model_var=0, turbo=False, gpu=0, gpu_m=1)
```

使用acnet算法固定放大两倍（只适合Anime风格）。  

||||
|:---|:---|:---|
| <kbd>model</kbd> | `1`\|`2`\|`3` | 使用的模型，分别对应 `acnet-gan` `acnet-hdn` `arnet-hdn` |
| <kbd>model_var</kbd> | `0`\| `1`\|`2`\|`3` | 模型的变体（仅对2号模型有效，表示为降噪强度），分别对应 `acnet-hdn0` `acnet-hdn1` `acnet-hdn2` `acnet-hdn3` |
| <kbd>turbo</kbd> | `True`\|`False` | 是否使用内部提速技巧 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_m</kbd> | `1`\|`2` | 选择其中一种显卡加速模式，分别对应 OpenCL Cuda |

***

### ARTCNN_NV

> 所需依赖：  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
ARTCNN_NV(input=?, lt_hd=False, model=8, gpu=0, gpu_t=2, st_eng=False, ws_size=0)
```

用 ArtCNN 固定放大2倍（只适合Anime风格）。

||||
|:---|:---|:---|
| <kbd>lt_hd</kbd> | `True`\|`False` | 是否对超过HD分辨率（720P）的源进行处理 |
| <kbd>model</kbd> | `6`\|`7`\|`8` | 使用的模型，详见下方解释 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>st_eng</kbd> | `True`\|`False` | 是否使用静态引擎（需要对不同分辨率的源各进行预处理）；动态引擎自适应不同分辨率（384²→DCI2K） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

在禁用 <kbd>lt_hd</kbd> 的情况下，使用动态引擎时的首选优化分辨率为1280x720，启用该选项后，优化分辨率则为1920x1080。  
模型代号中的 `6` 为ArtCNN_R16F96， `7` 为ArtCNN_R8F64， `8` 为ArtCNN_R8F64_DS  

***

### CUGAN_NV

> 所需依赖：  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
CUGAN_NV(input=?, lt_hd=False, nr_lv=-1, sharp_lv=1.0, gpu=0, gpu_t=2, st_eng=False, ws_size=0)
```

用 Real-CUGAN (pro) 固定放大两倍，附带降噪（只适合Anime风格）。

||||
|:---|:---|:---|
| <kbd>lt_hd</kbd> | `True`\|`False` | 是否对超过HD分辨率（720P）的源进行处理 |
| <kbd>nr_lv</kbd> | `-1`\|`0`\|`3` | 降噪强度， `-1` 为不降噪 |
| <kbd>sharp_lv</kbd> | 浮点 | 锐度，应介于 `0..0` 到 `2.0` |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>st_eng</kbd> | `True`\|`False` | 是否使用静态引擎（需要对不同分辨率的源各进行预处理）；动态引擎自适应不同分辨率（384²→DCI2K） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

在禁用 <kbd>lt_hd</kbd> 的情况下，使用动态引擎时的首选优化分辨率为1280x720，启用该选项后，优化分辨率则为1920x1080。  
如需制约或节约显存占用，应优先启用静态引擎，其次限制 <kbd>ws_size</kbd> 的值。

>[!NOTE]
>使用 vsNV 包的用户：此功能所需的模型文件不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.0_0_7.cugan-models.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/models/cugan/pro-conservative-up2x.onnx`

***

### EDI_US_STD

> 所需依赖：[fmtconv](https://vsdb.top/plugins/fmtc) + [NNEDI3CL](https://vsdb.top/plugins/nnedi3cl) + [znedi3](https://vsdb.top/plugins/znedi3)

```python
EDI_US_STD(input=?, ext_proc=True, nsize=4, nns=3, cpu=True, gpu=-1)
```

用nnedi3算法固定放大两倍。  
追求速度应使用着色器版本，例如 [nnedi3_nns128_win8x4.glsl](https://github.com/hooke007/mpv_PlayKit/blob/main/portable_config/shaders/nnedi3_nns128_win8x4.glsl)

||||
|:---|:---|:---|
| <kbd>ext_proc</kbd> | `True`\|`False` | 是否使用外部的（提速）格式转换处理 |
| <kbd>nsize</kbd> | `0`\|`4` | 分别对应 8x6 8x4 |
| <kbd>nns</kbd> | `2`\|`3`\|`4` | 分别对应 64 128 256 |
| <kbd>cpu</kbd> | `True`\|`False` | 分别对应使用cpu还是gpu |
| <kbd>gpu</kbd> | `-1`\|`0`\|`1`\|`2` | 指定显卡， `0` 为排序一号， `-1` 为自动 |

***

### NGU_HQ

> 所需依赖：[DualSynth-madVR](https://github.com/Jaded-Encoding-Thaumaturgy/DualSynth-madVR) + [madVR(beta/test)](https://www.videohelp.com/software/madVR)

```python
NGU_HQ(input=?)
```

使用madVR的NGU-AA(high)算法放大两倍（实验性）

仅供测试，当前既无法指定显卡，性能的利用率也非常低（比在mpc在使用的性能要求可能要翻倍）。

>[!NOTE]
>使用 vsAMD/vsNV 包的用户：此功能所需的madVR组件不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.0_4_3.mad.b204.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/madVR/madVR64.ax`

***

## 运动补偿

***

### MVT_LQ

> 所需依赖：[MVTools](https://vsdb.top/plugins/mv)

```python
MVT_LQ(input=?, fps_in=23.976, fps_out=59.940, recal=True, block=True)
```

补帧至任意帧率（不支持VFR）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_out</kbd> | 浮点 | 指定输出帧率 |
| <kbd>recal</kbd> | `True`\|`False` | 是否使用二次分析 |
| <kbd>block</kbd> | `True`\|`False` | 是否使用Block（速度快）模式 |

***

### MVT_MQ

> 所需依赖：[MVTools](https://vsdb.top/plugins/mv)

```python
MVT_MQ(input=?, fps_in=23.976, fps_out=59.940, qty_lv=1, block=True, blksize=8, thscd1=360, thscd2=80)
```

用mvtools的block或flow模式补帧至任意帧率（不支持VFR；修改自xvs）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_out</kbd> | 浮点 | 指定输出帧率 |
| <kbd>qty_lv</kbd> | `1`\|`2`\|`3` | 质量等级 |
| <kbd>block</kbd> | `True`\|`False` | 是否使用Block（速度快）模式 |
| <kbd>blksize</kbd> | `4`\|`8`\|`16`\|`32` | 块尺寸 |
| <kbd>thscd1</kbd> | 整数 | 块阈值1 |
| <kbd>thscd2</kbd> | `0~255` 整数 | 块阈值2 |

***

### DRBA_DML

```python
DRBA_DML(input=?, model=2, turbo=1, fps_in=23.976, fps_num=2, fps_den=1, sc_mode=0, gpu=0, gpu_t=2)
```

用 DRBA 补帧至固定数倍。

||||
|:---|:---|:---|
| <kbd>model</kbd> | `1`\|`2` | 使用的模型，分别对应 v1 v2_lite |
| <kbd>turbo</kbd> | `0`\|`1`\|`2` | 使用内部提速技巧的等级， `0` 为禁用 |
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | 整数 | <kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的值即帧率倍数（计算结果可为浮点） |
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>sc_mode</kbd> | `0`\|`1`\|`2` | 场景切换检测的模式， `0` 为禁用 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |

性能需求 —— 模型v1 > v2_lite

***

### DRBA_NV

```python
DRBA_NV(input=?, model=2, int8_qnt=False, turbo=1, fps_in=23.976, fps_num=2, fps_den=1, sc_mode=0, gpu=0, gpu_t=2, ws_size=0)
```

用 DRBA 补帧至固定数倍。

||||
|:---|:---|:---|
| <kbd>model</kbd> | `1`\|`2` | 使用的模型，分别对应 v1 v2_lite |
| <kbd>int8_qnt</kbd> | `True`\|`False` | 是否混合int8量化加速（速度提升的有限，同时质量退化严重） |
| <kbd>turbo</kbd> | `0`\|`1`\|`2` | 使用内部提速技巧的等级， `0` 为禁用 |
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | 整数 | <kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的值即帧率倍数（计算结果可为浮点） |
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>sc_mode</kbd> | `0`\|`1`\|`2` | 场景切换检测的模式， `0` 为禁用 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

性能需求 —— 模型v1 > v2_lite

***

### RIFE_STD

>[!CAUTION]
>对Windows用户已过时，换用 [RIFE_DML](https://github.com/hooke007/mpv_PlayKit/wiki/3_K7sfunc#rife_dml)

<details>

> 所需依赖：[MVTools](https://vsdb.top/plugins/mv) + [RIFE(fork)](https://github.com/styler00dollar/VapourSynth-RIFE-ncnn-Vulkan) + [VMAF](https://vsdb.top/plugins/vmaf)

```python
RIFE_STD(input=?, model=21, turbo=2, fps_num=2, fps_den=1, sc_mode=1, stat_th=60.0, gpu=0, gpu_t=2)
```

用 rife v4+ 补帧至任意倍率。

||||
|:---|:---|:---|
| <kbd>model</kbd> | `23`\|`70`\|`72`\|`73` | 使用的模型，分别对应4.6 4.25lite 4.26 4.26heavy |
| <kbd>turbo</kbd> | `0`\|`1`\|`2` | 使用内部提速技巧的等级， `0` 为禁用 |
| <kbd>fps_num</kbd> | 整数 | <kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的值即帧率倍数（计算结果可为浮点） |
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>sc_mode</kbd> | `0`\|`1`\|`2` | 场景切换检测的模式， `0` 为禁用 |
| <kbd>stat_th</kbd> | 浮点 | 静止帧的检测阈值（最大 `60.0` ），跳过相似帧（需要 `turbo` 为 `2` ） |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |

性能需求 —— 模型4.26heavy > 4.26 > 2.25lite > 4.6

>[!NOTE]  
>使用 vsNV 包的用户：此功能所需的核心组件及所有模型均不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.x_x_x.rife_std-core_models.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/librife_windows_x86-64.dll`

</details>

***

### RIFE_DML

> 所需依赖：  
> pip3: `onnx`  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [MVTools](https://vsdb.top/plugins/mv) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
RIFE_DML(input=?, model=46, turbo=True, fps_in=23.976, fps_num=2, fps_den=1, sc_mode=1, gpu=0, gpu_t=2)
```

用 rife v4+ 补帧至固定数倍。

||||
|:---|:---|:---|
| <kbd>model</kbd> | `46`\|`4251`\|`426`\|`4262` | 使用的模型，分别对应 4.6 4.25lite 4.26 4.26heavy |
| <kbd>turbo</kbd> | `True`\|`False` | 是否使用内部提速技巧 |
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | 整数 | <kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的值即帧率倍数（计算结果可为浮点，但此时不适用VFR，因为会产生音画偏移） |
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>sc_mode</kbd> | `0`\|`1`\|`2` | 场景切换检测的模式， `0` 为禁用 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |

性能需求 —— 模型4.26heavy > 4.26 > 2.25lite > 4.6

***

### RIFE_NV

> 所需依赖：  
> pip3: `onnx`  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [MVTools](https://vsdb.top/plugins/mv) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
RIFE_NV(input=?, model=46, int8_qnt=False, turbo=2, fps_in=23.976, fps_num=2, fps_den=1, sc_mode=1, gpu=0, gpu_t=2, ws_size=0)
```

用 rife v4+ 补帧至固定数倍。

||||
|:---|:---|:---|
| <kbd>model</kbd> | `46`\|`4251`\|`426`\|`4262` | 使用的模型，分别对应 4.6 4.25lite 4.26 4.26heavy |
| <kbd>int8_qnt</kbd> | `True`\|`False` | 是否混合int8量化加速（速度提升的有限，同时质量退化严重） |
| <kbd>turbo</kbd> | `0`\|`1`\|`2` | 使用内部提速技巧的等级， `0` 为禁用 |
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | 整数 | <kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的值即帧率倍数（计算结果可为浮点，但此时不适用VFR，因为会产生音画偏移） |
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>sc_mode</kbd> | `0`\|`1`\|`2` | 场景切换检测的模式， `0` 为禁用 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

性能需求 —— 模型4.26heavy > 4.26 > 2.25lite > 4.6

***

### SVP_LQ

> 所需依赖：[SVPflow1](https://github.com/hooke007/mpv_PlayKit/discussions/114) + [SVPflow2](https://github.com/hooke007/mpv_PlayKit/discussions/114)

```python
SVP_LQ(input=?, fps_in=23.976, fps_num=2, cpu=0, gpu=0)
```

用svpflow算法（修改自mvtools的flow模式）补帧至固定整数倍。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | `2`\|`3`\|`4` | 补帧倍率 |
| <kbd>cpu</kbd> | `0`\|`1` | 是否只使用CPU， `0` 为启用显卡加速 |
| <kbd>gpu</kbd> | `0`\|`11`\|`12`\|`21` | 指定显卡， `0` 为排序一号 |

>[!NOTE]
>使用 vsAMD/vsNV 包的用户：此功能所需的SVP组件不被附带在包中

***

### SVP_HQ

> 所需依赖：[SVPflow1](https://github.com/hooke007/mpv_PlayKit/discussions/114) + [SVPflow2](https://github.com/hooke007/mpv_PlayKit/discussions/114)

```python
SVP_HQ(input=?, fps_in=23.976, fps_dp=59.940, cpu=0, gpu=0)
```

用svpflow算法（修改自mvtools的flow模式）补帧至60（不支持VFR；移植自 [natural-harmonia-gropius](https://github.com/natural-harmonia-gropius) 的旧脚本）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_dp</kbd> | 浮点 | 指定显示器刷新率 |
| <kbd>cpu</kbd> | `0`\|`1` | 是否只使用CPU， `0` 为启用显卡加速 |
| <kbd>gpu</kbd> | `0`\|`11`\|`12`\|`21` | 指定显卡， `0` 为排序一号 |

>[!NOTE]
>使用 vsAMD/vsNV 包的用户：此功能所需的SVP组件不被附带在包中

***

### SVP_PRO

> 所需依赖：[SVPflow1](https://github.com/hooke007/mpv_PlayKit/discussions/114) + [SVPflow2](https://github.com/hooke007/mpv_PlayKit/discussions/114)

```python
SVP_PRO(input=?, fps_in=23.976, fps_num=2, fps_den=1, abs=False, cpu=0, nvof=False, gpu=0)
```

用svpflow算法（修改自mvtools的flow模式）补帧（修改自 [BlackMickey](https://github.com/BlackMickey) 的方案）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>fps_num</kbd> | 整数 ||
| <kbd>fps_den</kbd> | 整数 ||
| <kbd>abs</kbd> | `True`\|`False` | 当为 `True` 时，<kbd>fps_num</kbd>/<kbd>fps_den</kbd> 的计算结果为输出的帧率；否则为输出的倍率 |
| <kbd>cpu</kbd> | `0`\|`1` | 是否只使用CPU， `0` 为使用显卡加速 |
| <kbd>nvof</kbd> | `True`\|`False` | 是否使用Nvdia Optical Flow（启用时需要使用显卡加速） |
| <kbd>gpu</kbd> | `0`\|`11`\|`12`\|`21` | 指定显卡， `0` 为排序一号 |

>[!NOTE]
>使用 vsAMD/vsNV 包的用户：此功能所需的SVP组件不被附带在包中

***

## 去块降噪

***

### DPIR_DBLK_NV

> 所需依赖：  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
DPIR_DBLK_NV(input=?, lt_hd=False, model=2, nr_lv=50.0, gpu=0, gpu_t=2, st_eng=False, ws_size=0)
```

用 DPIR2021 算法去块。

||||
|:---|:---|:---|
| <kbd>lt_hd</kbd> | `True`\|`False` | 是否对超过HD分辨率（720P）的源进行处理 |
| <kbd>model</kbd> | `2`\|`3` | 使用的模型，分别对应 drunet_deblocking_grayscale drunet_deblocking_color |
| <kbd>nr_lv</kbd> | 浮点 | 去块强度 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>st_eng</kbd> | `True`\|`False` | 是否使用静态引擎（需要对不同分辨率的源各进行预处理）；动态引擎自适应不同分辨率（384²→DCI2K） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

在禁用 <kbd>lt_hd</kbd> 的情况下，使用动态引擎时的首选优化分辨率为1280x720，启用该选项后，优化分辨率则为1920x1080。  
如需制约或节约显存占用，应优先启用静态引擎，其次限制 <kbd>ws_size</kbd> 的值。

>[!NOTE]
>使用 vsNV 包的用户：此功能所需的所有模型均不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.0_2_0.dpir-models.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/models/dpir/drunet_deblocking_color.onnx`

***

### BILA_NV

> 所需依赖：[BilateralGPU_RTC](https://vsdb.top/plugins/bilateralgpu_rtc)

```python
BILA_NV(input=?, nr_spat=[3.0, 0.0, 0.0], nr_csp=[0.02, 0.0, 0.0], gpu=0, gpu_t=4)
```

用双边滤波算法降噪。

||||
|:---|:---|:---|
| <kbd>nr_spat</kbd> | 浮点数组 | 每平面的降噪强度 |
| <kbd>nr_csp</kbd> | 浮点数组 | 每平面的模糊强度 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过CPU线程数） |

***

### BM3D_NV

> 所需依赖：[BM3DCUDA_RTC](https://vsdb.top/plugins/bm3dcuda_rtc)

```python
BM3D_NV(input=?, nr_lv=[5,0,0], bs_ref=8, bs_out=7, gpu=0)
```

用bm3d算法降噪。

||||
|:---|:---|:---|
| <kbd>nr_lv</kbd> | 整数组 | 每平面的降噪强度 |
| <kbd>bs_ref</kbd> | `1`\|`2`\|`3`\|`4`\|`5`\|`6`\|`7`\|`8` | 参考帧的block_step |
| <kbd>bs_out</kbd> | `1`\|`2`\|`3`\|`4`\|`5`\|`6`\|`7`\|`8` | 处理帧的block_step，应小于 <kbd>bs_ref</kbd> 的值 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |

***

### CCD_STD

> 所需依赖：[akarin](https://vsdb.top/plugins/akarin)

```python
CCD_STD(input=?, nr_lv=20.0)
```

降低彩噪。

||||
|:---|:---|:---|
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |

***

### DFTT_STD

> 所需依赖：[dfttest2_CPU](https://github.com/AmusementClub/vs-dfttest2)

```python
DFTT_STD(input=?, plane=[0], nr_lv=8.0, size_sb=16, size_so=12, size_tb=3)
```

DFTTest算法降噪

||||
|:---|:---|:---|
| <kbd>plane</kbd> | 整数组 | 降噪处理的平面，全平面即 `[0, 1, 2]` |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>size_sb</kbd> | 整数 | 空域窗口长度 |
| <kbd>size_so</kbd> | 整数 | 空域重叠量 |
| <kbd>size_tb</kbd> | 整数 | 时域长度（帧数） |

***

### DFTT_NV

> 所需依赖：[dfttest2_GPURTC](https://github.com/AmusementClub/vs-dfttest2)

```python
DFTT_NV(input=?, plane=[0], nr_lv=8.0, size_sb=16, size_so=12, size_tb=3, gpu=0, gpu_t=4)
```

DFTTest算法降噪

||||
|:---|:---|:---|
| <kbd>plane</kbd> | 整数组 | 降噪处理的平面，全平面即 `[0, 1, 2]` |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>size_sb</kbd> | 整数 | 空域窗口长度 |
| <kbd>size_so</kbd> | 整数 | 空域重叠量 |
| <kbd>size_tb</kbd> | 整数 | 时域长度（帧数） |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过CPU线程数） |

***

### DPIR_NR_NV

> 所需依赖：  
> plugins: [akarin](https://vsdb.top/plugins/akarin) + [vsmlrt](https://github.com/AmusementClub/vs-mlrt)

```python
DPIR_NR_NV(input=?, lt_hd=False, model=0, nr_lv=5.0, gpu=0, gpu_t=2, st_eng=False, ws_size=0)
```

用 DPIR2021 算法降低（亮度或彩色）噪点。

||||
|:---|:---|:---|
| <kbd>lt_hd</kbd> | `True`\|`False` | 是否对超过HD分辨率（720P）的源进行处理 |
| <kbd>model</kbd> | `0`\|`1` | 使用的模型，分别对应 drunet_gray drunet_color |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>st_eng</kbd> | `True`\|`False` | 是否使用静态引擎（需要对不同分辨率的源各进行预处理）；动态引擎自适应不同分辨率（384²→DCI2K） |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

在禁用 <kbd>lt_hd</kbd> 的情况下，使用动态引擎时的首选优化分辨率为1280x720，启用该选项后，优化分辨率则为1920x1080。  
如需制约或节约显存占用，应优先启用静态引擎，其次限制 <kbd>ws_size</kbd> 的值。

>[!NOTE]
>使用 vsNV 包的用户：此功能所需的所有模型均不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.0_2_0.dpir-models.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/models/dpir/drunet_color.onnx`


***

### FFT3D_STD

> 所需依赖：[FFT3DFilter](https://vsdb.top/plugins/fft3dfilter) + [libfftw3f-3.dll](http://fftw.org/install/windows.html) + [Neo_FFT3D](https://vsdb.top/plugins/neo_fft3d)

```python
FFT3D_STD(input=?, mode=1, nr_lv=2.0, plane=[0], frame_bk=3, cpu_t=6)
```

用fft3d算法降噪。

||||
|:---|:---|:---|
| <kbd>mode</kbd> | `1`\|`2` | fft3d内核，分别对应 FFT3DFilter Neo-FFT3D |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>plane</kbd> | 整数组 | 降噪处理的平面，全平面即 `[0, 1, 2]` |
| <kbd>frame_bk</kbd> | `-1`\|`0`\|`1`\|`2`\|`3`\|`4`\|`5` | `-1` 为仅锐化和去光晕， `0` 为Temporal Kalman， `1` 为2D (spatial) Wiener， `2~5` 为N帧的3D Wiener |
| <kbd>cpu_t</kbd> | 整数 | 使用的处理器线程数 |

***

### NLM_STD

> 所需依赖：[KNLMeansCL](https://vsdb.top/plugins/knlm) + [zsmooth](https://github.com/adworacz/zsmooth) + [vs-nlm-ispc](https://github.com/AmusementClub/vs-nlm-ispc)

```python
NLM_STD(input=?, blur_m=2, nlm_m=1, frame_num=1, rad_sw=2, rad_snw=2, nr_lv=3.0, gpu=0)
```

用NL-means算法降噪。  
追求速度应使用着色器版本，例如 [nlmeans.glsl](https://github.com/hooke007/mpv_PlayKit/blob/main/portable_config/shaders/nlmeans.glsl)

||||
|:---|:---|:---|
| <kbd>blur_m</kbd> | `0`\|`1`\|`2` | 分离模式。 `0` 为不使用 |
| <kbd>nlm_m</kbd> | `1`\|`2` | 降噪核心，分别对应 OpenCL CPU |
| <kbd>frame_num</kbd> | 整数 | 降噪帧数 |
| <kbd>rad_sw</kbd> | 整数 | 搜索窗口半径 |
| <kbd>rad_snw</kbd> | 整数 | 近邻窗口半径 |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |

***

### NLM_NV

> 所需依赖：[vs-nlm-cuda](https://github.com/AmusementClub/vs-nlm-cuda) + [zsmooth](https://github.com/adworacz/zsmooth)

```python
NLM_NV(input=?, blur_m=2, frame_num=1, rad_sw=2, rad_snw=2, nr_lv=3.0, gpu=0, gpu_t=4)
```

用NL-means算法降噪。  
追求速度应使用着色器版本，例如 [nlmeans.glsl](https://github.com/hooke007/mpv_PlayKit/blob/main/portable_config/shaders/nlmeans.glsl)

||||
|:---|:---|:---|
| <kbd>blur_m</kbd> | `0`\|`1`\|`2` | 分离模式。 `0` 为不使用 |
| <kbd>frame_num</kbd> | 整数 | 降噪帧数 |
| <kbd>rad_sw</kbd> | 整数 | 搜索窗口半径 |
| <kbd>rad_snw</kbd> | 整数 | 近邻窗口半径 |
| <kbd>nr_lv</kbd> | 浮点 | 降噪强度 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过CPU线程数） |

***

## 其它

***

### CSC_UV

```python
CSC_UV(input=?, cx=4, cy=4, sat_lv1=4.0, sat_lv2=0.8, blur=False)
```

UV色度偏移修正。

||||
|:---|:---|:---|
| <kbd>cx</kbd> | 整数 | 色度平面的水平移动，正值向左 |
| <kbd>cy</kbd> | 整数 | 色度平面的垂直移动，正值向左 |
| <kbd>sat_lv1</kbd> | 浮点 | mask阈值 |
| <kbd>sat_lv2</kbd> | 浮点 | 合并饱和度，小于 `1.0` 则降低饱和度 |
| <kbd>blur</kbd> | `True`\|`False` | 是否模糊mask |

***

### DEBAND_STD

> 所需依赖：[vszip](https://github.com/dnjulek/vapoursynth-zip)

```python
DEBAND_STD(input=?, bd_range=15, bdy_rth=48.0, grainy=48.0, spl_m=4, grain_dy=True)
```

用f3kdb算法去色带，仅处理Y平面。

||||
|:---|:---|:---|
| <kbd>bd_range</kbd> | 整数 | 色带检测范围 |
| <kbd>bdy_rth</kbd> | 浮点 | 色带检测阈值 —— Y平面，范围 `0.0~255.0` |
| <kbd>grainy</kbd> | 浮点 | 最后阶段添加的颗粒数 —— Y平面，范围 `0.0~255.0` |
| <kbd>spl_m</kbd> | `1`\|`2`\|`3`\|`4` | 采样模式，分别对应 Column Square Row Average(Column&Row) |
| <kbd>grain_dy</kbd> | `True`\|`False` | 是否使用动态颗粒 |

***

### DEINT_LQ

> 所需依赖：[Bwdif](https://vsdb.top/plugins/bwdif)

```python
DEINT_LQ(input=?, iden=True, tff=True)
```

简易反交错。

||||
|:---|:---|:---|
| <kbd>iden</kbd> | `True`\|`False` | 是否输出双倍帧率 |
| <kbd>tff</kbd> | `True`\|`False` | 是否顶场优先 |

***

### DEINT_STD

> 所需依赖：[Bwdif](https://vsdb.top/plugins/bwdif) + [EEDI3](https://vsdb.top/plugins/eedi3m) + [NNEDI3CL](https://vsdb.top/plugins/nnedi3cl) + [TDeintMod](https://vsdb.top/plugins/tdm) + [Yadifmod](https://vsdb.top/plugins/yadifmod) + [znedi3](https://vsdb.top/plugins/znedi3)

```python
DEINT_STD(input=?, ref_m=1, tff=True, gpu=-1, deint_m=1)
```

反交错。输出帧率为双倍

||||
|:---|:---|:---|
| <kbd>ref_m</kbd> | `1`\|`2`\|`3` | 参考模式，分别对应 nnedi3(cpu) nnedi3(opencl) eedi3(opencl) |
| <kbd>tff</kbd> | `True`\|`False` | 是否顶场优先 |
| <kbd>gpu</kbd> | `-1`\|`0`\|`1`\|`2` | 指定显卡，0为排序一号，-1为自动 |
| <kbd>deint_m</kbd> | `1`\|`2`\|`3` | 去隔行的执行核心，分别对应 bwdif yadifmod tdm |

***

### DEINT_EX

> 所需依赖：  
> plugins: [znedi3](https://vsdb.top/plugins/znedi3) + [NNEDI3CL](https://vsdb.top/plugins/nnedi3cl) + [EEDI3](https://vsdb.top/plugins/eedi3m) + [FFT3DFilter](https://vsdb.top/plugins/fft3dfilter) + [libfftw3f-3.dll](http://fftw.org/install/windows.html) + [MVTools](https://vsdb.top/plugins/mv) + [KNLMeansCL](https://vsdb.top/plugins/knlm) + [dfttest2](https://github.com/AmusementClub/vs-dfttest2) + [zsmooth](https://github.com/adworacz/zsmooth)

```python
DEINT_EX(input=?, fps_in=23.976, deint_lv=6, src_type=0, deint_den=1, tff=0, cpu=True, gpu=-1)
```

终极反交错。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>deint_lv</kbd> | `1`\|`2`\|`3`\|`4`\|`5`\|`6`\|`7`\|`8`\|`9`\|`10`\|`11` | 质量等级 |
| <kbd>src_type</kbd> | `0`\|`1`\|`2`\|`3` | 源类型，分别对应： interlaced( `0` ) general-progressive( `1` ) badly-deinterlaced( `2` 或 `3` ) |
| <kbd>deint_den</kbd> | `1`\|`2` | 输出帧率处理（当 <kbd>src_type</kbd> 为 `0` 时会先倍帧预处理），当为 `2` 时减半 |
| <kbd>tff</kbd> | `0`\|`1`\|`2` | 场序，分别对应： 自动检测 顶场优先 底场优先 |
| <kbd>cpu</kbd> | `True`\|`False` | 是否仅使用CPU |
| <kbd>gpu</kbd> | `-1`\|`0`\|`1`\|`2` | 使用的显卡序号， `-1` 为自动， `0` 为排序一号 |

***

### EDI_AA_STD

> 所需依赖：[NNEDI3CL](https://vsdb.top/plugins/nnedi3cl) + [znedi3](https://vsdb.top/plugins/znedi3)

```python
EDI_AA_STD(input=?, cpu=True, gpu=-1)
```

用nnedi3算法抗锯齿。

||||
|:---|:---|:---|
| <kbd>cpu</kbd> | `True`\|`False` | 分别对应使用CPU还是GPU |
| <kbd>gpu</kbd> | `-1`\|`0`\|`1`\|`2` | 指定显卡， `0` 为排序一号， `-1` 为自动 |

***

### EDI_AA_NV

> 所需依赖：[EEDI2CUDA](https://github.com/hooke007/VapourSynth-EEDI2CUDA)

```python
EDI_AA_NV(input=?, gpu=-1, gpu_t=4)
```

用eedi2算法抗锯齿。

||||
|:---|:---|:---|
| <kbd>gpu</kbd> | `-1`\|`0`\|`1`\|`2` | 指定显卡， `0` 为排序一号， `-1` 为自动 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过CPU线程数） |

***

### IVTC_STD

> 所需依赖：[TIVTC](https://vsdb.top/plugins/tivtc) + [VIVTC](https://vsdb.top/plugins/vivtc)

```python
IVTC_STD(input=?, fps_in=25, ivtc_m=1)
```

反转错误的帧率变换（仅限伪25/30帧转24帧）。

||||
|:---|:---|:---|
| <kbd>fps_in</kbd> | 浮点 | 指定输入源的帧率 |
| <kbd>ivtc_m</kbd> | `1`\|`2` | ivtc模式，分别对应 vivtc tivtc |

***

### STAB_STD

> 所需依赖：[MVTools](https://vsdb.top/plugins/mv) + [zsmooth](https://github.com/adworacz/zsmooth)

```python
STAB_STD(input=?)
```

镜头防抖（此类问题常见于胶片转录作品）

***

### STAB_HQ

> 所需依赖：[MVTools](https://vsdb.top/plugins/mv) + [zsmooth](https://github.com/adworacz/zsmooth)

```python
STAB_HQ(input=?)
```

镜头防抖（此类问题常见于胶片转录作品）

***

## 混合

***

### UAI_DML

> 所需依赖：  
> pip3: `onnx`  
> plugins: [vsmlrt](https://github.com/AmusementClub/vs-mlrt) + [akarin](https://vsdb.top/plugins/akarin) + [vszip](https://github.com/dnjulek/vapoursynth-zip)

```python
UAI_DML(input=?, crc=False, model_pth="", fp16_qnt=True, gpu=0, gpu_t=2)
```

基于dx12显卡加速的使用自定义的ONNX模型（仅支持放大类）

||||
|:---|:---|:---|
| <kbd>crc</kbd> | `True`\|`False` | 是否执行色彩恢复补偿 |
| <kbd>model_pth</kbd> | 字符串 | 模型路径 |
| <kbd>fp16_qnt</kbd> | `True`\|`False` | 是否为fp32模型使用混合fp16量化以提速 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |

<kbd>crc</kbd> 仅适用于有明显错误偏色的模型，因为色彩变化可能就是模型设计的一部分。  
<kbd>model_pth</kbd> 所用的模型仅支持部分onnx格式，可在下方链接中找到个人收集的兼容的第三方模型。  
既支持读取在同内建模型路径的模型，示例 `"test/yourmodel.onnx"`  
也支持读取外部绝对路径，示例 `r"X:/xxx/yourmodel.onnx"`  
如果你使用的是 mpv-lazy ，则内建模型的目录为 `.../mpv-lazy/vs-plugins/models/` ，请将要使用的模型放置于此路径下。

👉[**外部及历史模型备份**](https://github.com/hooke007/dotfiles/releases/tag/onnx_models) 

***

### UAI_MIGX

> 所需依赖：  
> pip3: `onnx`  
> plugins: [vsmlrt](https://github.com/AmusementClub/vs-mlrt) + [akarin](https://vsdb.top/plugins/akarin) + [vszip](https://github.com/dnjulek/vapoursynth-zip)

```python
UAI_MIGX(input=?, crc=False, model_pth="", fp16_qnt=True, exh_tune=False, gpu=0, gpu_t=2)
```

基于RDNA显卡加速的使用自定义的ONNX模型（仅支持放大类）

||||
|:---|:---|:---|
| <kbd>crc</kbd> | `True`\|`False` | 是否执行色彩恢复补偿 |
| <kbd>model_pth</kbd> | 字符串 | 模型路径 |
| <kbd>fp16_qnt</kbd> | `True`\|`False` | 是否为fp32模型使用混合fp16量化以提速 |
| <kbd>exh_tune</kbd> | `True`\|`False` | 穷举优化法 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |

<kbd>crc</kbd> 仅适用于有明显错误偏色的模型，因为色彩变化可能就是模型设计的一部分。  
<kbd>model_pth</kbd> 所用的模型仅支持部分onnx格式，可在下方链接中找到个人收集的兼容的第三方模型。  
既支持读取在同内建模型路径的模型，示例 `"test/yourmodel.onnx"`  
也支持读取外部绝对路径，示例 `r"X:/xxx/yourmodel.onnx"`  
如果你使用的是 mpv-lazy ，则内建模型的目录为 `.../mpv-lazy/vs-plugins/models/` ，请将要使用的模型放置于此路径下。

👉[**外部及历史模型备份**](https://github.com/hooke007/dotfiles/releases/tag/onnx_models) 

***

### UAI_NV_TRT

> 所需依赖：  
> plugins: [vsmlrt](https://github.com/AmusementClub/vs-mlrt) + [akarin](https://vsdb.top/plugins/akarin) + [vszip](https://github.com/dnjulek/vapoursynth-zip)

```python
UAI_NV_TRT(input=?, crc=False, model_pth="", opt_lv=3, cuda_opt=[0, 0, 0], int8_qnt=False, fp16_qnt=False, gpu=0, gpu_t=2, st_eng=False, res_opt=None, res_max=None, ws_size=0)
```

使用自定义的ONNX模型（仅支持放大类）

||||
|:---|:---|:---|
| <kbd>crc</kbd> | `True`\|`False` | 是否执行色彩恢复补偿 |
| <kbd>model_pth</kbd> | 字符串 | 模型路径（支持fp16/fp32接口的模型） |
| <kbd>opt_lv</kbd> | `0`\|`1`\|`2`\|`3`\|`4`\|`5` | 构建优化等级。等级越低引擎的生成越快，但可能需要占用更多的性能开销。等级过高可能无法正常生成引擎 |
| <kbd>cuda_opt</kbd> | 整数组（仅限0或1） | 是否启用Cuda的相关优化，例如 `[1, 1, 1]` 即对应全部启用 cuda_graph cudnn cublas 。如果要加速引擎生成，则应全部禁用 |
| <kbd>int8_qnt</kbd> | `True`\|`False` | 是否混合int8量化以提速（不同架构的模型提速表现不一，但总体都有明显的质量退化） |
| <kbd>fp16_qnt</kbd> | `True`\|`False` | 是否为fp32模型使用混合fp16量化以提速 |
| <kbd>gpu</kbd> | `0`\|`1`\|`2` | 指定显卡， `0` 为排序一号 |
| <kbd>gpu_t</kbd> | 整数 | 指定显卡线程数（最大不要超过 `4` ） |
| <kbd>st_eng</kbd> | `True`\|`False` | 是否使用静态引擎（需要对不同分辨率的源各进行预处理）；动态引擎自适应不同分辨率（ 384x384 → <kbd>res_max</kbd> 的值） |
| <kbd>res_opt</kbd> | 整数组 | 模型的首选优化分辨率，必须小于或等于 `res_max` 的值，示例 `[1280, 720]` |
| <kbd>res_max</kbd> | 整数组 | 模型的最大支持的分辨率，示例 `[1920, 1080]` |
| <kbd>ws_size</kbd> | 整数 | 约束显存（MiB），静态引擎的最小值为 `128` （自动为动态引擎进行双倍处理），设为低于此数的值即为不限制 |

<kbd>crc</kbd> 仅适用于有明显错误偏色的模型，因为色彩变化可能就是模型设计的一部分。  
<kbd>model_pth</kbd> 所用的模型仅支持部分onnx格式，可在下方链接中找到个人收集的兼容的第三方模型。  
既支持读取在同内建模型路径的模型，示例 `"test/yourmodel.onnx"`  
也支持读取外部绝对路径，示例 `r"X:/xxx/yourmodel.onnx"`  
如果你使用的是 mpv-lazy ，则内建模型的目录为 `.../mpv-lazy/vs-plugins/models/` ，请将要使用的模型放置于此路径下。

>[!IMPORTANT]
>如果使用动态引擎，则必须指定 <kbd>res_opt</kbd> 和 <kbd>res_max</kbd> ，如使用静态引擎则不填。

在使用动态引擎时， <kbd>res_opt</kbd> 对应的分辨率并不一定是源的分辨率，而是上一个滤镜输出的分辨率。  
- 例如你用 FMT_CTRL 模块预处理所有尺寸过大的片源到720p，那么此时的值应填 `[1280, 720]` （假定宽高比为16:9）；  
- 如果你不用 FMT_CTRL 模块限制分辨率，那么在此时的值应填你最常用的分辨率，比如你看1080p的视频最多，应填 `[1920, 1080]`

>[!TIP]
>在使用动态引擎时， <kbd>res_max</kbd> 限制的是待处理片段的最大分辨率，此分辨率同样并非源的分辨率，而是上一个滤镜输出的分辨率。  
>分辨率给的越大，越需要更大的显存和更长的引擎构建时间，示例的1080p已经足够了。  
>因此，不要填 `[3840, 2160]` 这种不切实际的值（这表示支持4k超到8k，等有RTX6090的话你再试试）。

👉[**外部及历史模型备份**](https://github.com/hooke007/dotfiles/releases/tag/onnx_models) 

***

### UVR_MAD

> 所需依赖：[DualSynth-madVR](https://github.com/Jaded-Encoding-Thaumaturgy/DualSynth-madVR) + [madVR(beta/test)](https://www.videohelp.com/software/madVR)

```python
UVR_MAD(input=?, ngu=0, ngu_q=1, rca_lv=0, rca_q=1)
```

使用自定义的madVR参数渲染（实验性）

||||
|:---|:---|:---|
| <kbd>ngu</kbd> | `0`\|`1`\|`2`\|`3`\|`4` | 是否使用NGU放大两倍， `0` 为禁用，剩下的数值分别对应变体 Anti-Alias Soft Standard Sharp |
| <kbd>ngu_q</kbd> | `1`\|`2`\|`3`\|`4` | NGU的质量，分别对应 low media high veryHigh |
| <kbd>rca_lv</kbd> | `0`\|`1`\|`2`\|`3`\|`4`\|`5`\|`6`\|`7`\|`8`\|`9`\|`10`\|`11`\|`12`\|`13`\|`14` | reduce compression artifacts 的强度， `0` 为禁用 |
| <kbd>rca_q</kbd> | `1`\|`2`\|`3`\|`4` | reduce compression artifacts 的质量，分别对应 low media high veryHigh |

仅供测试，当前既无法指定显卡，性能的利用率也非常低（比在mpc在使用的性能要求可能要翻倍）。

>[!NOTE]
>使用 vsAMD/vsNV 包的用户：此功能所需的madVR组件不被附带在包中，从 [👉此链接](https://github.com/hooke007/dotfiles/releases/tag/mpv_addones) 手动获取 `vs-k7sfunc.0_4_3.mad.b204.7z`  
>解压相关文件到指定路径中，示例 `.../mpv-lazy/vs-plugins/madVR/madVR64.ax`

***
