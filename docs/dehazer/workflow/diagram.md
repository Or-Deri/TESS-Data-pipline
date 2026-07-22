# Final Workflow Diagram

Visual map of the 3-D dehazing workflow. Ordering is load-bearing — see
[`pipeline/orchestration.py`](../../../paloma/cleaning/dehazer/pipeline/orchestration.py). Stage docs:
[index](README.md).

---

## Stage overview

Doc stages and how they relate to the runtime pipeline.

```mermaid
flowchart TB
  subgraph docs [Documentation stages]
    S00["00 Foundations"]
    S01["01 Setup"]
    S02["02 Load and normalize"]
    S03["03 Estimate airlight"]
    S04["04 Smooth airlight"]
    S05["05 Transmission"]
    S06["06 Recover and save"]
    S07["07 Ops"]
    S08["08 Verification"]
    SApp["Appendix"]
  end

  S00 --> S01 --> S02 --> S03 --> S04 --> S05 --> S06
  S01 -.-> S07
  S07 -.-> S02
  S06 --> S08
  S00 -.-> SApp
  S08 --> SApp
```

---

## Runtime pipeline (final data flow)

Artifacts produced at each step. Do not fuse the loops marked below.

```mermaid
flowchart LR
  subgraph input [Input]
    FITS["FITS sequence *.fits"]
  end

  subgraph stage02 [02 Load and normalize]
    Cube["cube N,H,W float64 in 0-1"]
    Meta["metadata orig_min orig_max filename"]
  end

  subgraph stage03 [03 Step 1 Airlight]
    RawA["raw_airlights A_0 .. A_N-1"]
  end

  subgraph stage04 [04 Step 2 Smooth A]
    SmoothA["smoothed A series sigma=1.5"]
  end

  subgraph stage05 [05 Step 3 Transmission]
    TRaw["per-frame t_i guided filter"]
    TSmooth["smoothed t_cube axis 0"]
  end

  subgraph stage06 [06 Step 4 Recover]
    L["L recovered then denormalized"]
    Out["dehazed__*.fits"]
  end

  FITS --> Cube
  FITS --> Meta
  Cube --> RawA
  RawA --> SmoothA
  Cube --> TRaw
  SmoothA --> TRaw
  TRaw --> TSmooth
  Cube --> L
  SmoothA --> L
  TSmooth --> L
  Meta --> L
  L --> Out
```

---

## Ordered checklist (must not fuse)

```mermaid
flowchart TD
  Start["dehaze"] --> GPU["resolve_gpu 07"]
  GPU --> Discover["discover sort cap FITS 02"]
  Discover --> Batch["for each batch"]
  Batch --> Load["load crop global_norm 02"]
  Load --> LoopA["for all frames: patches pairs estimate_airlight 03"]
  LoopA --> SmoothA["gaussian_filter1d on A 04"]
  SmoothA --> LoopT["for all frames: recover_transmission_map using smoothed A 05"]
  LoopT --> SmoothT["gaussian_filter_temporal on t_cube 05"]
  SmoothT --> LoopR["for all frames: recover denormalize save 06"]
  LoopR --> Batch
  Batch --> Marker["OUTPUT_LOCATION.txt 06"]
  Marker --> Done["done"]
```

> Airlight for **all** frames before smoothing $A$. Transmission for **all**
> frames from **smoothed** $A$ before smoothing $t$. Recovery uses **smoothed**
> $A$ and **smoothed** $t$.

---

## Stage ↔ code

| Stage | Primary code |
|---|---|
| 02 | [`io/fits_io.py`](../../../paloma/cleaning/dehazer/io/fits_io.py), [`io/normalize.py`](../../../paloma/cleaning/dehazer/io/normalize.py) |
| 03 | [`core/patches.py`](../../../paloma/cleaning/dehazer/core/patches.py), [`core/airlight.py`](../../../paloma/cleaning/dehazer/core/airlight.py) |
| 04 | [`workflow/stages.py`](../../../paloma/cleaning/dehazer/workflow/stages.py) (`SmoothAirlight`) + `gaussian_filter1d` |
| 05 | [`core/transmission.py`](../../../paloma/cleaning/dehazer/core/transmission.py), [`core/guided_filter.py`](../../../paloma/cleaning/dehazer/core/guided_filter.py), [`core/backend.py`](../../../paloma/cleaning/dehazer/core/backend.py) |
| 06 | [`core/recovery.py`](../../../paloma/cleaning/dehazer/core/recovery.py), [`io/fits_io.py`](../../../paloma/cleaning/dehazer/io/fits_io.py) |
| 07 | [`pipeline/orchestration.py`](../../../paloma/cleaning/dehazer/pipeline/orchestration.py), [`core/backend.py`](../../../paloma/cleaning/dehazer/core/backend.py) |
| 08 | [`evaluation/simulation.py`](../../../paloma/cleaning/dehazer/evaluation/simulation.py) |
