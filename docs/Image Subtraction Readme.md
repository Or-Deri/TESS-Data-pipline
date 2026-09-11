# Image Subtraction Pipeline (Main / Sequential)

A Python + C implementation of image subtraction for **TESS Full Frame Images (FFIs)**, based on Optimal Image Subtraction.

This repository contains:

* **Python pipeline** that prepares data, runs image subtraction, detects sources, and extracts lightcurves.
* **C differencing binary (`a.out`)** invoked by Python.
* **Smart skipping**: CCDs are skipped automatically if no new/modified FFIs are detected in their `00_raw_ffi/` folder.

---

## Features

* Preprocesses TESS FFIs (alignment, 2D cutout, background subtraction, master-frame creation).
* Builds reference master frames.
* Runs Optimal Image Subtraction (Oelkers et al. implementation under the hood).
* Cross-matches detected sources across residual frames.
* Extracts lightcurves from residual images.
* Flexible execution scopes:

  * **Single CCD** (sector, camera, CCD)
  * **Full camera** (sector + camera, all CCDs)
  * **Full sector** (all cameras & CCDs)
  * **Multiple sectors** in one run
* **Skip unchanged CCDs** to avoid reprocessing when there are no new FFIs.

---

## Requirements

* Python 3.10+
* Astropy, Photutils, Lightkurve, SciPy, Matplotlib
* CFITSIO (to build the C program)

Install Python deps using the provided `requirements.txt`.

---

## Installation

Clone and create a virtual environment:

```bash
git clone git@github.com:Astro-informatics-cipher-project/image-subtraction.git
cd image-subtraction
python3 -m venv image_substraction
source image_substraction/bin/activate
pip install -r requirements.txt
```

Compile the C program (adjust include/library paths if needed):

```bash
gcc oisdifference.c -lcfitsio -lm -o a.out
```

> If your file is named differently (e.g., `dia.c`), update the command accordingly.

---

## Directory Structure

```
image-subtraction/
│
├─ src/
│  ├─ core_science.py   # Preprocess, subtraction, photometry, utilities
│  ├─ pipeline.py       # High-level pipeline orchestration (sequential)
│  └─ main.py           # CLI entry point
│
├─ tess/                # Data (per sector/camera/ccd)
│  └─ s0001-c1-ccd1/
│     ├─ 00_raw_ffi/
│     ├─ 01_preprocessed/
│     ├─ 02_masters_frames/
│     ├─ 03_ref_data/
│     ├─ 04_residual_img/
│     ├─ 05_sources/
│     └─ 06_lightcurves/
│
├─ oisdifference.c      # C implementation (or similar)
├─ a.out                # Built C binary
├─ requirements.txt
├─ README.md
└─ .gitignore
```

---

## Usage

Run from the project root. The pipeline assumes FFIs are **already downloaded** into each CCD's `00_raw_ffi/`.

### Single CCD

```bash
python3 -m src.main --sector 1 --camera 1 --ccd 1 \
  --parent-folder /mnt/e/Image_subtration/tess \
  --code-dir /mnt/e/Image_subtration/tess
```

### Full Camera (process multiple CCDs)

```bash
python3 -m src.main --sector 1 --camera 1 --ccd 1 2 3 4 \
  --parent-folder /mnt/e/Image_subtration/tess \
  --code-dir /mnt/e/Image_subtration/tess
```

### Full Sector (all cameras & CCDs)

```bash
python3 -m src.main --sector 1 --camera 1 2 3 4 --ccd 1 2 3 4 \
  --parent-folder /mnt/e/Image_subtration/tess \
  --code-dir /mnt/e/Image_subtration/tess
```

### Multiple Sectors in one run

```bash
python3 -m src.main --sector 1 2 3 --camera 1 2 3 4 --ccd 1 2 3 4 \
  --parent-folder /mnt/e/Image_subtration/tess \
  --code-dir /mnt/e/Image_subtration/tess
```

> **Skipping behavior:** if a CCD has no new or modified files in `00_raw_ffi/` since the last run, it is reported with a `[SKIP]` message and is not reprocessed.

---

## Notes

* Temporary files written for the C program (e.g., `ref.fits`, `refstars.txt`, `img.fits`, `parms.txt`) live under your `--code-dir` and are overwritten each run; they reflect the **last processed CCD**. This is expected in sequential mode.
* Results (residuals, sources, lightcurves) are written under each CCD's subfolders.
* To run parallel processing, use the `feature/parallel` branch which provides `--workers` and isolated per-CCD scratch dirs.

---

## Citation

