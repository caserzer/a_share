"""Paired monthly comparisons; block resampling acknowledges overlapping labels."""
import numpy as np
import pandas as pd
from run_price_pilot import OUT


def run():
    dest = OUT / 'r03_information_probe'
    monthly = pd.read_csv(dest / 'monthly_scores.csv', parse_dates=['date'])
    pairs = [('valuation', 'technical'), ('financial', 'valuation'), ('full', 'financial'),
             ('macro_only_increment', 'technical'), ('full', 'recent24m_empirical')]
    rng = np.random.default_rng(24)
    results = []
    for horizon, g in monthly.groupby('horizon'):
        pivot = g.pivot(index='date', columns='model', values='quantile_loss').sort_index()
        block = 6 if horizon == 126 else 12
        for model, reference in pairs:
            diff = (pivot[model] - pivot[reference]).dropna()
            values = diff.to_numpy()
            means = []
            for _ in range(2000):
                starts = rng.integers(0, len(values), size=int(np.ceil(len(values) / block)))
                sample = np.concatenate([values[(s + np.arange(block)) % len(values)] for s in starts])[:len(values)]
                means.append(sample.mean())
            annual = diff.groupby(diff.index.year).mean()
            results.append({'horizon': horizon, 'model': model, 'reference': reference,
                'monthly_points': len(diff), 'block_months': block, 'mean_loss_delta': diff.mean(),
                'relative_loss_change': diff.mean() / pivot[reference].mean(),
                'block_interval_lower': np.quantile(means, .025), 'block_interval_upper': np.quantile(means, .975),
                'years_improved': int((annual < 0).sum()), 'years_total': len(annual)})
    frame = pd.DataFrame(results)
    frame.to_csv(dest / 'paired_comparisons.csv', index=False)
    print(frame.to_string(index=False))
    pred = pd.read_parquet(dest / 'predictions.parquet')
    pred['exchange'] = pred.instrument.str[:2]
    pred.groupby(['horizon', 'model', 'exchange'])[['quantile_loss', 'below_q05', 'coverage90']].mean().to_csv(
        dest / 'exchange_diagnostic.csv')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary = pd.read_csv(dest / 'summary.csv')
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout='constrained')
    for j, horizon in enumerate([126, 252]):
        s = summary[summary.horizon == horizon].set_index('model')
        s.quantile_loss.plot.barh(ax=axes[j, 0], color='#3c7195')
        axes[j, 0].set_title(f'{horizon} trading days: quantile loss (lower is better)')
        s.below_q05.mul(100).plot.barh(ax=axes[j, 1], color='#bd7054')
        axes[j, 1].axvline(5, color='black', linestyle='--', label='Nominal 5%')
        axes[j, 1].set_title('Realized frequency below predicted Q05 (%)')
        axes[j, 1].legend()
    fig.suptitle('EP24 R03 | 2021-2023 exploratory | price proxy, legacy universe')
    fig.savefig(dest / 'comparison.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    run()
