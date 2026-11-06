"""Execute the adaptive-stage redo with preserved predecessors and fresh outputs."""
from datetime import datetime, timezone
import argparse
import json
import pandas as pd
from context import EP, OUT, CACHE, THRESHOLDS, POLICIES, BENCHMARKS, baseline, js, sha
from data import prepare, industry_paths, benchmarks
from stages import discover
from scoring import stage_scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--reports-only', action='store_true')
    args = parser.parse_args()
    baseline()
    if args.reports_only:
        phases = pd.read_csv(CACHE / 'all_natural_stages.csv')
        scores = pd.concat([pd.read_csv(CACHE / f'stage_scores_T{int(t*100)}.csv') for t in THRESHOLDS], ignore_index=True)
        stocks = pd.concat([pd.read_csv(CACHE / f'stock_scores_T{int(t*100)}.csv') for t in THRESHOLDS], ignore_index=True)
        paths = pd.read_parquet(CACHE / 'industry_paths.parquet')
        source = json.loads((OUT / 'audits/inputs.json').read_text())
        js('audits/report_refresh', dict(status='working_report_refresh',
            at=datetime.now(timezone.utc).isoformat(), no_new_fit_or_stage_selection=True,
            reason='unique report module name avoids predecessor module collision; stock screen joined on phase/policy/benchmark',
            sources={p.name: sha(p) for p in sorted((EP / 'src').glob('*.py'))}))
        from report_adaptive import build
        build(phases, scores, stocks, paths, source)
        js('audits/run_complete', dict(status='working_result_awaiting_validation', phases=len(phases), scores=len(scores),
            stock_rows=len(stocks), no_forward_confirmation=True, sealed=False))
        print('V4 reports regenerated from saved stage and stock measurements', flush=True)
        return
    js('audits/run_start', dict(status='working', started_at=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(EP / 'research_plan.md'), thresholds=THRESHOLDS, valuation_policies=POLICIES,
        benchmarks=BENCHMARKS, min_months=6, max_months=18, split_long_stages=False,
        sources={p.name: sha(p) for p in sorted((EP / 'src').glob('*.py'))}))
    if args.prepare or not (CACHE / 'panel_with_tail.parquet').exists():
        panel, joined, marks, source = prepare()
    else:
        source = json.loads((OUT / 'audits/inputs.json').read_text())
        for name, field in [('panel_with_tail.parquet', 'panel_sha256'), ('valuation_marks.parquet', 'marks_sha256'),
                            ('assignments_with_tail_return.parquet', 'assignments_sha256')]:
            assert sha(CACHE / name) == source[field]
        panel = pd.read_parquet(CACHE / 'panel_with_tail.parquet')
        joined = pd.read_parquet(CACHE / 'assignments_with_tail_return.parquet')
        marks = pd.read_parquet(CACHE / 'valuation_marks.parquet')
    paths = industry_paths(panel, joined)
    phases = discover(paths)
    print('V4 natural stages', len(phases), flush=True)
    scores, stocks, stock_paths = stage_scores(phases, panel, joined, marks, benchmarks())
    from report_adaptive import build
    build(phases, scores, stocks, paths, source)
    js('audits/run_complete', dict(status='working_result_awaiting_validation',
        completed_at=datetime.now(timezone.utc).isoformat(), phases=len(phases), scores=len(scores),
        stock_rows=len(stocks), path_rows=len(stock_paths), no_forward_confirmation=True, sealed=False))
    print('V4 adaptive stages complete; validation pending', flush=True)


if __name__ == '__main__':
    main()
