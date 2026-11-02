# CSLab research talk

The current user-approved direction is the Greek Presenton **Signal Edition**,
documented in `presenton-signal.md`; `latest-presenton.json` identifies its remote
exports and preview. Consult that pointer first when asked for the latest deck.
It supersedes the styling of both local builders below and the earlier English
Presenton redesign in `presenton-redesign.md`. Do not deliver or rebuild a plain
local deck as a substitute for the Presenton version without explaining it.
Presenton exports are remote snapshots, not files rebuilt by `build.mjs` or
`build-en.mjs`; do not silently refresh shared previews.

Fifteen slides for approximately fifteen minutes. The editable slide text,
figures, native score table and speaker notes are built from verified outputs.
The local snapshots below retain the historical paper/black/red style.

`collect_data.py` snapshots completed score rows and current pending states.
`build.mjs` writes a new, timestamped PPTX under
`~/Downloads/CSLab_Presentation/current-*/output/`, renders every slide and runs
the presentation integrity/layout/import validators. It does not overwrite the
original draft. `latest.json` records the latest validated output path locally.
Presentation artifacts are not measurement evidence.

The latest reviewed PPTX and Greek notes are also copied to this directory as
`CSLab_Memory_Tiering_Current.pptx` and `speaker-notes-el.md` for repository access.

The separate English version preserves the same fifteen-slide design, figures,
score table and scientific limitations. Its reproducible source is `build-en.mjs`;
the reviewed outputs are `CSLab_Memory_Tiering_English.pptx` and
`speaker-notes-en.md`. Run it with the bundled Node executable:

```bash
node presentation/build-en.mjs
```

English builds use `~/Downloads/CSLab_Presentation/english-*/output/` and record
their path in the local, ignored `latest-en.json`. They do not replace the Greek
deck or its `latest.json` pointer. Neither builder updates the Presenton preview.

```bash
.venv/bin/python src/analysis/publish_fidelity.py
.venv/bin/python src/analysis/publish_revalidation.py
.venv/bin/python src/analysis/publish_pin_stage2.py
.venv/bin/python presentation/collect_data.py
# Use the Node executable returned by load_workspace_dependencies:
node presentation/build.mjs
```

The local builder uses the bundled Artifact Tool runtime. Override `CODEX_RUNTIME`
and `PRESENTATIONS_SKILL` if its location changes. All six primary simulator graph
runs, including PR and TC, have completed and passed validation. Stage
2 exploratory closest-case plots are shown only after a control completes and
remain explicitly labelled as reference-selected, not independent replication.

## Signal Edition, rebuilt locally (3 Νοεμβρίου 2026)

`CSLab_Memory_Tiering_Signal_EL.pptx` + `speaker-notes-signal-el.md`, built by
`build_signal_el.mjs`. This exists because the 1 November Presenton Signal
Edition became unretrievable: its preview JWT expired 2026-11-02 12:58, all
three export URLs were 24-hour, and `presenton-signal.md` records that the
source HTML lived only in a temporary directory and was deleted after delivery.
`CSLab_Memory_Tiering_Current.pptx` is dated 11-01 06:17 -- six hours *before*
the Signal design brief -- so it is the older paper/black/red local build, not
that edition.

The rebuild keeps the declared Signal design (#185ADB / #F04438 / #F5C542 /
#171717, League Spartan / IBM Plex Sans / Noto Sans, fifteen slides) and
preserves the evidence plots uncropped via `sizing: contain`. It is built with
pptxgenjs rather than the Codex artifact runtime, so it is reproducible here.

Greek all-caps drops the monotonic accent; `elUpper()` handles that, because
`toUpperCase()` alone yields "ΤΟ ΠΡΌΒΛΗΜΑ".

Run it with the Node in the Codex runtime cache:

```bash
~/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  presentation/build_signal_el.mjs
```
