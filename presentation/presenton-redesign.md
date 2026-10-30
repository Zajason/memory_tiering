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
speaker notes. Eighteen Chart.js charts are rebuilt from verified numerical
outputs rather than shrinking report screenshots. Discrete threshold plots
retain a common 0-1 CDF axis. Tracker and granularity slides show labelled
subsets for readability, not reference-selected best outcomes.

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

Presenton creation IDs: PPTX 24344, PDF 24345, PNG ZIP 24346. One preview was
created from 24344. Download and preview links expire after 24 hours; creation
IDs are provenance records, not a claim of permanent public access.

The same final HTML was exported to all three formats. Preflight found fifteen
direct 1280x720 slide children. Local Chromium checks confirmed fifteen notes,
eighteen nonblank canvases, loaded fonts and no text beyond slide bounds; all
slides were visually reviewed. This is not verification in native PowerPoint.
Chart canvases may be rasterized in the PPTX export.

Working HTML and renders were held only in a private Presenton temporary
directory and removed after delivery. Remote exports were not downloaded into
the repository, as required by the plugin workflow. Recreating the redesign
requires fresh temporary HTML based on this design brief and the recorded data;
the legacy local builders do not reproduce it.
