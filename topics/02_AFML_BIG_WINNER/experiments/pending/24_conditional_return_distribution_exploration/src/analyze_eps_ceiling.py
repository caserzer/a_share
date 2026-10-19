"""Optimistic bound for the actual R19 fallback/50% mixture structure.

This uses outcomes and is strictly an oracle diagnostic, never a candidate.
For a 50% mixture with a point mass at the true outcome, Brier and CRPS
are 25% of B's errors on adjusted rows; unadjusted rows retain B.
"""
import numpy as np
import pandas as pd
from prepare_panel import OUT
from build_eps_panel import PANEL
from fetch_eps_reports import DEST
from run_eps_ablation import GROUPS


def analyze():
    panel = pd.read_parquet(PANEL)
    fit = pd.read_csv(DEST/'fit_audit.csv')
    rows = []
    for horizon in [1, 3, 6]:
        base = pd.read_parquet(OUT/f'r15_three_factor_ablation/predictions_{horizon}m.parquet')
        base = base[base.model.eq('B') & base.actual.notna()].copy()
        flags = ['eps_positive', 'earnings_positive', 'earnings_pair_available']
        base = base.merge(panel[['date', 'instrument']+flags], on=['date', 'instrument'], validate='one_to_one')
        base['accuracy'] = np.where(base.actual.ne(0), (base.p_up > base.p_down) == (base.actual > 0), np.nan)
        for model in fit.model.unique():
            flag = GROUPS[model][0] if model in GROUPS else 'earnings_pair_available'
            counts = fit[(fit.months == horizon) & fit.model.eq(model)].set_index('date').training_rows
            mature = base.date.dt.strftime('%Y-%m-%d').map(counts)
            assert mature.notna().all()
            adjusted = base[flag] & mature.ge(1000)
            # Perfect candidate's up/down probabilities are known only ex post.
            perfect_up = .5*base.p_up + .5*base.actual.gt(0)
            perfect_down = .5*base.p_down + .5*base.actual.lt(0)
            mixed_accuracy = np.where(base.actual.ne(0), (perfect_up > perfect_down) == (base.actual > 0), np.nan)
            for metric in ['brier', 'multiclass_brier', 'crps', 'accuracy']:
                optimistic = mixed_accuracy if metric == 'accuracy' else .25*base[metric]
                data = base[['date', metric]].copy()
                data['oracle'] = np.where(adjusted, optimistic, base[metric])
                scores = data.groupby('date')[[metric, 'oracle']].mean().mean()
                ceiling = scores.oracle/scores[metric]-1 if metric == 'accuracy' else 1-scores.oracle/scores[metric]
                rows.append(dict(months=horizon, model=model, metric=metric,
                    relative_improvement_ceiling=ceiling, twenty_percent_possible=bool(ceiling >= .2),
                    adjusted_observed_rows=int(adjusted.sum()),
                    warning='ORACLE ONLY: future outcomes are used to bound this architecture; not a forecast or achieved score.'))
    result = pd.DataFrame(rows)
    result.to_csv(DEST/'mixture_ceiling_oracle_only.csv', index=False)
    return result


if __name__ == '__main__':
    print(analyze().drop(columns='warning').to_string(index=False))
