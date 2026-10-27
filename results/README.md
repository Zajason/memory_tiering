> **October 2026 audit:** Historical results below predate confirmed cache-path
> corrections. The window-fit causal explanation, HWT-gating explanation and
> 1.505x speedup claim are withdrawn. See [the audit](../docs/audit-2026-10.md) and
> [current methodology](../docs/methodology.md) for the corrected interpretation and paired
> access/miss measurements. Historical numerical agreement is not proof of replication.

# results/

The latest six-workload uniform-window scores and source manifests live in
`uniform-traffic10/` (Google+ BC/SSSP, synthetic other kernels) and
`uniform-kron-traffic10/` (all synthetic). See
[the completed campaign](../docs/uniform-windows.md). Only PageRank is close;
the other five curves still disagree substantially.

The input/window follow-up runs live in `matched-family/`: six completed
BC/SSSP runs plus four additional BFS/CC/PR/TC memory-window runs, source provenance,
compact paired histograms, `scores.csv` and
`comparison.csv`. It also uses the two `paired-v2/` synthetic reference runs.
See [the follow-up report](../docs/reproduction-followup.md). These results are
closer under memory-event windows, not an exact replication or CXL-device trace.
The parent `matched-family/scores.csv` is the BC/SSSP four-cell comparison;
the `uniform-*` score tables cover all six kernels. The table below is historical.

Raw `.pages.bin` dumps are **not kept** — they are gigabytes, gitignored, and
regenerable. Summaries, per-epoch CSVs and figures are kept.

| directory | what it is | still cited? |
|---|---|---|
| `spr-20t/` | GAPBS + liblinear, stock build, ROI on steady state | yes |
| `spr-20t-ul/` | GAPBS, user-space graph load — **the controller view**, the headline set | yes |
| `spr-1t/` | Redis, 4 MB CAT partition (M5's 1-way mask) | yes |
| `trackers/` | HPT/HWT accuracy vs hardware budget | yes |
| `sensitivity/` | epoch, cache, threads, scale, trials sweeps | yes |
| `figures-ul/`, `figures/` | paper-style plots | yes |
| `tracker-placement/` | per-epoch tracker top-K for the fair placement test | yes |
| `directed/` | **refuted hypothesis** — directed graph made bc/sssp worse | as a negative result |
| `scale25/`, `scale25-norm/` | **refuted hypothesis** — kron-25 at fixed and scaled windows | as a negative result |
| `window_probe/` | whole-run window bound, used for the bracketing argument | yes |

To regenerate everything: `make reproduce` (see the repository Makefile).
Numbers are verified against `docs/claims.md` by `./experiments/check_claims.sh`.
