# PRD Section: Design Goals

**Status:** Design goals (still apply) — **Cleaning** is the first area implemented under these principles; other stages remain shields.
**Parent document:** Product Requirements Document (PRD) for Paloma
**Related:** [architecture.md](./architecture.md)

---

## Overview

This section defines the engineering principles that govern how Paloma is designed and built. Paloma converts raw TESS FITS observations into structured, labeled, ML-ready datasets for exoplanet detection. Because the underlying science (detrending methods, feature engineering, vetting criteria) and the surrounding ecosystem (data sources, ML model architectures) are both expected to evolve continuously, the design goals below prioritize **structural flexibility and correctness of the data pipeline** over short-term implementation speed. Each goal below states what it means, why it matters specifically for Paloma, and how the architecture in `architecture.md` realizes it.

### Current ownership note

This repository currently **owns the cleaning area** (`Cleaner` protocol, `CleaningStage`, dehazer under `paloma.cleaning`). Other pipeline stages exist only as *shields* (stubs). The goals below still describe the full system; cleaning is the first concrete realization of Extensibility, Configuration Flexibility, Testability, and Reusability via a config-selected `Cleaner` registry.

---

## 1. Modularity

**What it is:** The system is decomposed into independent modules (ingestion, catalog, preprocessing, features, labeling, datasets, pipeline orchestration) each with a single, well-defined responsibility and a narrow public interface.

**Why it matters for Paloma:** TESS data processing spans genuinely distinct concerns — parsing an instrument file format is a different skill and a different rate of change than implementing a transit-detection algorithm, which is different again from catalog cross-matching. Bundling these together produces a codebase where a change to one concern (e.g., a new detrending technique) risks breaking an unrelated one (e.g., dataset export). Astronomy pipelines in practice are maintained by mixed teams (data engineers, astronomers, ML engineers) who each primarily touch one module.

**How the architecture supports it:** Stages communicate through shared domain types and the common `PipelineStage` interface (`architecture.md` §5), never through direct calls into each other's internals. Cleaning is isolated under `paloma.cleaning` / `CleaningStage`; other stages are shields until their owners implement them.

---

## 2. Separation of Concerns

**What it is:** Distinct responsibilities — file I/O, domain data modeling, scientific processing logic, and orchestration — are kept in separate layers that do not leak into one another.

**Why it matters for Paloma:** Without this discipline, it is easy for astronomy pipelines to end up with detrending code that also knows how to read FITS headers, or feature-extraction code that also knows about S3 paths — coupling that makes every part harder to test and harder to reason about, and makes it impossible to swap storage backends or file formats without touching scientific code.

**How the architecture supports it:** Cleaning separates the stage (`CleaningStage`) from algorithms (`Cleaner` implementations). The dehazer engine lives under `paloma.cleaning.dehazer`; the stage depends only on the `Cleaner` protocol. Other stages will follow the same boundary when owned.

---

## 3. Clear Pipeline Stages

**What it is:** The transformation from raw FITS to ML-ready dataset is expressed as an explicit, ordered sequence of stages, each with a defined input type, output type, and responsibility — not an ad hoc script.

**Why it matters for Paloma:** Exoplanet-detection datasets are only trustworthy if every transformation applied to the raw signal (filtering, detrending, normalization) is known, inspectable, and attributable. An opaque, monolithic "process everything" function makes it impossible to answer "which stage introduced this artifact?" or to reproduce a dataset from a partial re-run.

**How the architecture supports it:** `architecture.md` §2–§3 define the ordered stages with typed contracts via `PipelineStage`. Cleaning is implemented; remaining stages are named shields so the sequence stays visible in code.

---

## 4. Extensibility

**What it is:** The system can accommodate new preprocessing techniques, new data sources, new feature extractors, and new missions by *adding* code, not modifying existing, tested code.

**Why it matters for Paloma:** TESS light-curve processing is an active research area — new detrending methods and vetting statistics are published regularly, and the project's own roadmap includes future missions beyond TESS (e.g., Kepler/K2 archival data, PLATO in the 2030s). A design that requires touching core pipeline code for every new technique would accumulate risk and slow down every subsequent addition.

**How the architecture supports it:** Cleaning already uses a registry/factory (`register_cleaner` / `create_cleaner`) selected by `CleaningConfig` — new cleaners are added by writing a `@register_cleaner` class, not by changing `CleaningStage`. The same Strategy pattern is planned for detrending and classification (`architecture.md` §4).

---

## 5. Easy Integration of New Data Sources

**What it is:** Onboarding a new raw-data source (a different TESS pipeline product, or a different mission entirely) should require writing one new adapter, not touching preprocessing, features, labeling, or dataset code.

**Why it matters for Paloma:** TESS itself has multiple light-curve products (SPOC, QLP) with different file layouts and quality-flag conventions, and the long-term ambition is to support additional missions. If downstream modules depended on source-specific file structure, every new source would require re-implementing (and re-testing) the entire pipeline.

**How the architecture supports it:** Downstream stages are written against mission-agnostic domain types (`LightCurve`, `FeatureVector`, etc.; `architecture.md` §6). Ingestion remains a shield until owned; cleaning today operates on FFI directories via `CleaningRequest` / `CleaningResult`.

---

## 6. Easy Integration of New Machine Learning Models

**What it is:** Paloma's output contract (dataset schema, feature definitions, label semantics) is stable and independent of any specific model architecture, so new models can consume Paloma's datasets without requiring changes to Paloma.

**Why it matters for Paloma:** Paloma is explicitly scoped as a data pipeline, not a modeling library. Exoplanet-detection modeling approaches vary widely (CNNs over folded light curves, gradient-boosted trees over tabular features, transformer-based sequence models) and will keep evolving; coupling the dataset format to one model's expected input shape would force a pipeline change every time the ML team tries a new architecture.

**How the architecture supports it:** Classification and dataset export remain future work; the stable `FeatureVector` / `ClassificationResult` type shells in `architecture.md` §6 define the intended model-facing vocabulary.

---

## 7. Configuration Flexibility

**What it is:** Pipeline behavior (which preprocessing steps run, in what order, with what parameters; which feature extractors are enabled; how splits are computed) is declared in configuration, not hardcoded, and every run's configuration is captured for reproducibility.

**Why it matters for Paloma:** Researchers need to experiment with different detrending parameters or feature sets without code changes or redeploys, and every dataset used to train or evaluate a model must be exactly reproducible — a non-negotiable requirement when publishing or comparing exoplanet-detection results.

**How the architecture supports it:** Cleaning selects its algorithm and parameters via `CleaningConfig` (`cleaner` name + `params`). Broader YAML-driven pipeline config remains the long-term target once more stages are owned.

---

## 8. Maintainability

**What it is:** The codebase should remain easy to understand, debug, and modify as it grows, without requiring whole-system knowledge to make a local change.

**Why it matters for Paloma:** The project will be touched by contributors with different specialties (data engineering, astrophysics, ML) over an extended lifetime; a design that requires understanding the entire pipeline to fix a single bug does not scale with the team or the codebase.

**How the architecture supports it:** Ownership is stage-scoped. A cleaner author works in `paloma.cleaning` against the `Cleaner` protocol; shield stages mark unfinished ownership without mixing unfinished logic into cleaning.

---

## 9. Testability

**What it is:** Every component can be tested in isolation, using small, synthetic inputs, without requiring real FITS files, network access, or a live catalog service.

**Why it matters for Paloma:** Astronomical edge cases (data gaps, cosmic-ray outliers, flagged cadences, injected synthetic transits) are exactly what a detection pipeline must handle correctly, and they are far easier to construct and verify as small synthetic fixtures than to hunt for in real data.

**How the architecture supports it:** Cleaning is covered by `tests/` (synthetic FITS + optional full-resolution ground truth under `tests/data/groundtruth/`). Each `PipelineStage` remains a standalone `run` method, so future stages can be unit-tested the same way.

---

## 10. Scalability

**What it is:** The pipeline should handle growth along two axes: more targets per run (a full TESS sector has on the order of hundreds of thousands of light curves) and more sectors/missions over time, without architectural rework.

**Why it matters for Paloma:** TESS has already observed nearly the entire sky across many sectors, and the roadmap includes additional missions; a pipeline that only works at small scale would need to be rebuilt rather than grown.

**How the architecture supports it:** Per-target / per-batch stages without shared mutable state remain the scaling path (`architecture.md`). The dehazer already supports batching over FFI frames; broader distributed execution is future work.

---

## 11. Reliability

**What it is:** Pipeline runs should fail safely, be resumable, and never silently produce a corrupted or partially-invalid dataset.

**Why it matters for Paloma:** A dataset used to train an exoplanet-detection model is only as trustworthy as the pipeline that built it; silent data corruption or an undetected schema drift could produce a model that looks like it works but is learning from bad labels or malformed features — a failure mode that is expensive to detect after the fact.

**How the architecture supports it:** Stages may return `None` to stop the chain (chain-of-responsibility). Cleaning returns `None` when no cleaned frames are produced. Ground-truth tests pin dehazer numeric output for regression safety.

---

## 12. Performance

**What it is:** Processing must be efficient enough to handle full-sector volumes of light curves in practical wall-clock time, and the exported dataset formats must be efficient for downstream ML training to read.

**Why it matters for Paloma:** A pipeline that is correct but too slow to run over a full sector, or that exports data in a format expensive to load during training, defeats the purpose of automating dataset construction.

**How the architecture supports it:** Cleaning uses vectorized NumPy/SciPy/OpenCV (optional GPU via CuPy). Dataset export formats remain future work for the dataset/classification owners.

---

## 13. Reusability

**What it is:** Core logic (a detrending transform, a feature extractor, a catalog cross-match routine) should be usable outside its original calling context — in a notebook, in a different pipeline configuration, or as a building block for a new stage.

**Why it matters for Paloma:** Astronomers and ML engineers frequently need to inspect or reuse a single processing step interactively (e.g., "run just the detrending step on this one target to visualize it") rather than only ever running the full pipeline end-to-end.

**How the architecture supports it:** `CleaningStage` and each `Cleaner` are importable and runnable alone; the dehazer also exposes `python -m paloma.cleaning.dehazer`. Shield stages keep the same `PipelineStage` shape for future owners.

---

## Summary Table

| Goal | Primary architectural mechanism | Cleaning status |
|---|---|---|
| Modularity | Package-per-concern, `PipelineStage` boundaries | Cleaning isolated under `paloma.cleaning` |
| Separation of Concerns | Stage vs algorithm (`Cleaner` protocol) | Implemented |
| Clear Pipeline Stages | Explicit ordered stages with typed contracts | Cleaning real; others shields |
| Extensibility | Config-driven cleaner registry | Implemented for cleaning |
| Easy Integration of New Data Sources | Mission-agnostic domain types | Types shelled; ingestion shield |
| Easy Integration of New ML Models | Model-agnostic feature/label types | Type shells only |
| Configuration Flexibility | `CleaningConfig` (broader YAML later) | Cleaning configurable |
| Maintainability | Stage ownership + shields | Cleaning owned |
| Testability | Standalone stages + fixtures | `tests/` for dehazer |
| Scalability | Per-batch / per-target design | Dehazer batching |
| Reliability | Chain stop on `None` + ground truth | Implemented for cleaning |
| Performance | Vectorized scientific stack | Dehazer engine |
| Reusability | Importable stages / CLI | Cleaning + dehazer CLI |
