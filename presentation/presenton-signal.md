# Presenton Signal Edition

Created on 1 November 2026 at the user's request to add character through
Presenton without losing the comparison plots. This is a new fifteen-slide
Greek presentation, not an overwrite of an earlier export or the local PPTX.
Its current remote links and creation IDs are in `latest-presenton.json`.
Download and preview links expire after 24 hours; IDs are provenance, not a
promise of permanent access. The preview was requested once using PPTX ID 24711;
Presenton resolves identical-HTML exports to the root creation 24709.

## Design

Presenton search selected design 18, **Bauhaus Signal**. Primary blue #185ADB,
signal red #F04438, yellow #F5C542 and ink #171717 give the talk stronger visual
structure. Technical diagrams, a geometric cover, asymmetrical layouts and
alternating white/dark sections replace the repeated plain text layout. White
evidence slides protect the original plots. League Spartan is used for Latin
display text, IBM Plex Sans for technical labels and Noto Sans for Greek copy;
all three have explicit Google Fonts imports. The original figure colors are
not recolored to match the theme.

## Required Evidence

| Slide | Preserved original image |
| --- | --- |
| 6 | `docs/assets/fig4_uniform_full.png` |
| 7 | `docs/assets/fig4_fidelity_full.png` |
| 10 | `results/fidelity-stage2-2026-10-28/exploratory-closest-full.png` |
| 11 | `results/revalidated-2026-10-25/sim-comparison/figure4-m5-pin-simulator.png` |
| 12 | `results/revalidated-2026-10-25/figures/trackers.png` |
| 13 | `results/revalidated-2026-10-25/figures/granularity.png` |

The primary comparison images keep all three rows, all six workloads, legends,
threshold colors, labels and footnotes. Images use `object-fit: contain`, without
cropping, masking, filters or replacement charts. The complete source score
table and the separate exploratory plot are retained. Editable text explains
coverage versus event counts using the verified real-input BFS counts (933M
accesses versus 62M fills). It does not imply equal traffic or cache irrelevance.

## Verified Snapshot and Limits

Stage 2 has 18/21 completed steps; three multithreaded controls remain held.
All six main simulator graph workloads are complete and audited; Liblinear is
active and BC window controls remain pending. The bounded real-input profiler
pilot is separate engineering work, not an M5 fidelity result or deployment
approval. Exact author inputs, WAC collection procedure and page denominator
remain evidence gaps. Failed RSS matching and negative controls remain in notes.
No measured application speedup or full M5 replication is claimed.

## Checks and Storage

The same final HTML was exported once to PPTX, PDF and PNG. Preflight and local
Chromium inspection found fifteen direct 1280x720 slides, fifteen speaker notes,
six fully loaded source images and no text overflow. All slides were reviewed
in a contact sheet; primary slides 6/7/11 were also inspected at full size.
Structural checks do not verify native PowerPoint rendering. Text is editable
where Presenton's conversion supports it; the preserved scientific figures are
raster images. No exported files were downloaded into the repository.

Working HTML and local renders were created only in a private Presenton OS
temporary directory and removed after delivery. Recreating this deck requires
fresh temporary HTML using the design brief and the verified source data; the
legacy local builders do not reproduce this style. Future data refreshes must
preserve these original plots and must not silently restore the old styling.
