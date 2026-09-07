# Image Subtraction Workflow

End-to-end OIS pipeline (runs as **ImageSubtractionStage**, after cleaning):

1. [00-foundations](workflow/00-foundations.md) — OIS math
2. [01-setup](workflow/01-setup.md) — config & layout
3. [02-preprocess](workflow/02-preprocess.md) — cutout, WCS align
4. [03-build-reference](workflow/03-build-reference.md) — masters & star list
5. [04-optimal-subtract](workflow/04-optimal-subtract.md) — OIS core
6. [05-iterative-background](workflow/05-iterative-background.md) — 2-pass loop
7. [06-detect-sources](workflow/06-detect-sources.md) — cross-match
8. [07-extract-lightcurves](workflow/07-extract-lightcurves.md) — photometry
9. [08-verification](workflow/08-verification.md) — tests & tolerances

```python
PreprocessFrames >> BuildReference >> OptimalSubtract
    >> DetectAndCrossMatch >> ExtractLightCurves
```

## Pipeline placement

```
Cleaning → ImageSubtraction → Detrending → …
```

Image subtraction is **not** a `Cleaner`. Use `ImageSubtractionStage` and
`SubtractionRequest.from_cleaning(cleaning_result, output_dir)`.
