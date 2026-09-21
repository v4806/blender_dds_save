import ast
from pathlib import Path

src = Path(Path(__file__).with_name("__init__.py")).read_text(encoding="utf-8")
tree = ast.parse(src)
want = {
    '_DDS_BC7_FORMATS', '_DDS_BC1_3_FORMATS', '_dds_is_bc7',
    '_dds_is_bc1_3', '_build_texconv_command'
}
ns = {'Path': Path}
for node in tree.body:
    if isinstance(node, (ast.Assign, ast.FunctionDef)):
        names = set()
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name): names.add(t.id)
        else:
            names.add(node.name)
        if names & want:
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<helper>', 'exec'), ns)

build = ns['_build_texconv_command']

def cmd(**kw):
    return build('texconv.exe', 'in.png', r'C:\out\a.dds', **kw)

def has(c, *xs):
    for x in xs:
        assert x in c, (x, c)

def lacks(c, *xs):
    for x in xs:
        assert x not in c, (x, c)

# BC7 SRGB: no ignore-srgb, quality max, GPU adapter and alpha weight.
c = cmd(dds_format='BC7_UNORM_SRGB', mip_enabled=False, bc_quality='max',
        use_gpu=True, gpu_adapter=2, singleproc=True, ignore_srgb_metadata=False,
        alpha_weight=2.0)
has(c, '-f', 'BC7_UNORM_SRGB', '-m', '1', '-gpu', '2', '-bc', 'x', '-aw', '2.0')
lacks(c, '--ignore-srgb', '-if', '-nogpu', '-singleproc')

# BC7 Linear: ignore source sRGB metadata, CPU and singleproc, quick.
c = cmd(dds_format='BC7_UNORM', mip_enabled=False, bc_quality='quick',
        use_gpu=False, gpu_adapter=2, singleproc=True, ignore_srgb_metadata=True,
        alpha_weight=1.0)
has(c, '--ignore-srgb', '-gpu' if False else '-nogpu', '-bc', 'q', '-singleproc')
lacks(c, '-aw', '-if')

# BC7 standard: no -bc, GPU means no singleproc.
c = cmd(dds_format='BC7_UNORM', mip_enabled=False, bc_quality='standard',
        use_gpu=True, gpu_adapter=0, singleproc=True, ignore_srgb_metadata=True)
has(c, '--ignore-srgb', '-gpu', '0')
lacks(c, '-bc', '-singleproc')

# BC1: uniform+dither combined as -bc ud, alpha threshold, mip filter/coverage.
c = cmd(dds_format='BC1_UNORM', mip_enabled=True, mip_filter='FANT',
        bc_weighting='uniform', bc_dither=True, alpha_threshold=0.35,
        keep_coverage=True, coverage_ref=0.45, separate_alpha=True,
        ignore_srgb_metadata=True, alpha_mode='KEEP')
has(c, '--ignore-srgb', '-m', '0', '-if', 'FANT', '-sepalpha',
    '-keepcoverage', '0.45', '-bc', 'ud', '-at', '0.35')
lacks(c, '-gpu', '-nogpu', '-singleproc', '-aw')

# BC3: same BC1-3 encoder flags, but no alpha threshold.
c = cmd(dds_format='BC3_UNORM_SRGB', mip_enabled=False,
        bc_weighting='uniform', bc_dither=True, alpha_threshold=0.25,
        ignore_srgb_metadata=False)
has(c, '-f', 'BC3_UNORM_SRGB', '-m', '1', '-bc', 'ud')
lacks(c, '--ignore-srgb', '-at', '-gpu', '-nogpu', '-singleproc', '-aw')

# BC5: no BC1-3/BC7 encoder-quality controls.
c = cmd(dds_format='BC5_UNORM', mip_enabled=False,
        bc_weighting='uniform', bc_dither=True, bc_quality='max',
        use_gpu=True, singleproc=True, ignore_srgb_metadata=True)
has(c, '--ignore-srgb', '-f', 'BC5_UNORM', '-m', '1')
lacks(c, '-bc', '-gpu', '-nogpu', '-singleproc', '-at', '-aw')

# Uncompressed: only format + mip/alpha operations apply.
c = cmd(dds_format='R8G8B8A8_UNORM_SRGB', mip_enabled=True,
        mip_filter='LANCZOS3', separate_alpha=True, keep_coverage=True,
        coverage_ref=0.5, alpha_mode='PREMULTIPLIED', ignore_srgb_metadata=False)
has(c, '-f', 'R8G8B8A8_UNORM_SRGB', '-m', '0', '-if', 'LANCZOS3',
    '-sepalpha', '-pmalpha')
lacks(c, '--ignore-srgb', '-bc', '-gpu', '-nogpu', '-singleproc', '-aw')

# Alpha KEEP must add neither transform flag.
c = cmd(dds_format='R8G8B8A8_UNORM', mip_enabled=False, alpha_mode='KEEP',
        ignore_srgb_metadata=True)
lacks(c, '-pmalpha', '-alpha')

print('PASS | 2.4.4 texconv parameter matrix')
