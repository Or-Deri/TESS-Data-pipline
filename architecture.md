# Paloma — Architecture Proposal

**Status:** Design / pre-implementation

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

## 3. Stage Responsibilities

### 1. Ingestion
- **Receives:** a raw FITS file (or reference to one).
- **Does:** reads the file and extracts the time and flux (brightness) arrays.
- **Returns:** a `LightCurve` object.

### 2. Validation
- **Receives:** a `LightCurve`.
- **Does:** checks the data is usable — e.g. arrays are not empty, time and flux have matching lengths, no obviously broken values. Rejects the light curve if it's invalid.
- **Returns:** the same `LightCurve`, unchanged, if valid (otherwise stops the pipeline).

### 3. Cleaning
- **Receives:** a validated `LightCurve`.
- **Does:** removes bad data points — e.g. flagged/missing values and extreme outliers.
- **Returns:** a cleaned `LightCurve`.

### 4. Detrending
- **Receives:** a cleaned `LightCurve`.
- **Does:** removes slow trends in brightness (e.g. caused by the star itself or the instrument) so that short, real signals stand out.
- **Returns:** a detrended `LightCurve`.

### 5. Normalization
- **Receives:** a detrended `LightCurve`.
- **Does:** rescales the flux values to a common, comparable scale (e.g. centered around 1.0).
- **Returns:** a `ProcessedLightCurve`, ready for feature extraction.

### 6. Feature Extraction
- **Receives:** a `ProcessedLightCurve`.
- **Does:** computes numeric features that describe the shape of the light curve (e.g. depth, duration, period, symmetry).
- **Returns:** a `FeatureVector`.

### 7. Classification
- **Receives:** a `FeatureVector`.
- **Does:** decides which category the light curve belongs to (transit, EB, dwarf star, or unknown).
- **Returns:** a `ClassificationResult`.

## 4. Design Patterns

### Pipeline
The whole system is one pipeline: a fixed, ordered list of stages that each transform data and hand it to the next stage. This makes the flow easy to follow and easy to test one stage at a time.

### Chain of Responsibility
Each stage decides whether to pass the data forward or stop the chain. This is most important in **Validation**: if the data doesn't pass the check, the chain stops there and later stages never run. Every stage in the pipeline can, in principle, stop the chain if something goes wrong (e.g. cleaning ends up with an empty light curve).

### Strategy
Some stages have more than one possible way to do their job, and we want to be able to swap the method without changing the pipeline itself. This project uses Strategy in:

- **Detrending** — different detrending methods (e.g. median filter, spline fit) can be plugged in via a `DetrendingStrategy`.
- **Classification** — different classification methods (e.g. rule-based, ML model) can be plugged in via a `ClassificationStrategy`.

The stage itself just calls its strategy — it doesn't know or care which specific algorithm is used underneath.

## 5. Main Classes / Interfaces

```
PipelineStage (interface)
    run(input) -> output

IngestionStage         implements PipelineStage
ValidationStage        implements PipelineStage
CleaningStage          implements PipelineStage
DetrendingStage        implements PipelineStage
NormalizationStage     implements PipelineStage
FeatureExtractionStage implements PipelineStage
ClassificationStage    implements PipelineStage
```

Strategy interfaces, used by the stages that need swappable behavior:

```
DetrendingStrategy (interface)
    apply(light_curve) -> light_curve

ClassificationStrategy (interface)
    classify(feature_vector) -> classification_result
```

`DetrendingStage` holds a `DetrendingStrategy` and delegates to it.
`ClassificationStage` holds a `ClassificationStrategy` and delegates to it.

## 6. Data Objects

```
LightCurve
    time: number[]
    flux: number[]
    metadata: dict          # e.g. source, target id

ProcessedLightCurve
    time: number[]
    flux: number[]          # cleaned, detrended, normalized
    metadata: dict

FeatureVector
    features: dict          # e.g. { depth, duration, period, ... }

ClassificationResult
    label: string           # "transit" | "EB" | "dwarf_star" | "unknown"
    confidence: number
```

## 7. Simple Execution Example

```python
stages = [
    IngestionStage(),
    ValidationStage(),
    CleaningStage(),
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

