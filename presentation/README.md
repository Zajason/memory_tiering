# Greek CSLab research talk

Fifteen slides for approximately fifteen minutes. The editable slide text,
figures, native score table and speaker notes are built from verified outputs.
The restrained paper/black/red visual style follows the revised research talk.

`collect_data.py` snapshots completed score rows and current pending states.
`build.mjs` writes a new, timestamped PPTX under
`~/Downloads/CSLab_Presentation/current-*/output/`, renders every slide and runs
the presentation integrity/layout/import validators. It does not overwrite the
original draft. `latest.json` records the latest validated output path locally.
Presentation artifacts are not measurement evidence.

The latest reviewed PPTX and Greek notes are also copied to this directory as
`CSLab_Memory_Tiering_Current.pptx` and `speaker-notes-el.md` for repository access.

```bash
.venv/bin/python src/analysis/publish_fidelity.py
.venv/bin/python src/analysis/publish_revalidation.py
.venv/bin/python src/analysis/publish_pin_stage2.py
.venv/bin/python presentation/collect_data.py
# Use the Node executable returned by load_workspace_dependencies:
node presentation/build.mjs
```

The local builder uses the bundled Artifact Tool runtime. Override `CODEX_RUNTIME`
and `PRESENTATIONS_SKILL` if its location changes. A future completed simulator
PR or TC run enters its figure after the simulator publisher validates it. Stage
2 exploratory closest-case plots are shown only after a control completes and
remain explicitly labelled as reference-selected, not independent replication.
