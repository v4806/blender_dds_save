"""DDS Save 2.4.5 UI 自测：只显示当前 DDS 格式适用参数，不显示说明文字。"""
import ast
from pathlib import Path

SRC = Path(__file__).with_name("__init__.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)
NAMES = {"_DDS_BC7_FORMATS", "_DDS_BC1_3_FORMATS", "_dds_is_bc7", "_dds_is_bc1_3", "_dds_has_alpha", "draw_save_params_ui"}
ns = {}
for node in TREE.body:
    if ((isinstance(node, ast.FunctionDef) and node.name in NAMES) or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in node.targets))):
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<ui_helper>", "exec"), ns)

class FakeLayout:
    use_property_split = False
    use_property_decorate = True
    def __init__(self):
        self.calls = []
    def prop(self, obj, name, **kwargs):
        self.calls.append(("prop", name))
    def label(self, **kwargs):
        self.calls.append(("label", kwargs.get("text", "")))
    def row(self, **kwargs):
        self.calls.append(("row", kwargs))
        return self

class Op:
    export_format = "DDS"
    dds_format = "BC7_UNORM"
    bc_quality = "max"
    alpha_weight = 1.0
    bc_weighting = "perceptual"
    bc_dither = False
    alpha_threshold = 0.5
    mip_enabled = False
    mip_filter = "FANT"
    separate_alpha = False
    keep_coverage = False
    coverage_ref = 0.5
    use_gpu = True
    gpu_adapter = "0"
    singleproc = False
    alpha_mode = "KEEP"
    color_mode = "RGBA"
    color_depth_float = "16"
    color_depth_int = "8"
    png_compression = 15
    quality = 90
    exr_codec = "ZIP"
    tiff_codec = "LZW"
    colorspace = "sRGB"

ns["_dds_has_alpha"] = ns["_dds_has_alpha"]
ns["draw_save_params_ui"](Op(), FakeLayout())


def draw_names(dds, mip=False, use_gpu=True, keep=False):
    op = Op(); op.dds_format = dds; op.mip_enabled = mip; op.use_gpu = use_gpu; op.keep_coverage = keep
    lay = FakeLayout(); ns["draw_save_params_ui"](op, lay)
    return [x[1] for x in lay.calls if x[0] == "prop"], [x for x in lay.calls if x[0] == "label"]

# BC7: only BC7 + common applicable params.
props, labels = draw_names("BC7_UNORM", mip=False, use_gpu=True)
assert "bc_quality" in props and "alpha_weight" in props and "use_gpu" in props and "gpu_adapter" in props and "alpha_mode" in props
assert "bc_weighting" not in props and "bc_dither" not in props and "alpha_threshold" not in props and "singleproc" not in props
assert labels == []

# BC1: BC1-specific params; no GPU/BC7 params.
props, labels = draw_names("BC1_UNORM", mip=True, use_gpu=True, keep=True)
assert "bc_weighting" in props and "bc_dither" in props and "alpha_threshold" in props
assert "gpu_adapter" not in props and "use_gpu" not in props and "alpha_weight" not in props
assert "mip_filter" in props and "separate_alpha" in props and "keep_coverage" in props and "coverage_ref" in props and "alpha_mode" in props
assert labels == []

# BC5: no alpha, no BC7/BC1 encoder controls.
props, labels = draw_names("BC5_UNORM", mip=True)
assert "bc_quality" not in props and "bc_weighting" not in props and "bc_dither" not in props
assert "use_gpu" not in props and "gpu_adapter" not in props and "singleproc" not in props and "alpha_mode" not in props
assert "mip_filter" in props
assert labels == []

# R8G8B8A8: only common mip/alpha controls, no BC controls.
props, labels = draw_names("R8G8B8A8_UNORM", mip=False)
assert "mip_enabled" in props and "alpha_mode" in props
assert "bc_quality" not in props and "bc_weighting" not in props and "use_gpu" not in props
assert labels == []

# DDS must contain no explanatory label calls at all.
for dds in ("BC7_UNORM", "BC1_UNORM", "BC3_UNORM", "BC5_UNORM", "R8G8B8A8_UNORM"):
    _, labels = draw_names(dds, mip=True, keep=True)
    assert labels == [], (dds, labels)

print("PASS | 2.4.5 save panel UI matrix")
