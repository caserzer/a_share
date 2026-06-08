# Experiment Workspace

Experiment names are not fixed at project start. Copy
`templates/experiment_template/` into `pending/<short_slug>/` only after a
workstream has a concrete requirement, frozen label contract, and validation
gate.

Each experiment folder owns:

- `config.yaml`: all thresholds, paths, label contracts, gates, and data cutoff.
- `code/`: experiment-specific scripts only.
- `outputs/`: generated data, metrics, tables, figures, reports, manifests,
  publishable artifacts, local cache, and large raw artifacts.
- `tests/`: focused checks for the experiment contract.
- `notes/`: design notes, review notes, and decision logs.

Reusable code belongs in top-level `src/afml_big_winner/`, not inside an
experiment folder.
