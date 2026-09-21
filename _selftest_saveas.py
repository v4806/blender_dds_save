"""IMAGE_OT_save_dds（另存为）专项自测：扩展名联动 + DDS/原生格式分流"""
import os
import tempfile
import zlib

import bpy

import addon_utils
import dds_save as mod

addon_utils.enable("dds_save")
try:
    bpy.ops.preferences.addon_enable(module="dds_save")
except Exception:
    pass

out = tempfile.mkdtemp(prefix="dds_saveas_")
print("SAVEAS_TMP", out)
res = []


def check(name, ok, detail=""):
    res.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")


# ---- 后台模式没有 window/area，用 temp_override 注入 image 上下文 ----
_ctx = bpy.context.temp_override
print("HAS_TEMP_OVERRIDE", hasattr(bpy.context, "temp_override"))

# 1. 扩展名联动（纯逻辑，直接走类方法）
for fmt, src, want in [
    ("DDS", os.path.join(out, "t.png"), ".dds"),
    ("PNG", os.path.join(out, "t.dds"), ".png"),
    ("JPEG", os.path.join(out, "t"), ".jpg"),
    ("WEBP", os.path.join(out, "t.dds"), ".webp"),
]:
    got = mod.IMAGE_OT_save_dds._with_format_ext(
        type("X", (), {"export_format": fmt})(), src)
    check(f"扩展名联动 {fmt}", os.path.splitext(got)[1].lower() == want, got)

# 2. 激活一张图像并验证 poll
im = bpy.data.images.new("saveas_dds", 64, 64)
im.pixels = [0.4] * (64 * 64 * 4)
im.filepath_raw = os.path.join(out, "src.png")
with _ctx(image=im):
    poll_ok = bpy.ops.image.save_dds.poll()
print("POLL", poll_ok)
check("有图像时 poll 通过", poll_ok, "temp_override(image=...)")

# 3. execute 分流：DDS
dds_target = os.path.join(out, "out.dds")
with _ctx(image=im):
    r = bpy.ops.image.save_dds(filepath=dds_target, export_format="DDS")
head = b""
if os.path.isfile(dds_target):
    with open(dds_target, "rb") as fh:
        head = fh.read(4)
check("execute DDS 分流", r == {"FINISHED"} and head == b"DDS ", f"{r} {head.hex()}")
check("DDS 分支不破坏 dirty 状态", im.is_dirty is True, f"is_dirty={im.is_dirty}")

# 4. execute 分流：JPEG（原生路径）
jpg_target = os.path.join(out, "out_with_ext.jpg")
im.pixels = [0.7] * (64 * 64 * 4)
with _ctx(image=im):
    r2 = bpy.ops.image.save_dds(filepath=jpg_target, export_format="JPEG", quality=85)
head2 = b""
if os.path.isfile(jpg_target):
    with open(jpg_target, "rb") as fh:
        head2 = fh.read(3)
check("execute JPEG 分流", r2 == {"FINISHED"} and head2 == b"\xff\xd8\xff", f"{r2} {head2.hex()}")
check("JPEG 分支清脏", im.is_dirty is False, f"is_dirty={im.is_dirty}")
check("非 DDS 分支不残留中间 PNG",
      not os.path.isfile(os.path.join(out, "out_with_ext.png")))

# 5. 扩展名与格式不符时按格式纠正落盘扩展名
mismatch = os.path.join(out, "mismatch.dds")
try:
    bpy.ops.preferences.addon_enable(module="dds_save")
except Exception:
    pass
with _ctx(image=im):
    bpy.ops.image.save_dds(filepath=mismatch, export_format="PNG")
corrected = os.path.join(out, "mismatch.png")
pass_saveas = os.path.isfile(corrected)
check("execute 按格式纠正扩展名", pass_saveas,
      f"png={os.path.isfile(corrected)} dds={os.path.isfile(mismatch)}")

# 6. PNG 走插件自编码：压缩参数真的生效、像素无损
im2 = bpy.data.images.new("saveas_png", 32, 32)
px = []
for y in range(32):
    for x in range(32):
        px += [(x % 16) / 15.0, (y % 16) / 15.0, ((x + y) % 8) / 7.0, 1.0]
im2.pixels = px
im2.colorspace_settings.name = "sRGB"
ref = os.path.join(out, "ref.png")
im2.filepath_raw = ref
im2.file_format = "PNG"
im2.save()
print("REF_EXISTS", os.path.isfile(ref), os.path.getsize(ref) if os.path.isfile(ref) else -1)

low = os.path.join(out, "c0.png")
high = os.path.join(out, "c100.png")
for target, comp in ((low, 0), (high, 100)):
    with _ctx(image=im2):
        bpy.ops.image.save_dds(filepath=target, export_format="PNG",
                               png_compression=comp, color_mode="RGBA", color_depth_int="8")
size_low = os.path.getsize(low) if os.path.isfile(low) else 0
size_high = os.path.getsize(high) if os.path.isfile(high) else 0
check("PNG 压缩参数生效", size_low > size_high > 0, f"comp0={size_low} comp100={size_high}")

ref_img = bpy.data.images.load(ref, check_existing=False)
enc_img = bpy.data.images.load(high, check_existing=False)
pa = list(ref_img.pixels)
pb = list(enc_img.pixels)
maxdiff = max(abs(pa[i] - pb[i]) for i in range(len(pa))) if len(pa) == len(pb) else -1
check("PNG 自编码像素无损", maxdiff == 0.0, f"maxdiff={maxdiff}")

# 6.1 PNG sRGB 编码不再被 colorspace 参数绕过。
tiny = bpy.data.images.new("saveas_png_srgb", 1, 1)
tiny.pixels = [0.5, 0.5, 0.5, 1.0]
tiny.colorspace_settings.name = "sRGB"
tiny_path = os.path.join(out, "tiny_srgb.png")
with _ctx(image=tiny):
    bpy.ops.image.save_dds(filepath=tiny_path, export_format="PNG",
                           colorspace="sRGB", color_mode="RGBA", color_depth_int="8")
raw = b""
has_srgb = False
if os.path.isfile(tiny_path):
    with open(tiny_path, "rb") as fh:
        data = fh.read()
    pos2 = 8
    idat = b""
    while pos2 + 12 <= len(data):
        n = int.from_bytes(data[pos2:pos2+4], "big")
        typ = data[pos2+4:pos2+8]
        payload = data[pos2+8:pos2+8+n]
        if typ == b"sRGB":
            has_srgb = True
        if typ == b"IDAT":
            idat += payload
        pos2 += 12 + n
    raw = zlib.decompress(idat) if idat else b""
check("PNG sRGB 元数据存在", has_srgb)
check("PNG sRGB 线性 0.5 编码正确",
      len(raw) >= 5 and raw[0] == 0 and tuple(raw[1:5]) == (188, 188, 188, 255),
      f"raw={list(raw[:5])}")


# 7. RGB / BW 颜色模式写入的通道数正确（读回后 Blender 统一为 4 通道，只看文件头）
rgb_png = os.path.join(out, "rgb.png")
with _ctx(image=im2):
    bpy.ops.image.save_dds(filepath=rgb_png, export_format="PNG", color_mode="RGB")
with open(rgb_png, "rb") as fh:
    head = fh.read(26)
color_type = head[25] if len(head) > 25 else -1
check("PNG 颜色模式 RGB 生效", color_type == 2, f"color_type={color_type}")

# 8. EXR / TIFF 编解码参数真正生效（save_render + Standard 路径）
exr_none = os.path.join(out, "codec_none.exr")
exr_dwaa = os.path.join(out, "codec_dwaa.exr")
with _ctx(image=im2):
    bpy.ops.image.save_dds(filepath=exr_none, export_format="OPEN_EXR", exr_codec="NONE")
    bpy.ops.image.save_dds(filepath=exr_dwaa, export_format="OPEN_EXR", exr_codec="DWAA")
size_exr_none = os.path.getsize(exr_none) if os.path.isfile(exr_none) else 0
size_exr_dwaa = os.path.getsize(exr_dwaa) if os.path.isfile(exr_dwaa) else 0
check("EXR 编解码参数生效", size_exr_none > size_exr_dwaa > 0,
      f"none={size_exr_none} dwaa={size_exr_dwaa}")

tif_none = os.path.join(out, "codec_none.tif")
tif_lzw = os.path.join(out, "codec_lzw.tif")
with _ctx(image=im2):
    bpy.ops.image.save_dds(filepath=tif_none, export_format="TIFF", tiff_codec="NONE")
    bpy.ops.image.save_dds(filepath=tif_lzw, export_format="TIFF", tiff_codec="LZW")
size_tif_none = os.path.getsize(tif_none) if os.path.isfile(tif_none) else 0
size_tif_lzw = os.path.getsize(tif_lzw) if os.path.isfile(tif_lzw) else 0
check("TIFF 编解码参数生效", size_tif_none > size_tif_lzw > 0,
      f"none={size_tif_none} lzw={size_tif_lzw}")

# 9. save_render 路径不得污染场景设置
sc_img = bpy.context.scene.render.image_settings
check("场景输出设置未被污染",
      sc_img.file_format == "PNG" and sc_img.compression == 15,
      f"fmt={sc_img.file_format} comp={sc_img.compression}")

# ------------------------------------------------------------- 汇总
failed = [r for r in res if not r[1]]
print(f"SAVEAS_SUMMARY total={len(res)} failed={len(failed)}")
for name, _, detail in failed:
    print(f"SAVEAS_FAILED {name} :: {detail}")
