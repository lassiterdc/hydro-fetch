"""
Self-contained replacement for multidriver-swg's `_old_code_to_refactor/_utils.py`.

The source module is 2,393 lines. Exactly ONE symbol from it is referenced by any
of the four absorbed scripts, traced by reading each script's usage rather than
its import statement -- the scripts used `from _utils import *`, which imports
everything and reveals nothing about what is actually needed.

Vendored symbol:
  - define_zarr_compression   (used by _a2_dwnld_aorc_pre_mrms.py, line ~66)

Reproduced byte-for-byte from the source. Nothing else was taken; the remaining
~2,390 lines are multidriver-swg's and stay there.

Source: multidriver-swg @ 1fba5826d024cf10ffb5d31ebd268b2900c48651
        _old_code_to_refactor/_utils.py, lines 19-24
"""


def define_zarr_compression(ds, clevel=5):
    import zarr
    encoding = {}
    for da_name in ds.data_vars:
        encoding[da_name] = {"compressor": zarr.Blosc(cname="zstd", clevel=clevel, shuffle=zarr.Blosc.SHUFFLE)}
    return encoding
