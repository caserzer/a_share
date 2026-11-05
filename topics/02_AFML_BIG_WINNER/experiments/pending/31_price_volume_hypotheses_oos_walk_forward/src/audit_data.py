"""Independent denominator and missing-price reconciliation supplement to P1."""
import json

import numpy as np
import pandas as pd

from build_data import compare_monthly
from common import OUT, cache, sha, utc_now, write_json
from ep30_adapter import EP30Adapter
from labels_and_maturity import infer_labels
from walk_forward import load_features


def main():
    a = EP30Adapter()
    no_prices = [r for r in a.inventory.itertuples() if f"normalized/prices_qfq/{r.security_id}.parquet" not in a.files]
    missing_reconcile = []
    b = pd.DataFrame({k: pd.Series(dtype='datetime64[ns]' if k == 'date' else 'object' if k in {'factor_chain_id', 'factor_source_sha256'} else 'float64')
                      for k in ['date', 'open', 'volume', 'qfq_open', 'qfq_close', 'factor_chain_id', 'factor_source_sha256']})
    for h in [20, 60, 120, "6_calendar_months"]:
        name = str(h)+"_sessions" if isinstance(h, int) else h
        old = a.read(f"normalized/labels/{name}_price.parquet")
        for s in no_prices:
            f = old.loc[old.security_id.eq(s.security_id)]
            if len(f):
                r = compare_monthly(infer_labels(b, a.days, f.date, h, s.delist_date), f)
                if r['mismatches'] or r['rows'] != r['compared']:
                    raise ValueError('missing-price reconciliation mismatch')
                missing_reconcile.append(dict(horizon=name, security_id=s.security_id, **r))
    initial = pd.read_csv(OUT/'audits/monthly_reconciliation.csv')
    extra = pd.DataFrame(missing_reconcile).groupby('horizon').sum(numeric_only=True).reset_index()
    full = pd.concat([initial, extra]).groupby('horizon').sum(numeric_only=True).reset_index()
    full.to_csv(OUT/'audits/monthly_reconciliation_full.csv', index=False)
    pd.DataFrame(missing_reconcile).to_csv(OUT/'audits/missing_price_reconciliation.csv', index=False)
    f = load_features()
    summary = []
    for (year, board), g in f.groupby([f.date.dt.year, 'board']):
        summary.append(dict(year=int(year), board=board, eligible_weekly=int(g.weekly.fillna(False).sum()),
                            observed_weekly=int((g.weekly.fillna(False)&g.observed.fillna(False)).sum()),
                            warmup_weekly=int((g.weekly.fillna(False)&g.warmup.fillna(False)).sum()),
                            unknown_or_insufficient=int((g.weekly.fillna(False)&~(g.observed.fillna(False)&g.warmup.fillna(False))).sum()),
                            h10_episode=int(g.h10_episode.fillna(False).sum()), h11_episode=int(g.h11_episode.fillna(False).sum()),
                            eligible_delisted_weekly=int((g.weekly.fillna(False)&g.is_delisted.fillna(False)).sum())))
    pd.DataFrame(summary).to_csv(OUT/'audits/population_by_year_board.csv', index=False)
    # Complete ancestry links; no outcome is added to any predictor.
    timeline = f[['security_id','date','known_at','feature_start','weekly','h10_episode','h11_episode']].copy()
    timeline['t0'] = timeline.date+pd.Timedelta(hours=15)
    timeline.to_parquet(cache()/'data_timeline.parquet', index=False)
    write_json(OUT/'audits/data_gate.json', dict(status='PASS_PROXY_ONLY', verified_at=utc_now(),
               monthly_rows=int(full.rows.sum()), monthly_mismatches=int(full.mismatches.sum()),
               missing_price_rows_reconciled=int(extra.rows.sum()), no_quote_securities=len(no_prices),
               timeline_path=str(cache()/'data_timeline.parquet'), timeline_sha256=sha(cache()/'data_timeline.parquet'),
               full_industry_risk_adjustment='BLOCKED_DATA', independent_shares='BLOCKED_DATA',
               H09='BLOCKED_DATA', strict_PIT='BLOCKED_DATA', execution_certification='BLOCKED_DATA'))


if __name__ == '__main__':
    main()
