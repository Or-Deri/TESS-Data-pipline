# Product Requirements Document — TESS Scattered-Light Removal, 3-D Spatio-Temporal Mode

> **Scope:** The **3-D (spatio-temporal)** dehazing pipeline only.
>
> This document has been split into a staged workflow. The full implementation
> contract lives at **[workflow/README.md](workflow/README.md)**.

## Stages

| Stage | File |
|---|---|
| Index + end-to-end ordering | [workflow/README.md](workflow/README.md) |
| 00 Foundations | [workflow/00-foundations.md](workflow/00-foundations.md) |
| 01 Setup | [workflow/01-setup.md](workflow/01-setup.md) |
| 02 Load & normalize | [workflow/02-load-normalize.md](workflow/02-load-normalize.md) |
| 03 Estimate airlight | [workflow/03-estimate-airlight.md](workflow/03-estimate-airlight.md) |
| 04 Smooth airlight | [workflow/04-smooth-airlight.md](workflow/04-smooth-airlight.md) |
| 05 Transmission | [workflow/05-transmission.md](workflow/05-transmission.md) |
| 06 Recover & save | [workflow/06-recover-save.md](workflow/06-recover-save.md) |
| 07 Ops | [workflow/07-ops.md](workflow/07-ops.md) |
| 08 Verification | [workflow/08-verification.md](workflow/08-verification.md) |
| Appendix | [workflow/appendix.md](workflow/appendix.md) |
| Final workflow diagram | [workflow/diagram.md](workflow/diagram.md) |
