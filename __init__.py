"""
DDS Save — Blender 图片保存增强（DDS 压缩 + 原生格式扩展）
=========================================
原理：利用 Microsoft DirectXTex texconv.exe 将 PNG 转换为 DDS。
依赖：texconv.exe
下载：https://github.com/microsoft/DirectXTex/releases
"""

# ============================================================================
# 多语言（仅界面文本；控制台/report 消息不在范围内）
# ============================================================================
# 界面文本以中文为源字符串。英文界面通过 en_US 字典把中文源映射为英文；
# 少数英文源（如 "Save All Images"）通过 zh_CN 字典映射为中文。
#
# 两个必须遵守的约束：
#   1) 不能用 bl_info["translation_dictionaries"] 引用本变量——Blender 的
#      addon_utils 用 ast.literal_eval 解析 bl_info，只接受字面量，见到变量名
#      会报 "malformed node or string"。因此改为在 register()/unregister() 里
#      手动调用 bpy.app.translations.register()/unregister()。
#   2) 键必须是 ("上下文", "源字符串") 元组，最外层是语言，中间是上下文。
#      上下文用 "*" 表示默认。写成两层 {lang: {source: target}} 会被 Blender
#      静默丢弃，翻译根本不生效。
_TRANSLATIONS = {
    "en_US": {
        # ---- 插件描述 ----
        ("*", "DDS 仅用 Blender 原生保存器生成 PNG，再交给 texconv 转码；按格式提供对应编码参数"):
            "DDS uses Blender's native saver to produce PNG, then hands it to texconv for "
            "transcoding; provides encoding parameters per format",
        ("*", "图像编辑器 > 图像 > 保存 / 另存为…"):
            "Image Editor > Image > Save / Save As…",

        # ---- DDS_FORMATS ----
        ("*", "BC7 压缩 sRGB，视觉无损，适用于颜色/漫反射贴图"):
            "BC7 compressed sRGB, visually lossless, suitable for color/diffuse maps",
        ("*", "BC7 压缩线性，适用于金属度/粗糙度/ AO 等数据贴图"):
            "BC7 compressed linear, suitable for metallic/roughness/AO data maps",
        ("*", "DXT1 压缩 sRGB，4bpp，无 Alpha"):
            "DXT1 compressed sRGB, 4bpp, no alpha",
        ("*", "DXT1 压缩线性，4bpp"):
            "DXT1 compressed linear, 4bpp",
        ("*", "DXT5 压缩 sRGB，8bpp，带 Alpha"):
            "DXT5 compressed sRGB, 8bpp, with alpha",
        ("*", "DXT5 压缩线性，8bpp，带 Alpha"):
            "DXT5 compressed linear, 8bpp, with alpha",
        ("*", "BC5 (法线贴图)"):
            "BC5 (Normal Map)",
        ("*", "双通道压缩，适用于法线贴图存储 XY"):
            "Two-channel compression, suitable for storing normal map XY",
        ("*", "未压缩 32bpp sRGB，数学无损"):
            "Uncompressed 32bpp sRGB, mathematically lossless",
        ("*", "未压缩 32bpp 线性，数学无损"):
            "Uncompressed 32bpp linear, mathematically lossless",

        # ---- MIP_FILTERS ----
        ("*", "箱式过滤"): "Box filter",
        ("*", "三角过滤"): "Triangle filter",
        ("*", "立方过滤"): "Cubic filter",
        ("*", "Fant 过滤（默认）"): "Fant filter (default)",
        ("*", "B 样条"): "B-Spline",
        ("*", "Catmull-Rom 过滤"): "Catmull-Rom filter",
        ("*", "Mitchell 过滤"): "Mitchell filter",
        ("*", "Lanczos 过滤"): "Lanczos filter",

        # ---- EXPORT_FILE_FORMATS ----
        ("*", "DDS（BC 压缩）"): "DDS (BC compressed)",
        ("*", "DirectDraw Surface，由 texconv 压缩（BC7/BC1/BC3/BC5 等）"):
            "DirectDraw Surface, compressed by texconv (BC7/BC1/BC3/BC5, etc.)",
        ("*", "无损 PNG，Blender 原生保存"):
            "Lossless PNG, saved natively by Blender",
        ("*", "有损 JPEG，支持质量参数"):
            "Lossy JPEG, supports quality parameter",
        ("*", "有损/无损 WebP，支持质量参数"):
            "Lossy/lossless WebP, supports quality parameter",
        ("*", "无损 TIFF"): "Lossless TIFF",
        ("*", "浮点 EXR"): "Floating-point EXR",
        ("*", "无压缩位图"): "Uncompressed bitmap",
        ("*", "辐照度 HDR"): "Radiance HDR",
        ("*", "JP2 格式"): "JP2 format",
        ("*", "Cineon 胶片格式"): "Cineon film format",
        ("*", "数字图像交换格式"): "Digital Picture Exchange format",
        ("*", "AV1 图像格式"): "AV1 image format",

        # ---- GPU ----
        ("*", "默认 GPU"): "Default GPU",

        # ---- DDSSavePreferences ----
        ("*", "texconv.exe 路径"): "texconv.exe Path",
        ("*", "指向 texconv.exe 的完整路径，留空则自动查找"):
            "Full path to texconv.exe; leave empty to auto-detect",
        ("*", "GPU 适配器"): "GPU Adapter",
        ("*", "选择用于 texconv 加速的 GPU（列表为 DXGI 适配器，索引直接传给 texconv -gpu）"):
            "Select the GPU used for texconv acceleration "
            "(list shows DXGI adapters; index is passed directly to texconv -gpu)",
        ("*", "GPU 加速"): "GPU Acceleration",
        ("*", "使用 GPU DirectCompute 加速压缩（推荐）"):
            "Use GPU DirectCompute to accelerate compression (recommended)",
        ("*", "单线程模式"): "Single-threaded Mode",
        ("*", "强制单线程处理（调试用，会显著变慢）"):
            "Force single-threaded processing (for debugging; significantly slower)",
        ("*", "texconv 路径（留空则自动查找）"):
            "texconv Path (empty = auto-detect)",
        ("*", "✗ 未找到"): "✗ Not found",
        ("*", "将 texconv.exe 放入插件目录，或点击下方下载"):
            "Place texconv.exe in the add-on directory, or click below to download",
        ("*", "下载 texconv.exe"): "Download texconv.exe",
        ("*", "引擎设置"): "Engine Settings",

        # ---- SaveParamsMixin ----
        ("*", "格式"): "Format",
        ("*", "颜色"): "Color",
        ("*", "色深"): "Color Depth",
        ("*", "色彩空间"): "Color Space",
        ("*", "质量"): "Quality",
        ("*", "压缩"): "Compression",
        ("*", "压缩方式"): "Compression",
        ("*", "DDS 格式"): "DDS Format",
        ("*", "旧版 sRGB 输入（已弃用）"): "Legacy sRGB Input (deprecated)",
        ("*", "仅为兼容旧版配置保留。DDS 保存时会按目标 DDS 格式自动处理色彩空间。"):
            "Kept only for compatibility with old configs. "
            "DDS saving handles color space automatically based on the target DDS format.",
        ("*", "BC7 压缩质量"): "BC7 Compression Quality",
        ("*", "快速"): "Quick",
        ("*", "仅模式 6"): "Mode 6 only",
        ("*", "标准"): "Standard",
        ("*", "texconv 默认"): "texconv default",
        ("*", "最高"): "Maximum",
        ("*", "启用更完整模式"): "Enable more complete modes",
        ("*", "BC1-3 权重"): "BC1-3 Weighting",
        ("*", "感知权重"): "Perceptual",
        ("*", "texconv 默认的人眼感知权重"): "texconv's default perceptual weighting",
        ("*", "统一权重"): "Uniform",
        ("*", "BC1-3 抖动"): "BC1-3 Dither",
        ("*", "对 BC1-3 启用抖动（-bc d）"): "Enable dithering for BC1-3 (-bc d)",
        ("*", "Alpha 阈值"): "Alpha Threshold",
        ("*", "BC1 1-bit Alpha 阈值（-at）"): "BC1 1-bit alpha threshold (-at)",
        ("*", "Coverage 参考值"): "Coverage Reference",
        ("*", "生成 Mipmap 时 Alpha Coverage 参考值（-keepcoverage）"):
            "Alpha coverage reference when generating mipmaps (-keepcoverage)",
        ("*", "BC7 Alpha 权重"): "BC7 Alpha Weight",
        ("*", "BC7 GPU 编码的 Alpha 误差权重（-aw）"):
            "Alpha error weight for BC7 GPU encoding (-aw)",
        ("*", "独立处理 Alpha"): "Separate Alpha",
        ("*", "生成/过滤 Mipmap 时单独处理 Alpha（-sepalpha）"):
            "Handle alpha separately when generating/filtering mipmaps (-sepalpha)",
        ("*", "保持 Alpha 覆盖率"): "Keep Alpha Coverage",
        ("*", "生成 Mipmap 时保持 Alpha 覆盖率（-keepcoverage）"):
            "Preserve alpha coverage when generating mipmaps (-keepcoverage)",
        ("*", "Alpha 处理"): "Alpha Handling",
        ("*", "保持原样"): "Keep",
        ("*", "不对 Alpha 做额外变换"): "No extra alpha transform",
        ("*", "预乘 Alpha"): "Premultiplied Alpha",
        ("*", "直通 Alpha"): "Straight Alpha",
        ("*", "生成 Mipmap"): "Generate Mipmaps",
        ("*", "Mip 过滤"): "Mip Filter",

        # ---- Operators ----
        # Operator 的 bl_label / bl_description 使用 "Operator" 翻译上下文，
        # 不是默认的 "*"。放错上下文时 UI 会原样显示源字符串（中文）。
        ("Operator", "刷新 GPU 列表"): "Refresh GPU List",
        ("Operator", "保存"): "Save",
        ("Operator", "保存当前图片（弹出参数设置，每张贴图独立记忆）"):
            "Save current image (opens a parameter dialog; remembered per image)",
        ("Operator", "另存为…"): "Save As…",
        ("Operator", "将当前图片另存为 DDS 或 Blender 原生格式"):
            "Save current image as DDS or a Blender-native format",
        ("Operator", "保存副本…"): "Save a Copy…",
        ("Operator", "将当前图片保存为副本到指定位置（DDS 由 texconv 压缩）"):
            "Save a copy of the current image to a chosen location "
            "(DDS compressed by texconv)",
        ("Operator", "保存所有已修改的图像（DDS 由 texconv 压缩）"):
            "Save all modified images (DDS compressed by texconv)",
    },

    # 少数英文源字符串在中文界面下的翻译（其余原生英文串由 Blender 内置字典处理）
    "zh_CN": {
        ("Operator", "Save All Images"): "保存所有图像",
    },
}


import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
import math
from pathlib import Path

import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty
from bpy_extras.io_utils import ExportHelper


# ============================================================================
# 常量
# ============================================================================

DDS_FORMATS = [
    ("BC7_UNORM_SRGB", "BC7 SRGB", "BC7 压缩 sRGB，视觉无损，适用于颜色/漫反射贴图"),
    ("BC7_UNORM", "BC7 Linear", "BC7 压缩线性，适用于金属度/粗糙度/ AO 等数据贴图"),
    ("BC1_UNORM_SRGB", "BC1 SRGB (DXT1)", "DXT1 压缩 sRGB，4bpp，无 Alpha"),
    ("BC1_UNORM", "BC1 Linear (DXT1)", "DXT1 压缩线性，4bpp"),
    ("BC3_UNORM_SRGB", "BC3 SRGB (DXT5)", "DXT5 压缩 sRGB，8bpp，带 Alpha"),
    ("BC3_UNORM", "BC3 Linear (DXT5)", "DXT5 压缩线性，8bpp，带 Alpha"),
    ("BC5_UNORM", "BC5 (法线贴图)", "双通道压缩，适用于法线贴图存储 XY"),
    ("R8G8B8A8_UNORM_SRGB", "R8G8B8A8 SRGB", "未压缩 32bpp sRGB，数学无损"),
    ("R8G8B8A8_UNORM", "R8G8B8A8 Linear", "未压缩 32bpp 线性，数学无损"),
]

MIP_FILTERS = [
    ("BOX", "BOX", "箱式过滤"),
    ("TRIANGLE", "TRIANGLE", "三角过滤"),
    ("CUBIC", "CUBIC", "立方过滤"),
    ("FANT", "FANT", "Fant 过滤（默认）"),
    ("B_SPLINE", "B-Spline", "B 样条"),
    ("CATMULL_ROM", "Catmull-Rom", "Catmull-Rom 过滤"),
    ("MITCHELL", "Mitchell", "Mitchell 过滤"),
    ("LANCZOS3", "Lanczos", "Lanczos 过滤"),
]

EXPORT_FILE_FORMATS = [
    ("DDS", "DDS（BC 压缩）", "DirectDraw Surface，由 texconv 压缩（BC7/BC1/BC3/BC5 等）"),
    ("PNG", "PNG", "无损 PNG，Blender 原生保存"),
    ("JPEG", "JPEG", "有损 JPEG，支持质量参数"),
    ("WEBP", "WebP", "有损/无损 WebP，支持质量参数"),
    ("TIFF", "TIFF", "无损 TIFF"),
    ("OPEN_EXR", "OpenEXR", "浮点 EXR"),
    ("BMP", "BMP", "无压缩位图"),
    ("TARGA", "Targa", "TGA"),
    ("HDR", "Radiance HDR", "辐照度 HDR"),
    ("IRIS", "Iris", "SGI Iris"),
    ("JPEG2000", "JPEG 2000", "JP2 格式"),
    ("CINEON", "Cineon", "Cineon 胶片格式"),
    ("DPX", "DPX", "数字图像交换格式"),
    ("AVIF", "AVIF", "AV1 图像格式"),
]

EXPORT_EXTENSIONS = {
    "DDS": ".dds", "PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp",
    "TIFF": ".tif", "OPEN_EXR": ".exr", "BMP": ".bmp", "TARGA": ".tga",
    "HDR": ".hdr", "IRIS": ".rgb", "JPEG2000": ".jp2", "CINEON": ".cin",
    "DPX": ".dpx", "AVIF": ".avif",
}

_TMP_MARK = ".dds_save_"

# 记录本次会话中由本插件生成的 DDS。Texture Auto Reload 可能重建/重载图像数据，
# 因此不能只把签名放在 Image 自定义属性里。全局缓存用于保证紧接着第二次“保存”
# 不会再次进行有损 BC 压缩；文件状态改变后会自动失效。
_DDS_SAVE_SIGNATURES = {}


def _format_ext(fmt):
    return EXPORT_EXTENSIONS.get(fmt, ".dds")


def _looks_like_temp_path(path):
    if not path:
        return False
    return _TMP_MARK in os.path.basename(path)


# ============================================================================
# PNG 编码器
# ============================================================================

PNG_COLOR_TYPES = {"BW": 0, "RGB": 2, "RGBA": 6}
DDS_SRGB_FORMATS = {
    fmt for fmt, _label, _desc in DDS_FORMATS if fmt.endswith("_SRGB")
}


def _dds_format_is_srgb(dds_format):
    """返回 DDS 输出格式是否带有 DXGI 的 _SRGB 后缀。"""
    return str(dds_format).upper() in DDS_SRGB_FORMATS


# DirectXTex / DXGI 的 SRGB 格式编号。DDS DX10 扩展头能明确告诉我们
# 原始 DDS 是线性还是 SRGB；这比依赖 Blender 对 DDS 的自动猜测可靠。
def _linear_to_srgb(value):
    """把 Blender 的场景线性 RGB 值转换为标准 sRGB 编码值。"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def _png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(pixels, width, height, color_mode="RGBA", bit_depth=8,
               compression=15, colorspace="Linear"):
    """以指定颜色空间写 PNG。

    Blender 的长期 float image buffer 使用场景线性值。这里不通过
    image.colorspace_settings 隐式转换，而是把输出颜色空间明确写进编码器。
    对 sRGB 输出执行 linear->sRGB 编码，并写入 PNG sRGB chunk。
    """
    if color_mode not in PNG_COLOR_TYPES:
        raise ValueError(f"不支持的 PNG 颜色模式: {color_mode}")
    if int(bit_depth) not in (8, 16):
        raise ValueError(f"不支持的 PNG 色深: {bit_depth}")
    if colorspace not in {"sRGB", "Linear", "Non-Color"}:
        raise ValueError(f"不支持的 PNG 色彩空间: {colorspace}")

    maxv = 65535 if int(bit_depth) == 16 else 255
    use16 = int(bit_depth) == 16
    color_type = PNG_COLOR_TYPES[color_mode]
    values = list(pixels)

    expected = width * height * 4
    if len(values) < expected:
        raise ValueError(f"像素数据不足: 需要 {expected}，实际 {len(values)}")

    def convert_channel(value):
        return _linear_to_srgb(value) if colorspace == "sRGB" else value

    rows = []
    for y in range(height - 1, -1, -1):
        base = y * width * 4
        row = bytearray()
        for x in range(width):
            i = base + x * 4
            r, g, b, a = values[i], values[i + 1], values[i + 2], values[i + 3]
            if color_mode == "BW":
                vals = (0.2126 * r + 0.7152 * g + 0.0722 * b,)
            elif color_mode == "RGB":
                vals = (r, g, b)
            else:
                vals = (r, g, b, a)

            for channel_index, value in enumerate(vals):
                value = convert_channel(value) if channel_index < len(vals) - (1 if color_mode == "RGBA" else 0) else value
                try:
                    if not math.isfinite(float(value)):
                        value = 0.0
                except (TypeError, ValueError):
                    value = 0.0
                value = max(0.0, min(1.0, float(value)))
                iv = int(round(value * maxv))
                if use16:
                    row += struct.pack(">H", iv)
                else:
                    row.append(iv)
        rows.append(b"\x00" + bytes(row))

    level = max(0, min(9, int(round(float(compression) * 9 / 100))))
    ihdr = struct.pack(">IIBBBBB", width, height, int(bit_depth), color_type, 0, 0, 0)
    chunks = [b"\x89PNG\r\n\x1a\n", _png_chunk(b"IHDR", ihdr)]
    if colorspace == "sRGB":
        # PNG sRGB intent 0 = Perceptual.
        chunks.append(_png_chunk(b"sRGB", b"\x00"))
    chunks.append(_png_chunk(b"IDAT", zlib.compress(b"".join(rows), level)))
    chunks.append(_png_chunk(b"IEND", b""))
    return b"".join(chunks)


def write_png(path, image, color_mode="RGBA", bit_depth=8, compression=15,
              colorspace="Linear"):
    w, h = image.size
    if w <= 0 or h <= 0:
        raise ValueError("图像尺寸无效")
    data = encode_png(list(image.pixels), w, h, color_mode, bit_depth,
                      compression, colorspace)
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


def _save_with_render_settings(image, path, fmt, color_mode="RGBA", color_depth=8,
                               exr_codec=None, tiff_codec=None, scene=None):
    sc = scene if scene is not None else bpy.context.scene
    if sc is None:
        raise ValueError("缺少场景上下文")

    ian = sc.render.image_settings
    old = {
        "view_transform": sc.view_settings.view_transform,
        "file_format": ian.file_format, "color_mode": ian.color_mode,
        "color_depth": ian.color_depth, "compression": ian.compression,
        "exr_codec": ian.exr_codec, "tiff_codec": ian.tiff_codec,
    }
    try:
        sc.view_settings.view_transform = "Standard"
        ian.file_format = fmt
        ian.color_mode = color_mode
        depth = str(color_depth)
        supported = ian.bl_rna.properties["color_depth"]
        valid = {it.identifier for it in supported.enum_items}
        if depth in valid:
            ian.color_depth = depth
        if exr_codec:
            ian.exr_codec = exr_codec
        if tiff_codec:
            ian.tiff_codec = tiff_codec
        image.save_render(path, scene=sc)
    finally:
        sc.view_settings.view_transform = old["view_transform"]
        ian.file_format = old["file_format"]
        ian.color_mode = old["color_mode"]
        ian.color_depth = old["color_depth"]
        ian.compression = old["compression"]
        ian.exr_codec = old["exr_codec"]
        ian.tiff_codec = old["tiff_codec"]


# ============================================================================
# Texconv 管理器
# ============================================================================


# ============================================================================
# Texconv 命令构建：把 UI 参数一项一项严格映射到官方命令行
# ============================================================================

_DDS_BC7_FORMATS = {"BC7_UNORM", "BC7_UNORM_SRGB"}
_DDS_BC6H_FORMATS = set()
_DDS_BC1_3_FORMATS = {
    "BC1_UNORM", "BC1_UNORM_SRGB",
    "BC3_UNORM", "BC3_UNORM_SRGB",
}
_DDS_BC_FORMATS = _DDS_BC1_3_FORMATS | _DDS_BC7_FORMATS | {
    "BC5_UNORM",
}


def _dds_is_bc7(dds_format):
    return str(dds_format).upper() in _DDS_BC7_FORMATS


def _dds_is_bc1_3(dds_format):
    return str(dds_format).upper() in _DDS_BC1_3_FORMATS


def _dds_is_bc(dds_format):
    return str(dds_format).upper() in _DDS_BC_FORMATS


def _build_texconv_command(texconv_path, input_png, output_dds, dds_format,
                            mip_enabled=False, mip_filter="FANT",
                            bc_quality="standard", use_gpu=True,
                            gpu_adapter=0, singleproc=False,
                            ignore_srgb_metadata=False,
                            bc_weighting="perceptual", bc_dither=False,
                            alpha_threshold=0.5, coverage_ref=0.5, alpha_weight=1.0,
                            separate_alpha=False, keep_coverage=False,
                            alpha_mode="KEEP"):
    """严格映射 UI 到 texconv；不额外修改像素内容。

    适用范围按 DirectXTex 官方选项区分：
      * BC1-BC3：-bc u/d，以及 BC1 的 -at。
      * BC7：-bc q/x、-aw；GPU/CPU/singleproc。
      * BC7：GPU/CPU/singleproc。
      * 生成 mip：-m 0 + -if；-sepalpha / -keepcoverage。
      * 其它格式不发送不适用的 BC 编码参数。
    """
    fmt = str(dds_format).upper()
    cmd = [str(texconv_path), "-nologo", "-y", "-ft", "DDS", "-f", fmt]

    if mip_enabled:
        cmd.extend(["-m", "0", "-if", str(mip_filter)])
        if separate_alpha:
            cmd.append("-sepalpha")
        if keep_coverage:
            cmd.extend(["-keepcoverage", str(float(coverage_ref))])
    else:
        cmd.extend(["-m", "1"])

    if ignore_srgb_metadata:
        cmd.append("--ignore-srgb")

    if _dds_is_bc1_3(fmt):
        bc_flags = []
        if str(bc_weighting).lower() == "uniform":
            bc_flags.append("u")
        if bc_dither:
            bc_flags.append("d")
        if bc_flags:
            cmd.extend(["-bc", "".join(bc_flags)])
        if fmt in {"BC1_UNORM", "BC1_UNORM_SRGB"}:
            cmd.extend(["-at", str(float(alpha_threshold))])

    if _dds_is_bc7(fmt):
        if use_gpu:
            cmd.extend(["-gpu", str(int(gpu_adapter))])
        else:
            cmd.append("-nogpu")

        if bc_quality == "quick":
            cmd.extend(["-bc", "q"])
        elif bc_quality == "max":
            cmd.extend(["-bc", "x"])

        if use_gpu:
            cmd.extend(["-aw", str(float(alpha_weight))])

        if singleproc and not use_gpu:
            cmd.append("-singleproc")

    if alpha_mode == "PREMLTIPLIED":
        cmd.append("-pmalpha")
    elif alpha_mode == "STRAIGHT":
        cmd.append("-alpha")

    cmd.extend(["-o", str(Path(output_dds).parent or "."), str(input_png)])
    return cmd


class TexconvManager:
    def __init__(self, manual_path=None):
        self.path = None
        if manual_path and os.path.isfile(manual_path):
            self.path = manual_path
        else:
            self._find()

    def _find(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(plugin_dir, "texconv.exe")
        if os.path.isfile(local_path):
            self.path = local_path
            return
        texconv = shutil.which("texconv.exe")
        if texconv:
            self.path = texconv
            return
        for p in [r"C:\Program Files\DirectXTex\texconv.exe",
                  r"C:\Program Files (x86)\DirectXTex\texconv.exe",
                  r"C:\tools\texconv.exe"]:
            if os.path.isfile(p):
                self.path = p
                return

    @property
    def available(self):
        return self.path is not None

    def convert(self, input_png, output_dds, dds_format="BC7_UNORM_SRGB",
                mip_enabled=False, mip_filter="FANT", srgb_input=False,
                bc_quality="max", use_gpu=True, gpu_adapter=0, singleproc=False,
                srgb_output=False, ignore_srgb_metadata=None,
                bc_weighting="perceptual", bc_dither=False,
                alpha_threshold=0.5, coverage_ref=0.5, alpha_weight=1.0,
                separate_alpha=False, keep_coverage=False,
                alpha_mode="KEEP"):
        if not self.path:
            return False, "texconv.exe 未找到"
        if not os.path.isfile(input_png):
            return False, f"输入文件不存在: {input_png}"

        out_dir = os.path.dirname(output_dds) or "."
        os.makedirs(out_dir, exist_ok=True)

        if ignore_srgb_metadata is None:
            ignore_srgb_metadata = not _dds_format_is_srgb(dds_format)

        cmd = _build_texconv_command(
            self.path, input_png, output_dds, dds_format,
            mip_enabled=mip_enabled, mip_filter=mip_filter,
            bc_quality=bc_quality, use_gpu=use_gpu, gpu_adapter=gpu_adapter,
            singleproc=singleproc, ignore_srgb_metadata=ignore_srgb_metadata,
            bc_weighting=bc_weighting, bc_dither=bc_dither,
            alpha_threshold=alpha_threshold, coverage_ref=coverage_ref,
            alpha_weight=alpha_weight, separate_alpha=separate_alpha,
            keep_coverage=keep_coverage, alpha_mode=alpha_mode,
        )


        # 诊断：把最终命令行打印到 Blender 控制台。
        try:
            print(f"[DDS Save] texconv cmd: {' '.join(cmd)}")
        except Exception:
            pass

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(cmd, capture_output=True, text=True,
                                    startupinfo=startupinfo, check=False,
                                    encoding="utf-8", errors="replace")

            if result.returncode != 0:
                err = result.stderr.strip() or "未知错误"
                expected = os.path.join(out_dir, Path(input_png).stem + ".dds")
                if os.path.normcase(os.path.abspath(expected)) != \
                        os.path.normcase(os.path.abspath(output_dds)):
                    _safe_remove(expected)
                return False, f"texconv 错误码 {result.returncode}: {err}"

            expected = os.path.join(out_dir, Path(input_png).stem + ".dds")
            if os.path.isfile(expected):
                same = (os.path.normcase(os.path.abspath(expected))
                        == os.path.normcase(os.path.abspath(output_dds)))
                if not same:
                    if os.path.isfile(output_dds):
                        os.remove(output_dds)
                    shutil.move(expected, output_dds)
                return True, f"保存成功: {output_dds}"
            return False, "texconv 未生成预期输出文件"
        except Exception as e:
            return False, f"执行 texconv 异常: {e}"


# ============================================================================
# GPU 检测
# ============================================================================

_gpu_cache = []


def _enumerate_dxgi_adapters():
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    class _GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)]

    class _LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD),
                    ("HighPart", wintypes.LONG)]

    class _DXGI_ADAPTER_DESC1(ctypes.Structure):
        _fields_ = [
            ("Description", ctypes.c_wchar * 128),
            ("VendorId", wintypes.UINT),
            ("DeviceId", wintypes.UINT),
            ("SubSysId", wintypes.UINT),
            ("Revision", wintypes.UINT),
            ("DedicatedVideoMemory", ctypes.c_size_t),
            ("DedicatedSystemMemory", ctypes.c_size_t),
            ("SharedSystemMemory", ctypes.c_size_t),
            ("AdapterLuid", _LUID),
            ("Flags", wintypes.UINT),
        ]

    iid = _GUID(0x770AAE78, 0xF26F, 0x4DBA,
                (wintypes.BYTE * 8)(0xA8, 0x29, 0x25, 0x3C,
                                    0x83, 0xD1, 0xB3, 0x87))

    try:
        dxgi = ctypes.windll.dxgi
    except (OSError, AttributeError):
        return None

    dxgi.CreateDXGIFactory1.restype = ctypes.c_int32
    dxgi.CreateDXGIFactory1.argtypes = [ctypes.POINTER(_GUID),
                                        ctypes.POINTER(ctypes.c_void_p)]

    factory = ctypes.c_void_p()
    hr = dxgi.CreateDXGIFactory1(ctypes.byref(iid), ctypes.byref(factory))
    if hr != 0 or not factory:
        return None

    def _vtbl_func(pobj, slot, restype, *argtypes):
        table = ctypes.cast(
            pobj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        addr = table[slot]
        if isinstance(addr, ctypes.c_void_p):
            addr = addr.value
        return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(addr)

    EnumAdapters1 = _vtbl_func(factory, 12, ctypes.c_int32,
                               ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))
    Release = _vtbl_func(factory, 2, ctypes.c_ulong)

    adapters = []
    try:
        idx = 0
        while True:
            adapter = ctypes.c_void_p()
            if EnumAdapters1(factory, idx, ctypes.byref(adapter)) != 0:
                break
            try:
                GetDesc1 = _vtbl_func(adapter, 10, ctypes.c_int32,
                                      ctypes.POINTER(_DXGI_ADAPTER_DESC1))
                desc = _DXGI_ADAPTER_DESC1()
                if GetDesc1(adapter, ctypes.byref(desc)) == 0:
                    adapters.append((
                        idx,
                        desc.Description,
                        int(desc.DedicatedVideoMemory),
                        desc.VendorId,
                        desc.DeviceId,
                        desc.SubSysId,
                        desc.Revision,
                        desc.AdapterLuid.LowPart,
                        desc.AdapterLuid.HighPart,
                        desc.Flags,
                    ))
            finally:
                _vtbl_func(adapter, 2, ctypes.c_ulong)(adapter)
            idx += 1
    finally:
        Release(factory)

    return adapters or None


def _detect_gpus():
    adapters = _enumerate_dxgi_adapters()
    if adapters:
        result = []
        for (idx, name, vram, vendor, device, subsys, revision,
             luid_low, luid_high, flags) in adapters:
            # DXGI_ADAPTER_FLAG_SOFTWARE = 2，过滤软件渲染器
            if flags & 2:
                continue
            name = (name or f"GPU {idx}").strip()
            vram_mb = vram // (1024 * 1024) if vram else 0
            label = f"{name}  ({vram_mb} MB)" if vram_mb else name
            result.append((str(idx), label, idx))

        def _rank(item):
            n = item[1].upper()
            if any(k in n for k in ("NVIDIA", "GEFORCE", "RTX", "GTX")):
                return 0
            if any(k in n for k in ("AMD", "RADEON")):
                return 1
            if any(k in n for k in ("INTEL", "UHD", "IRIS")):
                return 3
            return 2

        result.sort(key=_rank)
        return result or [("0", "默认 GPU", 0)]

    return [("0", "默认 GPU", 0)]


def _refresh_gpu_cache():
    global _gpu_cache
    _gpu_cache = _detect_gpus()


def _get_gpu_items(self, context):
    if not _gpu_cache:
        _refresh_gpu_cache()
    return [(ident, name, f"DXGI 适配器 {idx}（传给 texconv -gpu {idx}）")
            for ident, name, idx in _gpu_cache]


def _get_gpu_index(identifier):
    if not _gpu_cache:
        _refresh_gpu_cache()
    for ident, name, idx in _gpu_cache:
        if ident == identifier:
            return idx
    try:
        old_idx = int(identifier)
        for ident, name, idx in _gpu_cache:
            if idx == old_idx:
                return idx
    except (ValueError, TypeError):
        pass
    return 0


# ============================================================================
# 插件偏好设置
# ============================================================================

class DDSSavePreferences(AddonPreferences):
    bl_idname = __package__ if __package__ else __name__

    texconv_path: StringProperty(
        name="texconv.exe 路径",
        description="指向 texconv.exe 的完整路径，留空则自动查找",
        subtype="FILE_PATH",
        default="",
    )
    gpu_adapter: EnumProperty(
        name="GPU 适配器",
        description="选择用于 texconv 加速的 GPU（列表为 DXGI 适配器，索引直接传给 texconv -gpu）",
        items=_get_gpu_items,
    )
    use_gpu: BoolProperty(
        name="GPU 加速",
        description="使用 GPU DirectCompute 加速压缩（推荐）",
        default=True,
    )
    singleproc: BoolProperty(
        name="单线程模式",
        description="强制单线程处理（调试用，会显著变慢）",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="texconv 路径（留空则自动查找）", icon="SETTINGS")
        box.prop(self, "texconv_path", text="")
        mgr = TexconvManager(self.texconv_path or None)
        if mgr.available:
            box.label(text=f"✓ {mgr.path}", icon="CHECKBOX_HLT")
        else:
            box.label(text="✗ 未找到", icon="ERROR")
            box.label(text="将 texconv.exe 放入插件目录，或点击下方下载", icon="INFO")
            row = box.row()
            row.operator("wm.url_open", text="下载 texconv.exe", icon="URL").url \
                = "https://github.com/microsoft/DirectXTex/releases"

        box2 = layout.box()
        box2.label(text="引擎设置", icon="PREFERENCES")
        box2.prop(self, "use_gpu")
        row = box2.row()
        row.prop(self, "gpu_adapter", text="")
        row.operator("wm.dds_refresh_gpus", text="", icon="FILE_REFRESH")
        box2.prop(self, "singleproc")


# ============================================================================
# 共享工具函数与保存核心逻辑
# ============================================================================

def _safe_remove(path):
    if path and os.path.isfile(path):
        try:
            os.unlink(path)
        except OSError:
            pass


def _clear_image_dirty_via_native_save(image):
    """借一次 Blender 原生 Image.save() 写入临时 PNG 来清除 is_dirty 标记。

    背景：Blender 只在图像真正经过自身的原生保存器写出后才清除 `is_dirty`。
    DDS 路径全部走 texconv，Blender 不会把磁盘上的结果当作“已保存”，于是
    图像会一直显示为未保存状态。这里在系统临时目录写一个临时 PNG，触发
    Blender 原生保存器的清脏逻辑，随后立即删除该 PNG。

    副作用：仅临时改动 image.filepath_raw / image.file_format（保存后立即恢复），
    不改变像素内容、不改变色彩空间、不改变 DDS/PNG 产物。
    """
    try:
        if not bool(getattr(image, "is_dirty", False)):
            return
    except Exception:
        return

    tmp_path = None
    fd = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=_TMP_MARK + "dirty_",
                                        suffix=".png")
    except Exception:
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    if not tmp_path:
        return

    orig_filepath_raw = None
    orig_file_format = None
    try:
        try:
            orig_filepath_raw = image.filepath_raw
        except Exception:
            orig_filepath_raw = None
        try:
            orig_file_format = image.file_format
        except Exception:
            orig_file_format = None

        try:
            image.filepath_raw = tmp_path
        except Exception:
            pass
        try:
            image.file_format = "PNG"
        except Exception:
            pass

        try:
            image.save()
        except Exception:
            pass
    finally:
        try:
            if orig_filepath_raw is not None:
                image.filepath_raw = orig_filepath_raw
        except Exception:
            pass
        try:
            if orig_file_format is not None:
                image.file_format = orig_file_format
        except Exception:
            pass
        _safe_remove(tmp_path)


def _get_prefs(context=None):
    ctx = context if context is not None else bpy.context
    try:
        return ctx.preferences.addons[__package__].preferences
    except (KeyError, AttributeError):
        pass
    return DDSSavePreferences()


def _capture_image_editor_context(context, image):
    """在参数弹窗出现前记录发起保存的真实 IMAGE_EDITOR。"""
    try:
        area = getattr(context, "area", None)
        window = getattr(context, "window", None)
        if area is not None and getattr(area, "type", None) == "IMAGE_EDITOR":
            space = area.spaces.active
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            if space is not None:
                return window, getattr(window, "screen", None), area, region, space
    except Exception:
        pass
    return None


def _find_image_editor_context(context, image=None, preferred=None):
    """找到可用于 Blender 原生 IMAGE_OT_save_as 的 IMAGE_EDITOR 上下文。"""
    candidates = []

    def add(info, priority):
        if not info:
            return
        try:
            window, screen, area, region, space = info
            if area is None or area.type != "IMAGE_EDITOR" or space is None:
                return
            if image is not None and getattr(space, "image", None) is image:
                priority -= 100
            candidates.append((priority, info))
        except Exception:
            pass

    add(preferred, -1000)
    add(_capture_image_editor_context(context, image), -900)

    wm = getattr(context, "window_manager", None)
    for window in getattr(wm, "windows", []) or []:
        screen = getattr(window, "screen", None)
        for area in getattr(screen, "areas", []) or []:
            if getattr(area, "type", None) != "IMAGE_EDITOR":
                continue
            try:
                space = area.spaces.active
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                if space is not None:
                    add((window, screen, area, region, space), 0)
            except Exception:
                continue

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _new_native_png_image(image):
    """建立一个拥有真实像素缓冲的 Blender 临时 Image。

    这里不使用 Image.copy()，因为 Blender 的 Image.copy() 只复制数据块包装器，
    不复制底层像素缓冲。临时图像只存在于保存期间，原图不会被修改。
    """
    from array import array

    w, h = map(int, image.size)
    if w <= 0 or h <= 0:
        raise ValueError("图像尺寸无效")

    temp = bpy.data.images.new(
        name=f"{_TMP_MARK}png_{os.getpid()}_{int(time.time() * 1000) & 0xFFFFFF:x}",
        width=w,
        height=h,
        alpha=True,
        float_buffer=False,
    )
    try:
        # 这些设置对应用户在 Blender 原生 Save As PNG 中验证过的路径：
        # PNG / RGBA / 8-bit；颜色空间直接继承当前 Image 的颜色空间设置。
        temp.source = "GENERATED"
        try:
            temp.generated_type = "BLANK"
        except Exception:
            pass
        temp.file_format = "PNG"
        try:
            src_cs = image.colorspace_settings.name
            if src_cs:
                temp.colorspace_settings.name = src_cs
        except Exception:
            pass
        try:
            temp.alpha_mode = image.alpha_mode
        except Exception:
            pass

        count = w * h * 4
        buf = array("f", [0.0]) * count
        image.pixels.foreach_get(buf)
        temp.pixels.foreach_set(buf)
        temp.update()
        return temp
    except Exception:
        try:
            bpy.data.images.remove(temp)
        except Exception:
            pass
        raise


def _native_save_png_via_blender(context, image, output_png, preferred_context=None):
    """只使用 Blender 自己的图像保存器生成 PNG。

    DDS 路径不会自己改颜色、Gamma、DDS Header 或 PNG 字节。唯一的工作是：
    将当前 Blender Image 的像素原样放进一个临时 Blender Image，然后调用
    Blender 原生 Save As；如果 operator context 无法通过 poll，则使用同一个
    临时 Image 的原生 Image.save 作为兜底。之后这个临时 Image 立即删除。
    """
    if not output_png:
        return False, "中间 PNG 路径为空"

    output_png = bpy.path.abspath(output_png)
    os.makedirs(os.path.dirname(output_png) or ".", exist_ok=True)
    _safe_remove(output_png)

    temp = None
    try:
        temp = _new_native_png_image(image)
        ctx_info = _find_image_editor_context(
            context, image=image, preferred=preferred_context
        )

        operator_error = None
        if ctx_info is not None:
            window, screen, area, region, space = ctx_info
            old_image = getattr(space, "image", None)
            try:
                space.image = temp
                kwargs = dict(
                    save_as_render=False,
                    copy=True,
                    allow_path_tokens=False,
                    filepath=output_png,
                    check_existing=False,
                    relative_path=False,
                )
                base = {"window": window, "area": area}
                if screen is not None:
                    base["screen"] = screen
                variants = [
                    dict(base, region=region, space_data=space),
                    dict(base, region=region),
                    dict(base, space_data=space),
                    dict(base),
                ]
                for variant in variants:
                    try:
                        with bpy.context.temp_override(**variant):
                            if not bpy.ops.image.save_as.poll():
                                operator_error = "poll=False"
                                continue
                            result = bpy.ops.image.save_as("EXEC_DEFAULT", **kwargs)
                        if os.path.isfile(output_png) and os.path.getsize(output_png) > 0:
                            with open(output_png, "rb") as fh:
                                if fh.read(8) == b"\x89PNG\r\n\x1a\n":
                                    print(
                                        f"[DDS Save] native PNG: {output_png} "
                                        f"(Blender IMAGE_OT_save_as)"
                                    )
                                    return True, f"中间 PNG 已由 Blender 原生 Save As 保存: {output_png}"
                            operator_error = f"operator={result!r}, invalid PNG"
                        else:
                            operator_error = f"operator={result!r}, no PNG"
                    except Exception as exc:
                        operator_error = str(exc)
            finally:
                try:
                    space.image = old_image
                except Exception:
                    pass

        # 不再复制/重编码原图。这里仍然是 Blender 原生 Image.save，且 temp 已经
        # 拥有明确像素缓冲与 PNG file_format，不会得到 GENERATED 空白图。
        try:
            temp.filepath_raw = output_png
            result = temp.save(filepath=output_png, save_copy=True)
            if os.path.isfile(output_png) and os.path.getsize(output_png) > 0:
                with open(output_png, "rb") as fh:
                    if fh.read(8) == b"\x89PNG\r\n\x1a\n":
                        print(
                            f"[DDS Save] native PNG: {output_png} "
                            f"(Blender Image.save fallback)"
                        )
                        return True, f"中间 PNG 已由 Blender 原生 Image.save 保存: {output_png}"
            return False, (
                "Blender 原生 PNG 保存失败 "
                f"(save_as={operator_error!r}, fallback={result!r})"
            )
        except Exception as exc:
            return False, (
                "Blender 原生 PNG 保存失败 "
                f"(save_as={operator_error!r}, fallback={exc})"
            )
    finally:
        if temp is not None:
            try:
                bpy.data.images.remove(temp)
            except Exception:
                pass


def _dds_save_core(context, image, output_dds, dds_format="BC7_UNORM_SRGB",
                    srgb_input=False, bc_quality="max", mip_enabled=False,
                    mip_filter="FANT", use_gpu=True, singleproc=False,
                    gpu_adapter=None, force_reencode=False, preferred_context=None,
                    bc_weighting="perceptual", bc_dither=False,
                    alpha_threshold=0.5, coverage_ref=0.5, alpha_weight=1.0,
                    separate_alpha=False, keep_coverage=False,
                    alpha_mode="KEEP"):

    if not output_dds:
        return False, "输出路径为空"
    output_dds = bpy.path.abspath(output_dds)
    if not output_dds:
        return False, "输出路径为空"

    if _looks_like_temp_path(output_dds):
        return False, ("输出路径指向插件的临时文件，已拒绝。"
                       "请在「另存为…」中重新指定路径。")

    prefs = _get_prefs(context)
    texconv_path = prefs.texconv_path.strip() or None

    if gpu_adapter is None:
        gpu_adapter = _get_gpu_index(prefs.gpu_adapter)
    elif isinstance(gpu_adapter, str):
        gpu_adapter = _get_gpu_index(gpu_adapter)

    mgr = TexconvManager(texconv_path)
    if not mgr.available:
        return False, "texconv.exe 未找到！请在插件偏好设置中配置路径。"

    out_dir = os.path.dirname(output_dds) or "."
    os.makedirs(out_dir, exist_ok=True)

    try:
        orig_filepath = image.filepath_raw
    except Exception:
        orig_filepath = None
    try:
        orig_colorspace = image.colorspace_settings.name
    except Exception:
        orig_colorspace = None

    # 不读取 DDS 源头颜色空间，也不做手写 gamma 往返。
    # DDS 的唯一图像输入就是 Blender 当前已经正确解释后的 Image buffer；
    # 中间 PNG 完全交给 Blender 原生 Save As 生成。
    target_is_srgb = _dds_format_is_srgb(dds_format)
    output_abs = os.path.normcase(os.path.abspath(output_dds))

    # 直接判断当前输出是否就是本插件上一轮生成、且文件状态/参数没有变化。
    # 这项判断与 Blender 的 Texture Auto Reload 独立，解决紧接着第二次保存
    # 又进行一次有损 BC7 压缩的问题。
    try:
        sig = _DDS_SAVE_SIGNATURES.get(output_abs)
        if not sig:
            sig = image.get("_dds_save_signature")
        if (not force_reencode and sig
                and sig.get("pipeline_version") == 3
                and not bool(getattr(image, "is_dirty", False))
                and sig.get("dds_format") == dds_format
                and bool(sig.get("mip_enabled")) == bool(mip_enabled)
                and sig.get("mip_filter") == mip_filter
                and sig.get("bc_quality") == bc_quality
                and sig.get("bc_weighting") == bc_weighting
                and bool(sig.get("bc_dither")) == bool(bc_dither)
                and abs(float(sig.get("alpha_threshold", 0.5)) - float(alpha_threshold)) < 1e-9
                and abs(float(sig.get("coverage_ref", 0.5)) - float(coverage_ref)) < 1e-9
                and abs(float(sig.get("alpha_weight", 1.0)) - float(alpha_weight)) < 1e-9
                and bool(sig.get("separate_alpha")) == bool(separate_alpha)
                and bool(sig.get("keep_coverage")) == bool(keep_coverage)
                and sig.get("alpha_mode") == alpha_mode
                and bool(sig.get("use_gpu")) == bool(use_gpu)
                and int(sig.get("gpu_adapter", -1)) == int(gpu_adapter)
                and bool(sig.get("singleproc")) == bool(singleproc)
                and os.path.isfile(output_dds)):
            st = os.stat(output_dds)
            if (int(sig.get("file_size", -1)) == int(st.st_size)
                    and int(sig.get("file_mtime_ns", -1)) == int(st.st_mtime_ns)):
                try:
                    print("[DDS Save] unchanged output + identical parameters: "
                          "skip lossy DDS recompression")
                except Exception:
                    pass
                return True, f"已保存: {output_dds}（内容未修改，跳过重复 BC 压缩）"
    except Exception:
        pass

    token = f"{os.getpid()}_{int(time.time() * 1000) & 0xFFFFFF:x}_{id(image) & 0xFFFF:x}"
    tmp_stem = os.path.join(out_dir, f"{_TMP_MARK}{token}")
    tmp_png_path = tmp_stem + ".png"
    tmp_dds_path = tmp_stem + ".dds"

    try:
        try:
            print(f"[DDS Save] image={image.name!r}, colorspace={orig_colorspace!r}, "
                  f"input=Blender native PNG, target={dds_format}")
        except Exception:
            pass

        # ★ 唯一的中间格式步骤：直接调用 Blender 原生 Save As Image。
        # 不碰原 DDS 的 file_format，不自行做 gamma，也不解析源 DDS 颜色空间。
        ok_png, png_msg = _native_save_png_via_blender(
            context, image, tmp_png_path, preferred_context=preferred_context
        )
        if not ok_png:
            _safe_remove(tmp_png_path)
            return False, png_msg

        # 纯转码：不主动执行 sRGB<->Linear 转换。
        # SRGB 目标：保留 Blender PNG 的 sRGB 元数据，不带 --ignore-srgb。
        # Linear 目标：使用 --ignore-srgb，使 PNG 的 sRGB 元数据不会改变
        # 非-SRGB DDS 的数值映射。其余 UI 参数分别映射到 -f/-m/-if/-bc/-gpu/-nogpu/-singleproc。
        success, msg = mgr.convert(
            input_png=tmp_png_path, output_dds=tmp_dds_path,
            dds_format=dds_format, mip_enabled=mip_enabled,
            mip_filter=mip_filter, srgb_input=False, srgb_output=False,
            bc_quality=bc_quality, use_gpu=use_gpu,
            gpu_adapter=gpu_adapter, singleproc=singleproc,
            ignore_srgb_metadata=None,
            bc_weighting=bc_weighting, bc_dither=bc_dither,
            alpha_threshold=alpha_threshold, coverage_ref=coverage_ref,
            alpha_weight=alpha_weight, separate_alpha=separate_alpha,
            keep_coverage=keep_coverage, alpha_mode=alpha_mode,
        )
        if not success:
            _safe_remove(tmp_dds_path)
            return False, msg

        if not os.path.isfile(tmp_dds_path):
            return False, "texconv 未生成预期输出文件"

        os.replace(tmp_dds_path, output_dds)

        try:
            st = os.stat(output_dds)
            sig = {
                "pipeline_version": 3,
                "dds_format": dds_format,
                "mip_enabled": bool(mip_enabled),
                "mip_filter": mip_filter,
                "bc_quality": bc_quality,
                "bc_weighting": bc_weighting,
                "bc_dither": bool(bc_dither),
                "alpha_threshold": float(alpha_threshold),
                "coverage_ref": float(coverage_ref),
                "alpha_weight": float(alpha_weight),
                "separate_alpha": bool(separate_alpha),
                "keep_coverage": bool(keep_coverage),
                "alpha_mode": alpha_mode,
                "use_gpu": bool(use_gpu),
                "gpu_adapter": int(gpu_adapter),
                "singleproc": bool(singleproc),
                "file_size": int(st.st_size),
                "file_mtime_ns": int(st.st_mtime_ns),
            }
            _DDS_SAVE_SIGNATURES[output_abs] = dict(sig)
            image["_dds_save_signature"] = dict(sig)
        except Exception:
            pass

        return True, (f"保存成功: {output_dds}  "
                      f"[Blender PNG -> {'SRGB' if target_is_srgb else 'Linear'}]")
    except Exception as e:
        _safe_remove(tmp_dds_path)
        return False, f"DDS 保存异常: {e}"
    finally:
        try:
            image.filepath_raw = orig_filepath
        except Exception:
            pass
        _safe_remove(tmp_png_path)
        _safe_remove(tmp_dds_path)


# ============================================================================
# 抽取的公共 UI 绘制逻辑与保存逻辑
# ============================================================================

def _dds_has_alpha(dds_format):
    return str(dds_format).upper() in {
        "BC1_UNORM", "BC1_UNORM_SRGB",
        "BC3_UNORM", "BC3_UNORM_SRGB",
        "BC7_UNORM", "BC7_UNORM_SRGB",
        "R8G8B8A8_UNORM", "R8G8B8A8_UNORM_SRGB",
    }


def draw_save_params_ui(op, layout):
    """只显示当前格式真正适用的保存参数，不显示说明性文字或无效灰色项。"""
    layout.use_property_split = True
    layout.use_property_decorate = False
    fmt = op.export_format

    layout.prop(op, "export_format")

    if fmt == "DDS":
        dds = str(op.dds_format).upper()
        layout.prop(op, "dds_format")

        # 编码器专属参数：只显示当前 DDS 格式支持的参数。
        if _dds_is_bc7(dds):
            layout.prop(op, "bc_quality")
            layout.prop(op, "alpha_weight")
            layout.prop(op, "use_gpu")
            if bool(op.use_gpu):
                layout.prop(op, "gpu_adapter")
            else:
                layout.prop(op, "singleproc")
        elif _dds_is_bc1_3(dds):
            layout.prop(op, "bc_weighting")
            layout.prop(op, "bc_dither")
            if dds in {"BC1_UNORM", "BC1_UNORM_SRGB"}:
                layout.prop(op, "alpha_threshold")

        # 通用 DDS 参数。
        layout.prop(op, "mip_enabled")
        if bool(op.mip_enabled):
            layout.prop(op, "mip_filter")
            if _dds_has_alpha(dds):
                layout.prop(op, "separate_alpha")
            if _dds_is_bc1_3(dds):
                layout.prop(op, "keep_coverage")
                if bool(op.keep_coverage):
                    layout.prop(op, "coverage_ref")

        # 只有带 Alpha 的 DDS 才显示 Alpha 处理。
        if _dds_has_alpha(dds):
            layout.prop(op, "alpha_mode")
        return

    layout.prop(op, "color_mode")

    if fmt == "OPEN_EXR":
        layout.prop(op, "color_depth_float")
        layout.prop(op, "exr_codec")
    elif fmt == "PNG":
        layout.prop(op, "color_depth_int")
        layout.prop(op, "png_compression")
    elif fmt in {"JPEG", "WEBP", "AVIF"}:
        layout.prop(op, "quality")
    elif fmt == "TIFF":
        layout.prop(op, "color_depth_int")
        layout.prop(op, "tiff_codec")
    elif fmt in {"JPEG2000", "CINEON", "DPX", "HDR", "IRIS", "TARGA", "BMP"}:
        layout.prop(op, "color_depth_int")
    layout.prop(op, "colorspace")


def execute_save_logic(op, context, out_path):
    image = _active_image(context)
    if image is None:
        return False, "没有活动图片"

    if _looks_like_temp_path(out_path):
        return False, ("输出路径指向插件的临时文件，已拒绝。"
                       "当前图片的保存路径可能已被污染，"
                       "请用「另存为…」重新指定一个正式路径。")

    fmt = op.export_format
    if fmt not in EXPORT_EXTENSIONS:
        return False, f"暂不支持的格式: {fmt}"

    if fmt == "DDS":
        return _dds_save_core(
            context, image, out_path,
            dds_format=op.dds_format, srgb_input=False,
            bc_quality=op.bc_quality, mip_enabled=op.mip_enabled,
            mip_filter=op.mip_filter, use_gpu=op.use_gpu,
            gpu_adapter=op.gpu_adapter, singleproc=op.singleproc,
            bc_weighting=op.bc_weighting, bc_dither=op.bc_dither,
            alpha_threshold=op.alpha_threshold, coverage_ref=op.coverage_ref,
            alpha_weight=op.alpha_weight, separate_alpha=op.separate_alpha,
            keep_coverage=op.keep_coverage, alpha_mode=op.alpha_mode,
            force_reencode=getattr(op, "_dds_force_reencode", False),
            preferred_context=getattr(op, "_dds_ui_context", None),
        )

    orig_filepath = image.filepath_raw
    orig_colorspace = image.colorspace_settings.name
    # 不直接读取 image.file_format：已载入 DDS 在部分 Blender 版本中可能是无效枚举。
    orig_format = None
    try:
        ext = os.path.splitext(orig_filepath or "")[1].lower()
        for known_fmt, known_ext in EXPORT_EXTENSIONS.items():
            if ext == known_ext:
                orig_format = known_fmt
                break
    except Exception:
        pass
    try:
        if op.colorspace and orig_colorspace != op.colorspace:
            try:
                image.colorspace_settings.name = op.colorspace
            except Exception:
                pass

        if fmt == "PNG":
            write_png(out_path, image, color_mode=op.color_mode,
                      bit_depth=int(op.color_depth_int), compression=op.png_compression,
                      colorspace=op.colorspace or "sRGB")
        elif fmt in {"JPEG", "WEBP", "AVIF"}:
            image.file_format = fmt
            image.filepath_raw = out_path
            image.save(quality=op.quality)
        else:
            depth = (op.color_depth_float if fmt == "OPEN_EXR" else op.color_depth_int)
            _save_with_render_settings(
                image, out_path, fmt, color_mode=op.color_mode,
                color_depth=depth, exr_codec=op.exr_codec, tiff_codec=op.tiff_codec,
            )
        return True, f"已保存: {out_path}"
    except Exception as e:
        return False, f"保存失败: {e}"
    finally:
        try:
            image.file_format = orig_format
        except Exception:
            pass
        try:
            image.filepath_raw = orig_filepath
        except Exception:
            pass
        try:
            if image.colorspace_settings.name != orig_colorspace:
                image.colorspace_settings.name = orig_colorspace
        except Exception:
            pass


# ============================================================================
# 刷新 GPU 列表
# ============================================================================

class WM_DDS_refresh_gpus(Operator):
    """重新检测系统中的 GPU 硬件"""
    bl_idname = "wm.dds_refresh_gpus"
    bl_label = "刷新 GPU 列表"

    def execute(self, context):
        _refresh_gpu_cache()
        self.report({"INFO"}, f"检测到 {len(_gpu_cache)} 个 GPU")
        p = _get_prefs(context)
        current_ident = p.gpu_adapter
        valid_idents = [ident for ident, _, _ in _gpu_cache]
        if current_ident not in valid_idents:
            p.gpu_adapter = valid_idents[0] if valid_idents else "0"
        return {"FINISHED"}


def _active_image(context):
    sd = getattr(context, "space_data", None)
    img = getattr(sd, "image", None) if sd is not None else None
    if img is not None:
        return img
    for attr in ("edit_image", "image"):
        img = getattr(context, attr, None)
        if img is not None:
            return img
    wm = getattr(context, "window_manager", None)
    for window in getattr(wm, "windows", []) or []:
        for area in getattr(window.screen, "areas", []) or []:
            if area.type == "IMAGE_EDITOR":
                img = getattr(area.spaces.active, "image", None)
                if img is not None:
                    return img
    return None


# ============================================================================
# 参数属性定义
# ============================================================================
class SaveParamsMixin:
    """定义所有保存参数，方便在多个操作符中复用"""
    export_format: EnumProperty(name="格式", items=EXPORT_FILE_FORMATS, default="DDS")
    color_mode: EnumProperty(name="颜色", items=[("BW", "BW", ""), ("RGB", "RGB", ""), ("RGBA", "RGBA", "")], default="RGBA")
    color_depth_int: EnumProperty(name="色深", items=[("8", "8", ""), ("16", "16", "")], default="8")
    color_depth_float: EnumProperty(name="色深", items=[("16", "16", ""), ("32", "32", "")], default="16")
    colorspace: EnumProperty(name="色彩空间", items=[("sRGB", "sRGB", ""), ("Non-Color", "Non-Color", ""), ("Linear", "Linear", "")], default="sRGB")
    quality: IntProperty(name="质量", default=90, min=0, max=100, subtype="PERCENTAGE")
    png_compression: IntProperty(name="压缩", default=15, min=0, max=100, subtype="PERCENTAGE")
    exr_codec: EnumProperty(name="压缩方式", items=[("NONE", "None", ""), ("ZIP", "ZIP", ""), ("PIZ", "PIZ", ""), ("RLE", "RLE", ""), ("DWAA", "DWAA", ""), ("DWAB", "DWAB", "")], default="ZIP")
    tiff_codec: EnumProperty(name="压缩", items=[("NONE", "None", ""), ("LZW", "LZW", ""), ("DEFLATE", "Deflate", ""), ("PACKBITS", "PackBits", "")], default="LZW")
    dds_format: EnumProperty(name="DDS 格式", items=DDS_FORMATS, default="BC7_UNORM_SRGB")

    # 兼容旧版文件/脚本的隐藏属性。DDS 保存完全不读取它。
    srgb_input: BoolProperty(
        name="旧版 sRGB 输入（已弃用）",
        description="仅为兼容旧版配置保留。DDS 保存时会按目标 DDS 格式自动处理色彩空间。",
        default=False,
        options={'HIDDEN'},
    )
    bc_quality: EnumProperty(name="BC7 压缩质量", items=[("quick", "快速", "仅模式 6"), ("standard", "标准", "texconv 默认"), ("max", "最高", "启用更完整模式")], default="max")
    bc_weighting: EnumProperty(name="BC1-3 权重", items=[("perceptual", "感知权重", "texconv 默认的人眼感知权重"), ("uniform", "统一权重", "-bc u")], default="perceptual")
    bc_dither: BoolProperty(name="BC1-3 抖动", description="对 BC1-3 启用抖动（-bc d）", default=False)
    alpha_threshold: bpy.props.FloatProperty(name="Alpha 阈值", description="BC1 1-bit Alpha 阈值（-at）", default=0.5, min=0.0, max=1.0, subtype="FACTOR")
    coverage_ref: bpy.props.FloatProperty(name="Coverage 参考值", description="生成 Mipmap 时 Alpha Coverage 参考值（-keepcoverage）", default=0.5, min=0.0, max=1.0, subtype="FACTOR")
    alpha_weight: bpy.props.FloatProperty(name="BC7 Alpha 权重", description="BC7 GPU 编码的 Alpha 误差权重（-aw）", default=1.0, min=0.0, max=100.0)
    separate_alpha: BoolProperty(name="独立处理 Alpha", description="生成/过滤 Mipmap 时单独处理 Alpha（-sepalpha）", default=False)
    keep_coverage: BoolProperty(name="保持 Alpha 覆盖率", description="生成 Mipmap 时保持 Alpha 覆盖率（-keepcoverage）", default=False)
    alpha_mode: EnumProperty(name="Alpha 处理", items=[("KEEP", "保持原样", "不对 Alpha 做额外变换"), ("PREMLTIPLIED", "预乘 Alpha", "-pmalpha"), ("STRAIGHT", "直通 Alpha", "-alpha")], default="KEEP")
    mip_enabled: BoolProperty(name="生成 Mipmap", default=False)
    mip_filter: EnumProperty(name="Mip 过滤", items=MIP_FILTERS, default="FANT")
    use_gpu: BoolProperty(name="GPU 加速", default=True)
    gpu_adapter: EnumProperty(name="GPU 适配器", items=_get_gpu_items)
    singleproc: BoolProperty(name="单线程模式", default=False)


# ============================================================================
# 统一保存操作符
# ============================================================================

class IMAGE_OT_save_current(Operator, SaveParamsMixin):
    """保存当前图片——弹出参数窗口，每张贴图独立记忆"""
    bl_idname = "image.save_current"
    bl_label = "保存"
    bl_description = "保存当前图片（弹出参数设置，每张贴图独立记忆）"
    bl_options = {'PRESET'}

    @classmethod
    def poll(cls, context):
        return _active_image(context) is not None

    def invoke(self, context, event):
        image = _active_image(context)
        if image is None:
            self.report({"ERROR"}, "没有可保存的图像")
            return {"CANCELLED"}

        fp = image.filepath
        if not fp:
            self.report({"ERROR"}, "图片暂无文件路径，请使用「另存为…」")
            return {"CANCELLED"}

        if _looks_like_temp_path(fp):
            self.report({"ERROR"},
                        "该图片的保存路径已被插件的临时文件占用，"
                        "请用「另存为…」重新指定正式路径后再保存。")
            return {"CANCELLED"}

        ext = os.path.splitext(fp)[1].lower()
        fmt = None
        for k, v in EXPORT_EXTENSIONS.items():
            if v == ext:
                fmt = k
                break

        if not fmt:
            try:
                image.save()
                self.report({"INFO"}, f"已保存: {fp}")
            except Exception as e:
                self.report({"ERROR"}, f"保存失败: {e}")
            return {"CANCELLED"}

        # “保存”只能按当前文件扩展名决定格式，避免旧缓存把 .png
        # 路径错误地当成 DDS（或反之）保存。
        self.export_format = fmt

        prefs = _get_prefs(context)
        self.use_gpu = prefs.use_gpu
        self.gpu_adapter = prefs.gpu_adapter
        self.singleproc = prefs.singleproc

        # 恢复除 export_format / srgb_input 外的当前贴图参数。
        saved_params = image.get("_save_params", {})
        for key in saved_params:
            if key in {"export_format", "srgb_input"}:
                continue
            if hasattr(self, key):
                try:
                    setattr(self, key, saved_params[key])
                except Exception:
                    pass

        # 再次确保格式与实际保存路径一致。
        self.export_format = fmt

        # 参数弹窗会改变当前 operator context；保存原始 IMAGE_EDITOR 上下文。
        self._dds_ui_context = _capture_image_editor_context(context, image)

        return context.window_manager.invoke_props_dialog(self, width=380)

    def cancel(self, context):
        """取消回调。

        注意：Blender 的 Operator.cancel 返回值必须为 None，
        不能返回 {"CANCELLED"}，否则会抛
        "expected class X, function cancel to return None" 并让对话框残留。
        """
        try:
            self._dds_ui_context = None
        except Exception:
            pass
        return None

    def draw(self, context):
        try:
            draw_save_params_ui(self, self.layout)
        except Exception as exc:
            try:
                print(f"[DDS Save] save_current draw error: {exc!r}")
            except Exception:
                pass

    def execute(self, context):
        image = _active_image(context)
        fp = image.filepath
        if not fp:
            self.report({"ERROR"}, "图片暂无文件路径，请使用「另存为…」")
            return {"CANCELLED"}
        if _looks_like_temp_path(fp):
            self.report({"ERROR"},
                        "该图片的保存路径已被插件的临时文件占用，"
                        "请用「另存为…」重新指定正式路径。")
            return {"CANCELLED"}

        params_to_save = {}
        for key in ["export_format", "color_mode", "color_depth_int", "color_depth_float",
                    "colorspace", "quality", "png_compression", "exr_codec", "tiff_codec",
                    "dds_format", "bc_quality", "bc_weighting", "bc_dither",
                    "alpha_threshold", "coverage_ref", "alpha_weight",
                    "separate_alpha", "keep_coverage",
                    "alpha_mode", "mip_enabled", "mip_filter",
                    "use_gpu", "gpu_adapter", "singleproc"]:
            if hasattr(self, key):
                params_to_save[key] = getattr(self, key)
        image["_save_params"] = params_to_save

        success, msg = execute_save_logic(self, context, fp)
        if success:
            # “保存”语义上等同于原生保存：成功后清除 is_dirty。
            # DDS 路径由 texconv 出图，Blender 不会自动清脏，这里借一次
            # 临时原生保存触发清脏（临时 PNG 会立即被删除）。
            _clear_image_dirty_via_native_save(image)
        self.report({"INFO"} if success else {"ERROR"}, msg)
        return {"FINISHED"} if success else {"CANCELLED"}


# ============================================================================
# 另存为操作符
# ============================================================================

class IMAGE_OT_save_dds(Operator, ExportHelper, SaveParamsMixin):
    """将当前图片另存为指定格式（DDS 由 texconv 压缩）"""
    bl_idname = "image.save_dds"
    bl_label = "另存为…"
    bl_description = "将当前图片另存为 DDS 或 Blender 原生格式"

    filename_ext = ".dds"
    filter_glob: StringProperty(default="*", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _active_image(context) is not None

    def draw(self, context):
        # 防御：draw 中任何异常都不能让文件浏览器在取消时残留窗口。
        try:
            draw_save_params_ui(self, self.layout)
        except Exception as exc:
            try:
                print(f"[DDS Save] save_dds draw error: {exc!r}")
            except Exception:
                pass
            try:
                self.layout.label(text="参数面板绘制异常，详见控制台")
            except Exception:
                pass

    def cancel(self, context):
        """取消回调。

        注意：Blender 的 Operator.cancel 返回值必须为 None，
        不能返回 {"CANCELLED"}。之前返回 set 会抛
        "expected class IMAGE_OT_save_dds, function cancel to return None, not set"，
        导致文件浏览器的取消收尾流程中断，留下半关的窗口外壳。
        """
        try:
            self._dds_ui_context = None
        except Exception:
            pass
        try:
            self._dds_force_reencode = False
        except Exception:
            pass
        return None

    def _with_format_ext(self, filepath):
        if not filepath:
            return filepath
        want = _format_ext(self.export_format)
        base = os.path.splitext(filepath)[0]
        if not base:
            return filepath
        if os.path.splitext(filepath)[1].lower() == want:
            return filepath
        return base + want

    def check(self, context):
        # 防御：取消收尾那一帧 check() 仍可能被调用，异常会触发
        # "只移除插件 UI、留下文件浏览器窗口"的残留 bug。
        try:
            if not self.filepath:
                return False
            new_path = self._with_format_ext(self.filepath)
        except Exception:
            return False
        if new_path != self.filepath:
            try:
                self.filepath = new_path
            except Exception:
                return False
            return True
        return False

    def execute(self, context):
        out = self._with_format_ext(self.filepath)
        self._dds_force_reencode = False
        success, msg = execute_save_logic(self, context, out)
        self.report({"INFO"} if success else {"ERROR"}, msg)
        return {"FINISHED"} if success else {"CANCELLED"}

    def invoke(self, context, event):
        image = _active_image(context)
        self.export_format = "DDS"
        self.quality = 90

        # 有明确当前扩展名时，另存为默认跟随当前格式。
        if image and image.filepath and not _looks_like_temp_path(image.filepath):
            ext = os.path.splitext(image.filepath)[1].lower()
            for fmt, known_ext in EXPORT_EXTENSIONS.items():
                if ext == known_ext:
                    self.export_format = fmt
                    break

        prefs = _get_prefs(context)
        self.use_gpu = prefs.use_gpu
        self.gpu_adapter = prefs.gpu_adapter
        self.singleproc = prefs.singleproc

        # “另存为…”恢复当前贴图最近一次参数；旧版 srgb_input 不恢复。
        saved_params = image.get("_save_params", {}) if image else {}
        for key, value in saved_params.items():
            if key == "srgb_input":
                continue
            if hasattr(self, key):
                try:
                    setattr(self, key, value)
                except Exception:
                    pass

        if image and image.filepath and not _looks_like_temp_path(image.filepath):
            base = os.path.splitext(os.path.basename(image.filepath))[0]
            self.filepath = base + _format_ext(self.export_format)

        # 参数弹窗会改变当前 operator context；保存原始 IMAGE_EDITOR 上下文。
        self._dds_ui_context = _capture_image_editor_context(context, image)

        try:
            return super().invoke(context, event)
        except Exception as exc:
            # 启动文件浏览器失败时直接返回 CANCELLED，避免半初始化状态。
            self.report({"ERROR"}, f"另存为对话框启动失败: {exc}")
            return {"CANCELLED"}


# ============================================================================
# 保存为副本操作符
# ============================================================================
# 说明：本类为「另存为…」的独立平行实现，不复用/继承 IMAGE_OT_save_dds，
# 避免 Blender RNA 注册时因父子类关系导致父类 poll 变灰的问题。
# 逻辑与「另存为…」完全一致：弹出文件浏览器 → 用户选路径 → 走同一条
# execute_save_logic 保存。区别只有 idname / label / description。

class IMAGE_OT_save_dds_copy(Operator, ExportHelper, SaveParamsMixin):
    """将当前图片保存为副本到指定位置（不改变当前图像的保存路径）"""
    bl_idname = "image.save_dds_copy"
    bl_label = "保存副本…"
    bl_description = "将当前图片保存为副本到指定位置（DDS 由 texconv 压缩）"

    filename_ext = ".dds"
    filter_glob: StringProperty(default="*", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _active_image(context) is not None

    def draw(self, context):
        try:
            draw_save_params_ui(self, self.layout)
        except Exception as exc:
            try:
                print(f"[DDS Save] save_dds_copy draw error: {exc!r}")
            except Exception:
                pass
            try:
                self.layout.label(text="参数面板绘制异常，详见控制台")
            except Exception:
                pass

    def cancel(self, context):
        """取消回调。返回值必须为 None，理由同 IMAGE_OT_save_dds.cancel。"""
        try:
            self._dds_ui_context = None
        except Exception:
            pass
        try:
            self._dds_force_reencode = False
        except Exception:
            pass
        return None

    def _with_format_ext(self, filepath):
        if not filepath:
            return filepath
        want = _format_ext(self.export_format)
        base = os.path.splitext(filepath)[0]
        if not base:
            return filepath
        if os.path.splitext(filepath)[1].lower() == want:
            return filepath
        return base + want

    def check(self, context):
        try:
            if not self.filepath:
                return False
            new_path = self._with_format_ext(self.filepath)
        except Exception:
            return False
        if new_path != self.filepath:
            try:
                self.filepath = new_path
            except Exception:
                return False
            return True
        return False

    def execute(self, context):
        out = self._with_format_ext(self.filepath)
        self._dds_force_reencode = False
        success, msg = execute_save_logic(self, context, out)
        self.report({"INFO"} if success else {"ERROR"}, msg)
        return {"FINISHED"} if success else {"CANCELLED"}

    def invoke(self, context, event):
        image = _active_image(context)
        self.export_format = "DDS"
        self.quality = 90

        # 有明确当前扩展名时，副本默认跟随当前格式。
        if image and image.filepath and not _looks_like_temp_path(image.filepath):
            ext = os.path.splitext(image.filepath)[1].lower()
            for fmt, known_ext in EXPORT_EXTENSIONS.items():
                if ext == known_ext:
                    self.export_format = fmt
                    break

        prefs = _get_prefs(context)
        self.use_gpu = prefs.use_gpu
        self.gpu_adapter = prefs.gpu_adapter
        self.singleproc = prefs.singleproc

        # 恢复当前贴图最近一次参数；旧版 srgb_input 不恢复。
        saved_params = image.get("_save_params", {}) if image else {}
        for key, value in saved_params.items():
            if key == "srgb_input":
                continue
            if hasattr(self, key):
                try:
                    setattr(self, key, value)
                except Exception:
                    pass

        # 保存为副本默认文件名：原文件名 + "_copy" + 扩展名。
        if image and image.filepath and not _looks_like_temp_path(image.filepath):
            base = os.path.splitext(os.path.basename(image.filepath))[0]
            self.filepath = base + "_copy" + _format_ext(self.export_format)

        # 参数弹窗会改变当前 operator context；保存原始 IMAGE_EDITOR 上下文。
        self._dds_ui_context = _capture_image_editor_context(context, image)

        try:
            return super().invoke(context, event)
        except Exception as exc:
            self.report({"ERROR"}, f"保存副本对话框启动失败: {exc}")
            return {"CANCELLED"}


# ============================================================================
# 保存所有已修改图像（替换原生 image.save_all_modified）
# ============================================================================
# 说明：Blender 原生 image.save_all_modified 遇到 .dds 的已修改图像会走
# 原生 IMAGE_OT_save 路径，Blender 无法写 DDS 字节流 → 报
# "无法写入图像: internal error"。本操作符完全替换该菜单项：
#   * 有文件路径、且扩展名是插件支持格式的已修改图像：
#       - .dds → 走插件的 _dds_save_core（复用该图缓存的上次保存参数）
#       - 其余 → 走 Blender 原生 image.save()
#   * 无文件路径 / 临时路径的图像被跳过（与原生行为一致）。
# 不改变任何保存机制，只是替换菜单项。

class IMAGE_OT_save_all_modified(Operator):
    """保存所有已修改的图像（DDS 走 texconv，其余走 Blender 原生）"""
    bl_idname = "image.save_all_modified_custom"
    bl_label = "Save All Images"
    bl_description = "保存所有已修改的图像（DDS 由 texconv 压缩）"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        for img in bpy.data.images:
            try:
                if img.is_dirty and img.filepath and not _looks_like_temp_path(img.filepath):
                    return True
            except Exception:
                continue
        return False

    def execute(self, context):
        prefs = _get_prefs(context)
        saved = 0
        failed = 0
        skipped = 0
        errors = []

        # 复制一份列表，因为保存过程中可能触发图像数据块变化。
        for image in list(bpy.data.images):
            try:
                if not image.is_dirty:
                    continue
                fp = image.filepath
                if not fp or _looks_like_temp_path(fp):
                    skipped += 1
                    continue

                ext = os.path.splitext(fp)[1].lower()
                fmt = None
                for k, v in EXPORT_EXTENSIONS.items():
                    if v == ext:
                        fmt = k
                        break

                if fmt == "DDS":
                    sp = dict(image.get("_save_params", {}) or {})
                    ok, msg = _dds_save_core(
                        context, image, fp,
                        dds_format=sp.get("dds_format", "BC7_UNORM_SRGB"),
                        srgb_input=False,
                        bc_quality=sp.get("bc_quality", "max"),
                        mip_enabled=bool(sp.get("mip_enabled", False)),
                        mip_filter=sp.get("mip_filter", "FANT"),
                        use_gpu=bool(sp.get("use_gpu", prefs.use_gpu)),
                        gpu_adapter=sp.get("gpu_adapter") or prefs.gpu_adapter,
                        singleproc=bool(sp.get("singleproc", prefs.singleproc)),
                        bc_weighting=sp.get("bc_weighting", "perceptual"),
                        bc_dither=bool(sp.get("bc_dither", False)),
                        alpha_threshold=float(sp.get("alpha_threshold", 0.5)),
                        coverage_ref=float(sp.get("coverage_ref", 0.5)),
                        alpha_weight=float(sp.get("alpha_weight", 1.0)),
                        separate_alpha=bool(sp.get("separate_alpha", False)),
                        keep_coverage=bool(sp.get("keep_coverage", False)),
                        alpha_mode=sp.get("alpha_mode", "KEEP"),
                    )
                    if ok:
                        saved += 1
                        # DDS 由 texconv 出图，Blender 不会自动清脏；借一次
                        # 临时原生保存触发清脏（临时 PNG 会立即被删除）。
                        _clear_image_dirty_via_native_save(image)
                    else:
                        failed += 1
                        errors.append(f"{image.name}: {msg}")
                else:
                    # 非 DDS：交给 Blender 原生保存（PNG/JPEG/WEBP/EXR/TIFF...）。
                    try:
                        image.save()
                        saved += 1
                    except Exception as e:
                        failed += 1
                        errors.append(f"{image.name}: {e}")
            except Exception as e:
                failed += 1
                errors.append(f"{image.name}: {e}")

        if failed == 0:
            msg = f"已保存 {saved} 张图像"
            if skipped:
                msg += f"，跳过 {skipped} 张（无路径/临时路径）"
            self.report({"INFO"}, msg)
        else:
            msg = f"已保存 {saved} 张，失败 {failed} 张"
            if skipped:
                msg += f"，跳过 {skipped} 张"
            self.report({"WARNING"}, msg)
            for e in errors[:5]:
                print(f"[DDS Save] save_all error: {e}")

        return {"FINISHED"} if failed == 0 else {"CANCELLED"}


# ============================================================================
# 快捷键接管：Save / Save As 使用原生快捷键
# ============================================================================
# 原生 Blender 在 Image Editor 中把 Alt+S / Shift+Alt+S 绑到
# image.save / image.save_as。插件把这两项替换为 image.save_current /
# image.save_dds 时，必须同步接管快捷键，否则 Alt+S 仍会走原生保存路径
# （DDS 会报 internal error）。
#
# 做法：
#   1) 只把原生 keymap_item 的 active 置 False（保留条目，便于精确还原）。
#   2) 在 addon keyconfig 里新建同键位的插件快捷键。
#   3) 卸载时反向操作，完全恢复原生绑定。

_NATIVE_SAVE_IDNAMES = {"image.save", "image.save_as"}
_DISABLED_NATIVE_SAVE_ITEMS = []      # [(kmi, 原始 active 值)]
_ADDED_PLUGIN_KEYMAP_ITEMS = []       # [(keymap, kmi)]


def _disable_native_save_shortcuts():
    """停用原生 image.save / image.save_as 的快捷键绑定，并记住以便还原。"""
    _DISABLED_NATIVE_SAVE_ITEMS.clear()
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    kc = wm.keyconfigs.active
    if kc is None:
        return
    try:
        keymaps = list(kc.keymaps)
    except Exception:
        return
    for km in keymaps:
        try:
            items = list(km.keymap_items)
        except Exception:
            continue
        for kmi in items:
            if kmi.idname not in _NATIVE_SAVE_IDNAMES:
                continue
            try:
                orig_active = bool(kmi.active)
                kmi.active = False
            except Exception:
                continue
            _DISABLED_NATIVE_SAVE_ITEMS.append((kmi, orig_active))


def _add_plugin_save_shortcuts():
    """把原生 Alt+S / Shift+Alt+S 绑到插件的保存 / 另存为。"""
    _ADDED_PLUGIN_KEYMAP_ITEMS.clear()
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    kc = wm.keyconfigs.addon
    if kc is None:
        return

    # 优先沿用原生绑定所在的 keymap 上下文，保证触发范围与原生完全一致。
    km_specs = []
    try:
        native_kc = wm.keyconfigs.active
        if native_kc is not None:
            seen = set()
            for km in native_kc.keymaps:
                for kmi in km.keymap_items:
                    if kmi.idname in _NATIVE_SAVE_IDNAMES:
                        key = (km.name, km.space_type)
                        if key not in seen:
                            seen.add(key)
                            km_specs.append(key)
    except Exception:
        pass
    if not km_specs:
        km_specs = [("Image", "IMAGE_EDITOR")]

    specs = [
        # (idname, key, value, ctrl, shift, alt)
        ("image.save_current", "S", "PRESS", False, False, True),  # Alt+S
        ("image.save_dds", "S", "PRESS", False, True, True),       # Shift+Alt+S
    ]

    for km_name, km_space in km_specs:
        km = None
        try:
            km = kc.keymaps.get(km_name)
            if km is None:
                km = kc.keymaps.new(name=km_name, space_type=km_space)
        except Exception:
            km = None
        if km is None:
            continue
        for idname, key, value, ctrl, shift, alt in specs:
            try:
                kmi = km.keymap_items.new(
                    idname, key, value,
                    ctrl=ctrl, shift=shift, alt=alt, oskey=False,
                )
            except Exception:
                continue
            _ADDED_PLUGIN_KEYMAP_ITEMS.append((km, kmi))


def _restore_save_shortcuts():
    """卸载/重新注册时恢复原生快捷键，并移除插件新增的快捷键。"""
    # 1) 先移除插件新增的快捷键。
    for km, kmi in _ADDED_PLUGIN_KEYMAP_ITEMS:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _ADDED_PLUGIN_KEYMAP_ITEMS.clear()

    # 2) 再把原生条目按原来的 active 状态还原。
    for kmi, orig_active in _DISABLED_NATIVE_SAVE_ITEMS:
        try:
            kmi.active = orig_active
        except Exception:
            pass
    _DISABLED_NATIVE_SAVE_ITEMS.clear()


# ============================================================================
# 菜单接管
# ============================================================================

def menu_func_image_top(self, context):
    """与 Blender 原生 IMAGE_MT_image 完全一致的布局顺序。

    仅把原生「保存 / 另存为… / 保存副本… / 保存所有图像」四项替换成插件版本，
    其余菜单项、分隔符、顺序、图标与原生完全一致：
      * 保存 → FILE_TICK 图标（与原生一致）
      * 另存为… / 保存副本… / 保存所有图像 → 无图标（与原生一致）
    """
    import sys
    try:
        from bpy.app.translations import contexts as i18n_contexts
        ctxt = i18n_contexts.id_image
    except Exception:
        ctxt = None

    layout = self.layout
    sima = context.space_data
    ima = sima.image
    show_render = sima.show_render

    # --- New / Open / Open Cache Render -------------------------------------
    layout.operator("image.new", text="New...", text_ctxt=ctxt, icon="FILE_NEW")
    layout.operator("image.open", text="Open...", icon="FILE_FOLDER")
    layout.operator("image.read_viewlayers")

    # --- Replace / Reload / Edit Externally ---------------------------------
    if ima:
        layout.separator()
        if not show_render:
            layout.operator("image.replace", text="Replace...")
            layout.operator("image.reload", text="Reload")
        layout.operator("image.external_edit", text="Edit Externally")

    # --- Copy / Paste -------------------------------------------------------
    layout.separator()

    has_image_clipboard = False
    if sys.platform[:3] == "win" or sys.platform == "darwin":
        has_image_clipboard = True
    else:
        try:
            from _bpy import _ghost_backend
            if _ghost_backend() == "WAYLAND":
                has_image_clipboard = True
            del _ghost_backend
        except Exception:
            pass

    if has_image_clipboard:
        layout.operator("image.clipboard_copy", text="Copy")
        layout.operator("image.clipboard_paste", text="Paste")

    # --- Save / Save As / Save a Copy / Save All ----------------------------
    if ima:
        layout.separator()
        # 不传 text=，让 Blender 使用 operator 的 bl_label；
        # bl_label 会走翻译系统，text= 硬编码的字符串不会。
        # 「保存」保留原生 FILE_TICK 图标；其余三项原生没有图标。
        layout.operator("image.save_current", icon="FILE_TICK")
        layout.operator("image.save_dds")
        layout.operator("image.save_dds_copy")
        # 用插件版本替换原生 image.save_all_modified，避免 DDS 保存报错。
        layout.operator("image.save_all_modified_custom")

        # --- Invert / Resize / Transform / Pack -----------------------------
        layout.separator()
        layout.menu("IMAGE_MT_image_invert")
        layout.operator("image.resize", text="Resize")
        layout.menu("IMAGE_MT_image_transform")
        if ima.packed_file:
            if ima.filepath:
                layout.separator()
                layout.operator("image.unpack", text="Unpack")
        else:
            layout.separator()
            layout.operator("image.pack", text="Pack")

        if context.area and context.area.ui_type == "IMAGE_EDITOR":
            layout.separator()
            layout.operator("palette.extract_from_image", text="Extract Palette")


_orig_image_menu_draw = None


def _install_image_menu_override():
    global _orig_image_menu_draw
    menu_cls = getattr(bpy.types, "IMAGE_MT_image", None)
    if menu_cls is None:
        return False
    if _orig_image_menu_draw is None:
        _orig_image_menu_draw = menu_cls.draw
    menu_cls.draw = menu_func_image_top
    return True


def _restore_image_menu_override():
    global _orig_image_menu_draw
    menu_cls = getattr(bpy.types, "IMAGE_MT_image", None)
    if menu_cls is not None and _orig_image_menu_draw is not None:
        menu_cls.draw = _orig_image_menu_draw
    _orig_image_menu_draw = None


# ============================================================================
# 注册/注销
# ============================================================================

_classes = (
    DDSSavePreferences,
    WM_DDS_refresh_gpus,
    IMAGE_OT_save_current,
    IMAGE_OT_save_dds,
    IMAGE_OT_save_dds_copy,
    IMAGE_OT_save_all_modified,
)

def register():
    # 注册插件自带翻译字典。用 try/except 兜底：重复 register 或极旧版本
    # 缺少该 API 时不阻塞插件加载。
    try:
        bpy.app.translations.register(__name__, _TRANSLATIONS)
    except Exception as _exc:
        print(f"[DDS Save] translations register failed: {_exc!r}")

    # 防止重复注册（例如 addon_utils.enable + preferences.addon_enable 连调）
    # 导致快捷键接管状态叠加。
    _restore_save_shortcuts()

    _refresh_gpu_cache()
    for cls in _classes:
        bpy.utils.register_class(cls)
    _install_image_menu_override()

    # 先停用原生 Save / Save As 快捷键，再把同键位绑到插件操作符。
    _disable_native_save_shortcuts()
    _add_plugin_save_shortcuts()

def unregister():
    # 先注销翻译字典，再走原有卸载流程。
    try:
        bpy.app.translations.unregister(__name__)
    except Exception as _exc:
        print(f"[DDS Save] translations unregister failed: {_exc!r}")

    # 恢复原生 Save / Save As 快捷键，移除插件新增的快捷键。
    _restore_save_shortcuts()
    _restore_image_menu_override()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()