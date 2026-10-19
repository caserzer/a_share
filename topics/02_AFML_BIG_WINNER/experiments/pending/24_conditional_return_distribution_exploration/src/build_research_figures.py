"""Compact, reproducible figures from retained experiment results."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/ep24-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from run_price_pilot import OUT


def run():
    dest = OUT / 'report'
    dest.mkdir(exist_ok=True)
    pred = pd.read_parquet(OUT / 'r05_holdout/predictions.parquet')
    pred = pred[pred.mature & pred.actual.notna()].copy()
    pred['observed_up'] = (pred.actual > 0).astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout='constrained')
    for ax, h in zip(axes, [126, 252]):
        p = pred[pred.horizon == h]
        actual = p[p.model == 'expanding_empirical'].groupby('date').observed_up.mean()
        ax.plot(actual.index, actual, color='black', label='Observed cross-sectional up frequency')
        for model, name in [('expanding_empirical','Historical baseline'), ('peers_valuation','Valuation peers'),('catboost_full','Full CatBoost')]:
            s = p[p.model == model].groupby('date').p_up.mean()
            ax.plot(s.index, s, label=name)
        ax.set_title(f'{h}-session forecasts: predicted vs realized')
        ax.set_ylim(0,1)
        ax.tick_params(axis='x', rotation=35)
        ax.legend(fontsize=8)
    fig.suptitle('EP24 | Historical validation | Common market shocks are not independent stock trials')
    fig.savefig(dest / 'probability_drift.png', dpi=160)
    plt.close(fig)
    nav = pd.read_parquet(OUT / 'r06_portfolio_probe/daily_nav.parquet')
    matched = pd.read_parquet(OUT / 'r07_sensitivities/matched_gross_nav.parquet')
    fig, ax = plt.subplots(figsize=(12,5), layout='constrained')
    for style, label in [('all_equal','Full pool equal weight'),('selected_equal','Same selected pool equal weight'),
                          ('distribution_full','Distribution weights, full exposure'),('distribution_dynamic','Distribution weights, dynamic exposure')]:
        g=nav[(nav.model=='peers_valuation') & (nav.fee==.001) & (nav['style']==style)]
        ax.plot(g.date,g.nav/1e6,label=label)
    g=matched[(matched.model=='peers_valuation') & (matched.fee==.001)]
    ax.plot(g.date,g.nav/1e6,linestyle='--',label='Full pool, SAME dynamic gross exposure (posthoc control)')
    ax.set_title('EP24 allocation diagnostic | valuation peers | 10 bp per traded side')
    ax.set_ylabel('NAV / initial capital')
    ax.legend(fontsize=9)
    fig.savefig(dest / 'allocation_comparison.png',dpi=160)
    plt.close(fig)


if __name__=='__main__':
    run()
