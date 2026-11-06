"""Run the full-history extension without modifying any V1 artifact."""
from datetime import datetime, timezone
import argparse
import json
import pandas as pd
from core import (EP, OLD, OUT, CACHE, SOURCES, v1, write_json, build_panel,
                  load_members, assign, benchmark_data, states, score, detail)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-panel', action='store_true')
    args = parser.parse_args()
    write_json(OUT / 'audits/run_start.json', dict(status='working',
        started_at=datetime.now(timezone.utc).isoformat(), plan_sha256=v1.sha(EP / 'research_plan.md'),
        sources={p.name: v1.sha(p) for p in sorted((EP / 'src').glob('*.py'))},
        predecessor_v1_manifest_sha256=v1.sha(OLD / 'outputs/manifest.json'),
        beta_meaning='same_horizon_return_difference', no_regression_beta=True))
    if args.build_panel or not (CACHE / 'panel.parquet').exists():
        panel, aliases, source = build_panel()
    else:
        source = json.loads((OUT / 'audits/inputs.json').read_text())
        assert v1.sha(CACHE / 'panel.parquet') == source['panel_sha256']
        panel = pd.read_parquet(CACHE / 'panel.parquet')
        aliases = json.loads((CACHE / 'aliases.json').read_text())
    meta = json.loads((SOURCES / 'manifest.json').read_text())
    for r in meta['benchmarks']:
        assert v1.sha(SOURCES / (r['code'] + '.parquet')) == r['sha256']
    members = load_members(aliases)
    joined = assign(panel, members)
    print('V2 assignments', len(joined), flush=True)
    history, futures = benchmark_data(panel)
    origins, state, runs = states(joined, panel, history)
    detail('origin_states', origins)
    print('V2 states', len(state), 'leading runs', len(runs), flush=True)
    result, paths = score(joined, origins, panel, futures)
    from report_v2 import build
    build(result, state, runs, source)
    write_json(OUT / 'audits/run_complete.json', dict(status='working_result_ready_for_validation',
        completed_at=datetime.now(timezone.utc).isoformat(), outcome_rows=len(result),
        event_stock_path_rows=len(paths), strict_PIT='BLOCKED_DATA', sealed=False))
    print('V2 observation complete; independent validation pending', flush=True)


if __name__ == '__main__':
    main()
