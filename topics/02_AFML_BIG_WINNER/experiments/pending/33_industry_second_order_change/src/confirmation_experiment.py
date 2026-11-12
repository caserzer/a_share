"""R02 frozen single-filter and joint-filter ablations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from price_experiment import EP, HORIZONS, block_interval, digest


def main():
    panel = pd.read_parquet('/tmp/ep33_r01_panel.parquet')
    out = EP / 'outputs/r02'
    out.mkdir(parents=True, exist_ok=True)
    selected, cov, metrics = [], [], []
    for date, rows in panel.groupby('date', sort=True):
        base = rows[rows.acceleration.notna() & rows.coverage.ge(.8) & rows.members.ge(5)]
        for kind, pool in [('decelerating_decline', base[base.velocity.lt(0)&base.acceleration.gt(0)]),
                           ('accelerating_improvement', base[base.velocity.ge(0)&base.acceleration.gt(0)])]:
            p = pool.persistence.ge(.8)
            b = pool.breadth_change.gt(0) & pool.breadth_acceleration.gt(0)
            for variant, mask in [('persistent', p), ('breadth', b), ('joint', p&b)]:
                filtered = pool[mask]
                k = min(10, len(filtered), len(pool))
                cov.append(dict(date=date, pool=kind, variant=variant, pool_n=len(pool),
                                filtered_n=len(filtered), k=k,
                                missing_breadth=int(pool.breadth_acceleration.isna().sum())))
                if k == 0:
                    continue
                arms = {
                    'filtered_acceleration': filtered.sort_values(['acceleration','industry_code'],ascending=[False,True]).head(k),
                    'filtered_velocity': filtered.sort_values(['velocity','industry_code'],ascending=[False,True]).head(k),
                    'unfiltered_acceleration': pool.sort_values(['acceleration','industry_code'],ascending=[False,True]).head(k),
                }
                for arm, g in arms.items():
                    g = g.copy()
                    g['pool'], g['variant'], g['arm'] = kind, variant, arm
                    selected.append(g)
                    r = dict(date=date, pool=kind, variant=variant, arm=arm, selected=k)
                    for h in HORIZONS:
                        r[f'known{h}'] = int(g[f'excess{h}'].notna().sum())
                        r[f'complete{h}'] = bool(g[f'excess{h}'].notna().all())
                        r[f'excess{h}'] = g[f'excess{h}'].mean()
                        r[f'adverse{h}'] = g[f'adverse{h}'].mean()
                    metrics.append(r)
    selected = pd.concat(selected, ignore_index=True)
    selected.to_csv(out/'selected.csv.gz',index=False)
    pd.DataFrame(cov).to_csv(out/'coverage.csv',index=False)
    metrics = pd.DataFrame(metrics)
    metrics.to_csv(out/'date_metrics.csv',index=False)
    pairs = []
    for (pool, variant), g in metrics.groupby(['pool','variant']):
        a = g[g.arm.eq('filtered_acceleration')].set_index('date')
        for control in ['filtered_velocity','unfiltered_acceleration']:
            c = g[g.arm.eq(control)].set_index('date')
            for h in HORIZONS:
                ix = a.index.intersection(c.index)
                ix = ix[a.loc[ix,f'complete{h}'] & c.loc[ix,f'complete{h}']]
                delta = a.loc[ix,f'excess{h}'] - c.loc[ix,f'excess{h}']
                monthly = delta.groupby(delta.index.to_period('M')).mean()
                ci = block_interval(monthly)
                pairs.append(dict(pool=pool,variant=variant,control=control,horizon=h,dates=len(ix),months=len(monthly),
                                  delta=monthly.mean(),ci_low=ci[0],ci_high=ci[1],
                                  adverse_delta=(a.loc[ix,f'adverse{h}']-c.loc[ix,f'adverse{h}']).mean()))
    pd.DataFrame(pairs).to_csv(out/'paired.csv',index=False)
    (out/'receipt.json').write_text(json.dumps({'quality':'Historical-proxy','stage':'adaptive_exploration',
        'inputs':{str(p):digest(p) for p in [Path('/tmp/ep33_r01_panel.parquet'),EP/'rounds/r02_plan.md',Path(__file__)]}},indent=2)+'\n')
    print(pd.DataFrame(pairs).query('horizon==126').to_string(index=False))

if __name__=='__main__':
    main()
