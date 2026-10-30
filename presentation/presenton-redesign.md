# Presenton English redesign

Created on 30 October 2026 at the user's explicit request to replace the previous
styling using the Presenton plugin. The earlier Greek and English PPTX files
remain unchanged.

## Design

Presenton design 14, Sage Authority, adapted for a research seminar: DM Serif
Display headlines, Manrope body text, near-white background, forest green,
sage and charcoal. Editorial columns, thin rules and quiet folios replace the
heavy black footer bars. No decorative icons, stock imagery or card grids.
Fonts are imported from Google Fonts.

Fifteen English slides retain an approximately fifteen-minute narrative and
speaker notes. The initial redesign replaced the main comparison figures with
alternate charts. The user rejected that evidence-presentation change: styling
must not replace the original comparison plots. The corrected version restores
the original figures intact on slides 6, 7 and 11. Five supplementary Chart.js
charts remain. Tracker and granularity slides show labelled subsets for
readability, not reference-selected best outcomes.

## Required main figures

Preserve the full six-workload bar plots, including all three rows, threshold
colors, legends, labels and footnotes. Do not replace them with line charts or
error-only summaries during future styling changes.

| Slide | Original image | Rows |
|---|---|---|
| 6 | `docs/assets/fig4_uniform_full.png` | M5 / accesses / modeled misses |
| 7 | `docs/assets/fig4_fidelity_full.png` | M5 / real-input accesses / modeled misses |
| 11 | `results/revalidated-2026-10-25/sim-comparison/figure4-m5-pin-simulator.png` | M5 / Pin / simulator |

These slides use nearly the whole canvas for the uncropped figure, with a small
editable heading. Only these three slides changed in the correction; the other
twelve are unchanged. The images were uploaded once each through Presenton and
loaded using the returned HTTPS asset URLs. Their source SHA-256 values are:

```text
uniform:  0ad64a22912a5c30cf0dd2c095e6ac2642a110995207282410e359d4d181d7f1
fidelity: 484ddcb24d0ccc2f1c29c8295a7531a4d734d17fbcc8c1c86ab149b1238b22d6
sim:      a6713f40b1a676a6486537cea44c132d4a16ab355aaf9db24d6ed113946aa352
```

## Evidence and boundaries

- Baseline: `results/uniform-traffic10/comparison.csv` and `scores.csv`.
- Real-input comparison: `results/fidelity-2026-10-27/scores.csv`.
- Simulator: `results/revalidated-2026-10-25/sim-comparison/comparison.csv`.
- Stage 2: `results/fidelity-stage2-2026-10-28/scores.csv` and `campaign.json`.
- TC footprint: `results/fidelity-stage2-2026-10-28/tc-footprint-candidates.json`.
- Extensions: validated JSON analyses under `results/revalidated-2026-10-25/analysis/`.

The snapshot shows all six simulator graph workloads complete and Pin stage 2
at 14/21 steps, with larger-input twenty-thread TC running. It preserves the
failed footprint match, negative controls, unavailable exact author inputs and
collection protocol, and the absence of measured application speedup. It does
not assert full M5 replication or a causal explanation for residual disagreement.

## Delivery and checks

Initial, superseded Presenton creation IDs: PPTX 24344, PDF 24345, PNG ZIP 24346.
Corrected creation IDs with the restored main plots: PPTX 24352, PDF 24353,
PNG ZIP 24354. The corrected preview was created once from 24352.
The original preview was created from 24344. Download and preview links expire after 24 hours; creation
IDs are provenance records, not a claim of permanent public access.

The same final HTML was exported to all three formats. Preflight found fifteen
direct 1280x720 slide children. Local Chromium checks confirmed fifteen notes,
eighteen nonblank canvases, loaded fonts and no text beyond slide bounds; all
slides were visually reviewed. The correction was checked separately for all
three fully loaded original images, five remaining charts and fifteen slides
and notes. All three corrected slides were visually reviewed. This is not
verification in native PowerPoint.
Chart canvases may be rasterized in the PPTX export.

Working HTML and renders were held only in a private Presenton temporary
directory and removed after delivery. Remote exports were not downloaded into
the repository, as required by the plugin workflow. Recreating the redesign
requires fresh temporary HTML based on this design brief and the recorded data;
the legacy local builders do not reproduce it.
