# Paloma — PRD Section: Design Goals

**Status:** Design / Pre-implementation
**Parent document:** Product Requirements Document (PRD) for Paloma
**Related:** [architecture.md](./architecture.md)

---

## Overview

This section defines the engineering principles that govern how Paloma is designed and built. Paloma converts raw TESS FITS observations into structured, labeled, ML-ready datasets for exoplanet detection. Because the underlying science (detrending methods, feature engineering, vetting criteria) and the surrounding ecosystem (data sources, ML model architectures) are both expected to evolve continuously, the design goals below prioritize **structural flexibility and correctness of the data pipeline** over short-term implementation speed. Each goal below states what it means, why it matters specifically for Paloma, and how the architecture in `architecture.md` realizes it.

---

## 1. Modularity

**What it is:** The system is decomposed into independent modules (ingestion, catalog, preprocessing, features, labeling, datasets, pipeline orchestration) each with a single, well-defined responsibility and a narrow public interface.

**Why it matters for Paloma:** TESS data processing spans genuinely distinct concerns — parsing an instrument file format is a different skill and a different rate of change than implementing a transit-detection algorithm, which is different again from catalog cross-matching. Bundling these together produces a codebase where a change to one concern (e.g., a new detrending technique) risks breaking an unrelated one (e.g., dataset export). Astronomy pipelines in practice are maintained by mixed teams (data engineers, astronomers, ML engineers) who each primarily touch one module.

**How the architecture supports it:** The module breakdown in `architecture.md` §4 assigns each concern its own Python package (`ingestion/`, `preprocessing/`, `features/`, `labeling/`, `datasets/`, `pipeline/`) with an acyclic dependency graph (§4.1). Modules communicate only through a small set of shared domain types (`LightCurve`, `FeatureVector`, `CatalogEntry`, `LabeledRecord`) and the common `Stage` interface (§5), never through direct calls into each other's internals.

---

## 2. Separation of Concerns

**What it is:** Distinct responsibilities — file I/O, domain data modeling, scientific processing logic, and orchestration — are kept in separate layers that do not leak into one another.

**Why it matters for Paloma:** Without this discipline, it is easy for astronomy pipelines to end up with detrending code that also knows how to read FITS headers, or feature-extraction code that also knows about S3 paths — coupling that makes every part harder to test and harder to reason about, and makes it impossible to swap storage backends or file formats without touching scientific code.

**How the architecture supports it:** §5.3 of `architecture.md` states explicit boundary rules: only `ingestion` and `datasets` perform I/O, and only through the `io` storage abstraction; only `labeling` is permitted to combine feature data with catalog data. Every other module is a pure transformation over in-memory domain objects.

---

## 3. Clear Pipeline Stages

**What it is:** The transformation from raw FITS to ML-ready dataset is expressed as an explicit, ordered sequence of stages, each with a defined input type, output type, and responsibility — not an ad hoc script.

**Why it matters for Paloma:** Exoplanet-detection datasets are only trustworthy if every transformation applied to the raw signal (filtering, detrending, normalization) is known, inspectable, and attributable. An opaque, monolithic "process everything" function makes it impossible to answer "which stage introduced this artifact?" or to reproduce a dataset from a partial re-run.

**How the architecture supports it:** `architecture.md` §3 defines six explicit stages (Ingestion & Validation → Preprocessing → Feature Extraction → Catalog Cross-Match & Labeling → Dataset Assembly → Export), each with a documented input/output contract via the `Stage` interface (§5.2) and a manifest recording exactly which stages and parameters produced a given dataset (§10.5).

---

## 4. Extensibility

**What it is:** The system can accommodate new preprocessing techniques, new data sources, new feature extractors, and new missions by *adding* code, not modifying existing, tested code.

**Why it matters for Paloma:** TESS light-curve processing is an active research area — new detrending methods and vetting statistics are published regularly, and the project's own roadmap includes future missions beyond TESS (e.g., Kepler/K2 archival data, PLATO in the 2030s). A design that requires touching core pipeline code for every new technique would accumulate risk and slow down every subsequent addition.

**How the architecture supports it:** The config-driven `Stage` registry (§5.2, §9.1) means new preprocessing transforms, feature extractors, or data readers are registered by name and enabled via YAML configuration — the pipeline orchestrator and all other modules require zero changes. §9.2 shows explicitly how a new mission's reader plugs into the existing pipeline unchanged, because every reader's contract is simply "produce a `LightCurve`."

---

## 5. Easy Integration of New Data Sources

**What it is:** Onboarding a new raw-data source (a different TESS pipeline product, or a different mission entirely) should require writing one new adapter, not touching preprocessing, features, labeling, or dataset code.

**Why it matters for Paloma:** TESS itself has multiple light-curve products (SPOC, QLP) with different file layouts and quality-flag conventions, and the long-term ambition is to support additional missions. If downstream modules depended on source-specific file structure, every new source would require re-implementing (and re-testing) the entire pipeline.

**How the architecture supports it:** All ingestion readers converge on the single mission-agnostic `LightCurve` domain type (§5.1, §9.2). Every module from `preprocessing` onward is written against `LightCurve`, `FeatureVector`, and related types — never against a specific FITS layout — so a new `Reader` implementation is the entire integration cost.

---

## 6. Easy Integration of New Machine Learning Models

**What it is:** Paloma's output contract (dataset schema, feature definitions, label semantics) is stable and independent of any specific model architecture, so new models can consume Paloma's datasets without requiring changes to Paloma.

**Why it matters for Paloma:** Paloma is explicitly scoped as a data pipeline, not a modeling library (`architecture.md` §1.2). Exoplanet-detection modeling approaches vary widely (CNNs over folded light curves, gradient-boosted trees over tabular features, transformer-based sequence models) and will keep evolving; coupling the dataset format to one model's expected input shape would force a pipeline change every time the ML team tries a new architecture.

**How the architecture supports it:** The `datasets` module (§4, §9.3) produces a versioned, model-agnostic artifact — feature tables plus labels plus optional folded light-curve tensors — with schema and provenance recorded in a manifest. Model-specific reshaping or preprocessing is explicitly pushed to a thin adapter layer in the ML training repository, keeping that churn outside Paloma entirely.

---

## 7. Configuration Flexibility

**What it is:** Pipeline behavior (which preprocessing steps run, in what order, with what parameters; which feature extractors are enabled; how splits are computed) is declared in configuration, not hardcoded, and every run's configuration is captured for reproducibility.

**Why it matters for Paloma:** Researchers need to experiment with different detrending parameters or feature sets without code changes or redeploys, and every dataset used to train or evaluate a model must be exactly reproducible — a non-negotiable requirement when publishing or comparing exoplanet-detection results.

**How the architecture supports it:** `architecture.md` §7 and §9.1 describe a YAML-driven configuration schema (`paloma.config`) consumed solely by the pipeline orchestrator, with each stage receiving typed parameters rather than reading files itself. Every exported dataset ships with a manifest recording the exact configuration used to produce it (§10.5).

---

## 8. Maintainability

**What it is:** The codebase should remain easy to understand, debug, and modify as it grows, without requiring whole-system knowledge to make a local change.

**Why it matters for Paloma:** The project will be touched by contributors with different specialties (data engineering, astrophysics, ML) over an extended lifetime; a design that requires understanding the entire pipeline to fix a single bug does not scale with the team or the codebase.

**How the architecture supports it:** Strict module boundaries and a small, shared vocabulary of domain types (§4.1, §5.1) mean a contributor working on, say, detrending only needs to understand `preprocessing` and `models`. The acyclic dependency graph (§4.1) prevents hidden circular coupling that would otherwise force wide-reaching changes.

---

## 9. Testability

**What it is:** Every component can be tested in isolation, using small, synthetic inputs, without requiring real FITS files, network access, or a live catalog service.

**Why it matters for Paloma:** Astronomical edge cases (data gaps, cosmic-ray outliers, flagged cadences, injected synthetic transits) are exactly what a detection pipeline must handle correctly, and they are far easier to construct and verify as small synthetic fixtures than to hunt for in real data.

**How the architecture supports it:** Because every stage's interface is a pure function over typed domain objects (`LightCurve -> LightCurve`, `LightCurve -> FeatureVector`, etc.; §5.2), each can be unit-tested with hand-constructed synthetic light curves. The `io` storage abstraction (§4, §10.3) allows ingestion and dataset-writing code — the only I/O-touching modules — to be tested against an in-memory fake store instead of real storage.

---

## 10. Scalability

**What it is:** The pipeline should handle growth along two axes: more targets per run (a full TESS sector has on the order of hundreds of thousands of light curves) and more sectors/missions over time, without architectural rework.

**Why it matters for Paloma:** TESS has already observed nearly the entire sky across many sectors, and the roadmap includes additional missions; a pipeline that only works at small scale would need to be rebuilt rather than grown.

**How the architecture supports it:** Per-target stages (ingestion through labeling) have no shared mutable state and are explicitly designed as embarrassingly parallel (`architecture.md` §6.1, §10.2), allowing a scale-up path from single-process execution to multiprocessing or distributed execution (Dask/Ray) without interface changes. Dataset assembly, the one stage requiring a global view, is designed as streaming/partitioned aggregation specifically to avoid requiring all targets in memory at once (§6.1, §10.2).

---

## 11. Reliability

**What it is:** Pipeline runs should fail safely, be resumable, and never silently produce a corrupted or partially-invalid dataset.

**Why it matters for Paloma:** A dataset used to train an exoplanet-detection model is only as trustworthy as the pipeline that built it; silent data corruption or an undetected schema drift could produce a model that looks like it works but is learning from bad labels or malformed features — a failure mode that is expensive to detect after the fact.

**How the architecture supports it:** `architecture.md` §10.5 specifies that stages are designed to be idempotent (safe to retry), that intermediate artifacts are checkpointed per target (so an interrupted run does not require full reprocessing), and that validation gates run at ingestion (structural checks) and dataset assembly (schema and label-distribution sanity checks) to catch malformed data before it reaches a training set.

---

## 12. Performance

**What it is:** Processing must be efficient enough to handle full-sector volumes of light curves in practical wall-clock time, and the exported dataset formats must be efficient for downstream ML training to read.

**Why it matters for Paloma:** A pipeline that is correct but too slow to run over a full sector, or that exports data in a format expensive to load during training, defeats the purpose of automating dataset construction.

**How the architecture supports it:** Preprocessing and feature extraction are specified to be vectorized (NumPy/pandas/Astropy) and operate per-target for linear, parallelizable scaling (§10.4). Output formats are chosen specifically for training-time read performance: Parquet for columnar feature access, HDF5/TFRecord for chunked/memory-mapped array access to light-curve tensors (§7, §10.4).

---

## 13. Reusability

**What it is:** Core logic (a detrending transform, a feature extractor, a catalog cross-match routine) should be usable outside its original calling context — in a notebook, in a different pipeline configuration, or as a building block for a new stage.

**Why it matters for Paloma:** Astronomers and ML engineers frequently need to inspect or reuse a single processing step interactively (e.g., "run just the detrending step on this one target to visualize it") rather than only ever running the full pipeline end-to-end.

**How the architecture supports it:** Because every stage is a standalone class implementing the `Stage` interface over well-defined domain types rather than an inline step embedded in a larger script (§5.2), any individual transform, extractor, or labeler can be imported and invoked directly — in a notebook, a test, or a different pipeline configuration — without needing to run the full orchestrator.

---

## Summary Table

| Goal | Primary architectural mechanism |
|---|---|
| Modularity | Package-per-concern, acyclic dependency graph (§4) |
| Separation of Concerns | I/O and catalog-access boundary rules (§5.3) |
| Clear Pipeline Stages | Explicit six-stage flow with typed contracts (§3, §5.2) |
| Extensibility | Config-driven `Stage` registry (§5.2, §9) |
| Easy Integration of New Data Sources | Mission-agnostic `LightCurve` domain type (§5.1, §9.2) |
| Easy Integration of New ML Models | Model-agnostic dataset artifact + manifest (§9.3) |
| Configuration Flexibility | YAML-driven pipeline configuration (§7, §9.1) |
| Maintainability | Small shared vocabulary + strict module boundaries (§4.1) |
| Testability | Pure-function stage interfaces + `io` fakes (§5.2, §10.3) |
| Scalability | Per-target parallelism, streaming dataset assembly (§6.1, §10.2) |
| Reliability | Idempotent stages, checkpointing, validation gates (§10.5) |
| Performance | Vectorized processing, columnar/chunked export formats (§10.4) |
| Reusability | Standalone `Stage` implementations, importable independently (§5.2) |
