# results/

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
