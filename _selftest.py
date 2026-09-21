"""DDS Save 插件无界面自测脚本

用法（Blender 5.1）：
    & "D:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" `
        -b --factory-startup --python "D:\\Program Files\\Blender Foundation\\scripts\\addons\\dds_save\\_selftest.py"

覆盖：注册、DDS 保存/色彩转换、中间文件清理、原生多格式落盘、texconv 缺失报错、空路径报错。
"""

import os
import sys
import tempfile

import bpy

_PKG = "dds_save"
_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")


def main():
    # ---------------------------------------------------------------- 1. 注册
    import addon_utils

    if _PKG not in [m.__name__ for m in addon_utils.modules()]:
        check("插件位于 addon 路径", False, "未找到 dds_save 模块")
        return
    try:
        addon_utils.enable(_PKG)
        # addon_utils.enable 不会同步 preferences.addons，用操作符确保偏好条目存在
        bpy.ops.preferences.addon_enable(module=_PKG)
    except Exception as exc:  # noqa: BLE001
        check("插件启用", False, repr(exc))
        return
    check("插件启用", addon_utils.check(_PKG)[1] is True, "addon_utils.enable")
    check("操作符注册",
          hasattr(bpy.ops.image, "save_current") and hasattr(bpy.ops.image, "save_dds"))

    import dds_save as mod

    prefs = bpy.context.preferences.addons[_PKG].preferences
    mgr = mod.TexconvManager(prefs.texconv_path.strip() or None)
    check("texconv 可用", mgr.available, str(mgr.path))

    out_dir = tempfile.mkdtemp(prefix="dds_selftest_")
    print("SELFTEST_TMP", out_dir)

    # ------------------------------------------------- 2. DDS 保存 + 清脏
    im = bpy.data.images.new("selftest_dds", 64, 64)
    im.pixels = [0.4] * (64 * 64 * 4)
    check("像素修改后为脏", im.is_dirty is True, f"is_dirty={im.is_dirty}")

    dds_path = os.path.join(out_dir, "a.dds")
    im.filepath_raw = dds_path

    observed_convert = {}
    _orig_convert = mod.TexconvManager.convert

    def _spy_convert(self_mgr, *args, **kwargs):
        observed_convert.update(kwargs)
        return _orig_convert(self_mgr, *args, **kwargs)

    mod.TexconvManager.convert = _spy_convert
    try:
        ok, msg = mod._dds_save_core(
        bpy.context, im, dds_path,
        dds_format=prefs.dds_format,
        srgb_input=False,
        bc_quality=prefs.bc_quality,
        mip_enabled=prefs.mip_enabled,
        mip_filter=prefs.mip_filter,
        use_gpu=prefs.use_gpu,
        singleproc=prefs.singleproc,
        gpu_adapter=int(prefs.gpu_adapter),
    )
    finally:
        mod.TexconvManager.convert = _orig_convert

    check("DDS 保存成功", ok, msg)
    check("SRGB DDS 自动使用输出色彩转换",
          observed_convert.get("srgb_output") is mod._dds_format_is_srgb(prefs.dds_format),
          f"srgb_output={observed_convert.get('srgb_output')}")
    check("旧 srgb_input 不再触发错误输入解码",
          observed_convert.get("srgb_input") is False,
          f"srgb_input={observed_convert.get('srgb_input')}")
    if os.path.isfile(dds_path):
        with open(dds_path, "rb") as fh:
            head = fh.read(4)
        check("产物为 DDS 魔数", head == b"DDS ", head.hex())
    else:
        check("产物为 DDS 魔数", False, "文件不存在")
    check("DDS 保存不破坏 dirty 状态", im.is_dirty is True, f"is_dirty={im.is_dirty}")
    check("中间 PNG 已清理", not os.path.isfile(os.path.join(out_dir, "a.png")))
    check("图像路径已还原", os.path.normcase(im.filepath_raw) == os.path.normcase(dds_path),
          im.filepath_raw)

    # 线性目标即使传入旧版 srgb_input=True，也必须不加 -srgbi。
    linear_dds = os.path.join(out_dir, "a_linear.dds")
    observed_linear = {}
    _orig_convert2 = mod.TexconvManager.convert

    def _spy_convert2(self_mgr, *args, **kwargs):
        observed_linear.update(kwargs)
        return _orig_convert2(self_mgr, *args, **kwargs)

    mod.TexconvManager.convert = _spy_convert2
    try:
        ok_linear, msg_linear = mod._dds_save_core(
            bpy.context, im, linear_dds,
            dds_format="BC7_UNORM",
            srgb_input=True,
            bc_quality=prefs.bc_quality,
            mip_enabled=False,
            mip_filter=prefs.mip_filter,
            use_gpu=prefs.use_gpu,
            singleproc=prefs.singleproc,
            gpu_adapter=int(prefs.gpu_adapter),
        )
    finally:
        mod.TexconvManager.convert = _orig_convert2
    check("Linear DDS 保存成功", ok_linear, msg_linear)
    check("Linear DDS 不使用 sRGB 转换",
          observed_linear.get("srgb_input") is False and observed_linear.get("srgb_output") is False,
          f"in={observed_linear.get('srgb_input')} out={observed_linear.get('srgb_output')}")

    # --------------------------------------------- 3. 其它格式原生落盘 + 清脏
    for fmt, magic, ext in (("JPEG", b"\xff\xd8\xff", ".jpg"), ("PNG", b"\x89PNG", ".png")):
        img = bpy.data.images.new(f"selftest_{fmt}", 64, 64)
        img.pixels = [0.5] * (64 * 64 * 4)
        target = os.path.join(out_dir, f"b{ext}")
        img.filepath_raw = target
        img.file_format = fmt
        try:
            img.save(quality=90)
            with open(target, "rb") as fh:
                head = fh.read(len(magic))
            check(f"{fmt} 原生落盘", head == magic, head.hex())
            check(f"{fmt} 保存后清脏", img.is_dirty is False, f"is_dirty={img.is_dirty}")
        except Exception as exc:  # noqa: BLE001
            check(f"{fmt} 原生落盘", False, repr(exc))

    # ------------------------------------------------- 4. texconv 缺失时报错
    # 注意：TexconvManager 找不到 manual_path 时仍会回退到插件目录的 texconv.exe，
    # 因此这里直接用不存在的 manual_path 校验其查找语义，再验证空路径分支。
    mgr_missing = mod.TexconvManager(os.path.join(out_dir, "no_such_texconv.exe"))
    check("无效 manual_path 仍能回退查找", mgr_missing.available,
          f"回退到 {mgr_missing.path}")
    ok2, msg2 = mod._dds_save_core(bpy.context, im, "")
    check("空输出路径返回失败而非崩溃", ok2 is False, msg2[:60])

    # ------------------------------------------------- 5. 菜单接管与按格式绘制
    menu_cls = getattr(bpy.types, "IMAGE_MT_image", None)
    check("IMAGE_MT_image.draw 已被接管",
          menu_cls is not None and menu_cls.draw is mod.menu_func_image_top,
          getattr(getattr(menu_cls, "draw", None), "__name__", "?"))

    class _FakeLayout:
        use_property_split = None
        use_property_decorate = None

        def __init__(self):
            self.calls = []

        def row(self, **_kw):
            self.calls.append("row")
            return self

        def operator(self, idname, **_kw):
            self.calls.append(f"op:{idname}")
            return self

        def separator(self):
            self.calls.append("sep")

        def prop(self, _obj, name, **_kw):
            self.calls.append(f"prop:{name}")

        def label(self, **_kw):
            self.calls.append("label")

        def menu(self, idname, **_kw):
            self.calls.append(f"menu:{idname}")

    class _FakeMenu:
        def __init__(self):
            self.layout = _FakeLayout()

    # 构造能通过菜单 draw 所需属性的假上下文（ima 非空以便覆盖依赖图像的条目）
    class _FakeImage:
        source = "FILE"
        packed_file = None
        filepath = "/tmp/x.dds"

    class _FakeSpace:
        image = _FakeImage()
        show_render = False

    class _FakeArea:
        ui_type = "IMAGE_EDITOR"

    class _FakeCtx:
        space_data = _FakeSpace()
        area = _FakeArea()

    fake_menu = _FakeMenu()
    mod.menu_func_image_top(fake_menu, _FakeCtx())
    drawn = fake_menu.layout.calls
    check("接管菜单含插件项",
          "op:image.save_current" in drawn and "op:image.save_dds" in drawn,
          ",".join(drawn[:4]))
    check("插件两项各占一行（无 row 并排）",
          "row" not in drawn,
          f"row_count={drawn.count('row')}")
    check("接管菜单已扣除原生保存项",
          "op:image.save" not in drawn and "op:image.save_as" not in drawn,
          ",".join(c for c in drawn if "save" in c))
    check("接管菜单保留其余原生项",
          "op:image.new" in drawn and "op:image.open" in drawn
          and "op:image.reload" in drawn and "op:image.resize" in drawn
          and "menu:IMAGE_MT_image_transform" in drawn
          and "op:image.pack" in drawn,
          ",".join(c for c in drawn if c.startswith(("op:image", "menu:")))[:120])

    # draw() 按格式只显示对应参数（依据源码：定义 draw 即接管自动布局）
    expect_map = {
        "DDS": ("prop:dds_format", None),
        "PNG": ("prop:png_compression", "prop:dds_format"),
        "JPEG": ("prop:quality", "prop:dds_format"),
        "WEBP": ("prop:quality", "prop:dds_format"),
        "OPEN_EXR": ("prop:exr_codec", "prop:dds_format"),
        "TIFF": ("prop:tiff_codec", "prop:dds_format"),
        "BMP": ("prop:color_mode", "prop:dds_format"),
    }
    for fmt, (expect, forbidden) in expect_map.items():
        holder = type("FakeOp", (), {"export_format": fmt,
                                     "layout": _FakeLayout()})()
        try:
            mod.IMAGE_OT_save_dds.draw(holder, bpy.context)
            calls_now = holder.layout.calls
            ok = expect in calls_now and (not forbidden or forbidden not in calls_now)
            check(f"draw({fmt}) 只显示该格式参数", ok, ",".join(calls_now[:9]))
        except Exception as exc:  # noqa: BLE001
            check(f"draw({fmt}) 只显示该格式参数", False, repr(exc))

    # 非 DDS 格式必须带出通用图像参数（对齐原生面板）
    holder = type("FakeOp", (), {"export_format": "PNG", "layout": _FakeLayout()})()
    mod.IMAGE_OT_save_dds.draw(holder, bpy.context)
    common = holder.layout.calls
    check("非 DDS 显示颜色/色深/色彩空间",
          "prop:color_mode" in common and "prop:color_depth_int" in common
          and "prop:colorspace" in common,
          ",".join(common[:9]))

    # 注销后必须还原原生菜单 draw
    orig_draw = mod._orig_image_menu_draw
    mod.unregister()
    check("unregister 还原原生菜单", menu_cls.draw is orig_draw,
          getattr(menu_cls.draw, "__name__", "?"))
    mod.register()
    check("register 重新接管菜单", menu_cls.draw is mod.menu_func_image_top)

    # ------------------------------------------------------------- 汇总
    failed = [r for r in _results if not r[1]]
    print(f"SELFTEST_SUMMARY total={len(_results)} failed={len(failed)}")
    for name, _, detail in failed:
        print(f"SELFTEST_FAILED {name} :: {detail}")


main()
