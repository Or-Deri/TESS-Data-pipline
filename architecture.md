# Paloma — Architecture Proposal

**Status:** Partial implementation — **Cleaning** owned and implemented; other stages are *shields* (stubs).

## 1. Project Overview

Paloma is a data pipeline that takes light curve data (star brightness measured over time) and figures out what kind of astronomical phenomenon it shows.

The data comes from the TESS space telescope, supplied by Tequilla in FITS format. In the future, other sources of light curve data may be added.

Paloma reads a light curve, cleans it up, extracts useful information from it, and then classifies it as one of:

- **Transit** (possible exoplanet)
- **EB** (eclipsing binary star)
- **Dwarf star**
- **Unknown / other**

The system does this by passing each light curve through a fixed sequence of processing steps, one after another.

## 2. Pipeline Flow

```
Ingestion → Validation → Cleaning → Detrending → Normalization → Feature Extraction → Classification
```

Each stage takes the output of the previous stage, does one job, and passes its result to the next stage. If a stage fails (e.g. validation rejects the data), the pipeline stops early and does not continue to the next stages.

### Implementation ownership

| Stage | Status in this repo |
|---|---|
| Cleaning | **Owned / implemented** — `Cleaner` protocol + `CleaningStage` + dehazer (`paloma.cleaning`) |
| Ingestion, Validation, Detrending, Normalization, Feature Extraction, Classification | **Shield only** — `paloma.stages.shields.*` raise `NotImplementedError` if run |

## 3. Stage Responsibilities

### 1. Ingestion
- **Receives:** a raw FITS file (or reference to one).
- **Does:** reads the file and extracts the time and flux (brightness) arrays.
- **Returns:** a `LightCurve` object.
- **Code:** shield — `IngestionStage`.

### 2. Validation
- **Receives:** a `LightCurve`.
- **Does:** checks the data is usable — e.g. arrays are not empty, time and flux have matching lengths, no obviously broken values. Rejects the light curve if it's invalid.
- **Returns:** the same `LightCurve`, unchanged, if valid (otherwise stops the pipeline).
- **Code:** shield — `ValidationStage`.

### 3. Cleaning
- **Receives:** a validated `LightCurve` *(design target for light-curve cleaning)*.
- **Does:** removes bad data / scattered light so downstream stages see cleaner signal.
- **Returns:** a cleaned `LightCurve` *(design target)*.

> **Ownership / implementation:** this repo owns **cleaning**. The stage is defined
> against a pluggable `Cleaner` protocol (`clean(request) -> result`); cleaners
> self-register by name and the active one is chosen by
> `paloma.config.CleaningConfig`. `CleaningStage` holds the configured `Cleaner`
> and delegates.
>
> The first cleaner is `paloma.cleaning.dehazer_cleaner.DehazerCleaner` (engine:
> `paloma.cleaning.dehazer` — see [`docs/dehazer/README.md`](docs/dehazer/README.md)).
>
> Dehazing acts on FFI *image cubes*, so the live contract is directory-based
> `CleaningRequest` → `CleaningResult` (not `LightCurve` in / out). More cleaners
> can be registered without changing the stage.

### 4. Detrending
- **Receives:** a cleaned `LightCurve`.
- **Does:** removes slow trends in brightness (e.g. caused by the star itself or the instrument) so that short, real signals stand out.
- **Returns:** a detrended `LightCurve`.
- **Code:** shield — `DetrendingStage`.

### 5. Normalization
- **Receives:** a detrended `LightCurve`.
- **Does:** rescales the flux values to a common, comparable scale (e.g. centered around 1.0).
- **Returns:** a `ProcessedLightCurve`, ready for feature extraction.
- **Code:** shield — `NormalizationStage`.

### 6. Feature Extraction
- **Receives:** a `ProcessedLightCurve`.
- **Does:** computes numeric features that describe the shape of the light curve (e.g. depth, duration, period, symmetry).
- **Returns:** a `FeatureVector`.
- **Code:** shield — `FeatureExtractionStage`.

### 7. Classification
- **Receives:** a `FeatureVector`.
- **Does:** decides which category the light curve belongs to (transit, EB, dwarf star, or unknown).
- **Returns:** a `ClassificationResult`.
- **Code:** shield — `ClassificationStage`.

## 4. Design Patterns

### Pipeline
The whole system is one pipeline: a fixed, ordered list of stages that each transform data and hand it to the next stage. This makes the flow easy to follow and easy to test one stage at a time. Stage classes exist today; full end-to-end orchestration of all stages remains for owners of the non-cleaning steps.

### Chain of Responsibility
Each stage decides whether to pass the data forward or stop the chain. This is most important in **Validation**: if the data doesn't pass the check, the chain stops there and later stages never run. Every stage in the pipeline can, in principle, stop the chain if something goes wrong (e.g. cleaning ends up with no usable frames — `CleaningStage` returns `None`).

### Strategy
Some stages have more than one possible way to do their job, and we want to be able to swap the method without changing the pipeline itself. This project uses Strategy in:

- **Cleaning** — different cleaning algorithms plug in via the `Cleaner` protocol (registry + `CleaningConfig`); the first concrete cleaner is the dehazer. *(implemented)*
- **Detrending** — different detrending methods (e.g. median filter, spline fit) can be plugged in via a `DetrendingStrategy`. *(shield / future)*
- **Classification** — different classification methods (e.g. rule-based, ML model) can be plugged in via a `ClassificationStrategy`. *(shield / future)*

The stage itself just calls its strategy — it doesn't know or care which specific algorithm is used underneath.

## 5. Main Classes / Interfaces

```
PipelineStage (interface)
    run(input) -> output

IngestionStage         implements PipelineStage   # shield
ValidationStage        implements PipelineStage   # shield
CleaningStage          implements PipelineStage   # implemented
DetrendingStage        implements PipelineStage   # shield
NormalizationStage     implements PipelineStage   # shield
FeatureExtractionStage implements PipelineStage   # shield
ClassificationStage    implements PipelineStage   # shield
```

Strategy interfaces:

```
Cleaner (protocol)                         # implemented
    clean(CleaningRequest) -> CleaningResult | None

DetrendingStrategy (interface)             # future
    apply(light_curve) -> light_curve

ClassificationStrategy (interface)         # future
    classify(feature_vector) -> classification_result
```

`CleaningStage` holds a `Cleaner` and delegates to it (chosen by `CleaningConfig`).
`DetrendingStage` / `ClassificationStage` will hold their strategies once those stages are owned.

## 6. Data Objects

```
LightCurve                                 # shield type shell
    time: number[]
    flux: number[]
    metadata: dict

ProcessedLightCurve                        # shield type shell
    time: number[]
    flux: number[]
    metadata: dict

FeatureVector                              # shield type shell
    features: dict

ClassificationResult                       # shield type shell
    label: string           # "transit" | "EB" | "dwarf_star" | "unknown"
    confidence: number

CleaningRequest                            # implemented (cleaning I/O)
    input_dir: string
    output_dir: string
    params: dict
    metadata: dict

CleaningResult                             # implemented (cleaning I/O)
    input_dir: string
    output_dir: string
    outputs: string[]       # paths to cleaned FITS
    metadata: dict
```

## 7. Simple Execution Example

Full pipeline (once all stages are owned):

```python
stages = [
    IngestionStage(),
    ValidationStage(),
    CleaningStage.from_config(CleaningConfig(cleaner="dehazer")),
    DetrendingStage(strategy=MedianFilterDetrending()),
    NormalizationStage(),
    FeatureExtractionStage(),
    ClassificationStage(strategy=RuleBasedClassification()),
]

data = raw_fits_file
for stage in stages:
    data = stage.run(data)
    if data is None:
        break  # a stage rejected the data; stop the pipeline

result = data  # ClassificationResult, if the pipeline completed
```

Cleaning only (what this repo runs today):

```python
from paloma import CleaningStage, CleaningConfig, CleaningRequest

stage = CleaningStage.from_config(
    CleaningConfig(cleaner="dehazer", params={"num_frames": 5})
)
result = stage.run(
    CleaningRequest(
        input_dir="tests/data/groundtruth/raw",
        output_dir="results/cleaned",
    )
)
```
