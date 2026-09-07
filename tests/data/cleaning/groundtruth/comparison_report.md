# TESS Dehazing: Original vs Reverse — Bit-by-Bit Comparison

- Generated: 2026-07-08T19:59:19+00:00
- Mode: `3d` (spatio-temporal)
- Original run: `tess-scatter-removal` -> `/tmp/tess_cmp/original`
- Reverse run: `tess-scatter-removal-reverse` -> `/tmp/tess_cmp/reverse`
- Input FITS: `tess-downloader/TESS/s0003-c2-ccd1/00_raw_ffi` (5 frames)
- Interpreter: shared `tess-scatter-removal/.venv` (numpy/scipy/astropy, plain opencv-python)

## Verdict

**IDENTICAL.** All 5 output pairs are bit-for-bit identical at both the pixel-array level and the whole-file level. The reverse reimplementation reproduces the original exactly.

## Per-file results

| File | Shape | Dtype | Pixels bit-identical | File bytes identical | Max |Δ| | Mean |Δ| | # diff px |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tess2018288032939-s0003-2-1-0123-s_ffic.fits | 2048x2048 | >f8 | yes | yes | 0 | 0 | 0 |
| tess2018288142939-s0003-2-1-0123-s_ffic.fits | 2048x2048 | >f8 | yes | yes | 0 | 0 | 0 |
| tess2018289045939-s0003-2-1-0123-s_ffic.fits | 2048x2048 | >f8 | yes | yes | 0 | 0 | 0 |
| tess2018289072939-s0003-2-1-0123-s_ffic.fits | 2048x2048 | >f8 | yes | yes | 0 | 0 | 0 |
| tess2018289112939-s0003-2-1-0123-s_ffic.fits | 2048x2048 | >f8 | yes | yes | 0 | 0 | 0 |

## File MD5 checksums

| File | original MD5 | reverse MD5 | match |
| --- | --- | --- | --- |
| tess2018288032939-s0003-2-1-0123-s_ffic.fits | `f08f19ea24cac37a17edac510a983ad7` | `f08f19ea24cac37a17edac510a983ad7` | yes |
| tess2018288142939-s0003-2-1-0123-s_ffic.fits | `27f5d5a7a0cc2fe4c9d65a40713bed5c` | `27f5d5a7a0cc2fe4c9d65a40713bed5c` | yes |
| tess2018289045939-s0003-2-1-0123-s_ffic.fits | `ff2dc08f2dc9195ac6e58e8e880681f3` | `ff2dc08f2dc9195ac6e58e8e880681f3` | yes |
| tess2018289072939-s0003-2-1-0123-s_ffic.fits | `9f9295ea038faf245267b59cb0acc1fc` | `9f9295ea038faf245267b59cb0acc1fc` | yes |
| tess2018289112939-s0003-2-1-0123-s_ffic.fits | `bfdcb09a4f06bd09baffd581c7e0e0af` | `bfdcb09a4f06bd09baffd581c7e0e0af` | yes |

## Collected files in this folder

Each output is copied here with an implementation prefix:

- `original__dehazed_3d__tess2018288032939-s0003-2-1-0123-s_ffic.fits`
- `reverse__dehazed_3d__tess2018288032939-s0003-2-1-0123-s_ffic.fits`
- `original__dehazed_3d__tess2018288142939-s0003-2-1-0123-s_ffic.fits`
- `reverse__dehazed_3d__tess2018288142939-s0003-2-1-0123-s_ffic.fits`
- `original__dehazed_3d__tess2018289045939-s0003-2-1-0123-s_ffic.fits`
- `reverse__dehazed_3d__tess2018289045939-s0003-2-1-0123-s_ffic.fits`
- `original__dehazed_3d__tess2018289072939-s0003-2-1-0123-s_ffic.fits`
- `reverse__dehazed_3d__tess2018289072939-s0003-2-1-0123-s_ffic.fits`
- `original__dehazed_3d__tess2018289112939-s0003-2-1-0123-s_ffic.fits`
- `reverse__dehazed_3d__tess2018289112939-s0003-2-1-0123-s_ffic.fits`

