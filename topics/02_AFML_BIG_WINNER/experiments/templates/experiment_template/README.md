# Experiment Template

This is a copyable scaffold, not a fixed experiment. Rename the copied folder
only after the research requirement is frozen.

Expected flow:

1. Copy this directory to `experiments/pending/<short_slug>/`.
2. Update `config.yaml` with the workstream, label contract, data cutoff, and
   validation gates.
3. Keep experiment-only code in `code/`.
4. Write small reviewable outputs to `outputs/publishable/`.
5. Keep bulky generated state in `outputs/local_cache/` or
   `outputs/large_raw/`.
6. Record every completed run in `outputs/manifests/`.

Smoke run from the project root:

```bash
uv run python experiments/templates/experiment_template/code/run.py
```
