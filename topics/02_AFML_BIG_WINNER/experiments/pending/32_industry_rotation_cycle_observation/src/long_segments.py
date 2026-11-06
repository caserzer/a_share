"""A01: explicitly retrospective conditional description of long leading runs.

Added after inspecting v1 summaries. Never used as an origin-time selector.
This reads saved measurements only; it does not modify the entry definition.
"""
import gzip
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from observe import EP, OUT, CACHE, csv
from report import table, pct


def main():
    runs = pd.read_csv(OUT / 'metrics/leading_runs.csv')
    details = OUT / 'metrics/top3_outcomes.csv'
    compressed = details.with_suffix('.csv.gz')
    if details.exists():
        data = details.read_bytes()
        compressed.write_bytes(gzip.compress(data, mtime=0))
        CACHE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(details), str(CACHE / 'top3_outcomes.csv'))
    outcomes = pd.read_csv(compressed)
    long = runs[(runs.window == 12) & ~runs.left_censored & ~runs.right_censored & runs.months.between(12, 18)]
    joined = long.rename(columns={'months': 'run_months'}).merge(
        outcomes, left_on=['level', 'industry_code', 'start'], right_on=['level', 'industry_code', 'month'],
        how='left', suffixes=('_run', ''))
    joined['selected_with_future_duration'] = True
    csv('metrics/retrospective_long_segments', joined)
    rows = []
    for level in ['L2', 'L3']:
        for horizon in [9, 12]:
            g = joined[joined.level.eq(level) & joined.horizon.eq(horizon) & joined.members.ge(5)]
            k = g[g.mature & g.complete]
            paths = k.joint_positive_run.dropna()
            rows.append(dict(level=level, horizon=horizon, complete_long_runs=len(long[long.level.eq(level)]),
                             ranked_runs=len(g), mature=int(g.mature.sum()), known=len(k),
                             unknown=int((g.mature & ~g.complete).sum()), censored=int((~g.mature).sum()),
                             mean_return_median=k.mean_return.median(), all_positive_rate=k.all_positive.eq(True).mean(),
                             worst_return_median=k.worst_return.median(),
                             known_paths=len(paths), joint_ge9_fraction=paths.ge(9).mean()))
    summary = pd.DataFrame(rows)
    csv('metrics/retrospective_long_summary', summary)
    display = pd.DataFrame({'层级': summary.level, '期限/月': summary.horizon,
        '已结束12—18月段': summary.complete_long_runs, '排名完整段': summary.ranked_runs,
        '终点已知段': summary.known, '三股均涨': summary.all_positive_rate.map(pct),
        '组合涨幅中位': summary.mean_return_median.map(pct),
        '最差股涨幅中位': summary.worst_return_median.map(pct),
        '共同盈利≥9月': summary.joint_ge9_fraction.map(pct)})
    details = joined[joined.level.eq('L2') & joined.horizon.eq(12)].copy()
    details = details.sort_values(['start', 'industry_code'])
    shown = pd.DataFrame({'行业': details.industry_name, '开始': details.start, '结束': details.end,
        '领先/月': details.run_months, '固定前三/当前名称': details.display_names_current,
        '12月组合收益': details.mean_return.map(pct), '最差股收益': details.worst_return.map(pct),
        '三股共同盈利最长/月': details.joint_positive_run})
    text = ('# A01：事后观察到的12—18月长段，前三表现怎样\n\n'
        '**这是已看过第一版汇总后追加的描述性分组。** 选组使用未来才知道的完整领先时长；'
        '不能作为事前选行业或预测有效的证据，不改变原有进入事件与全样本分母。'
        '数据仍为Historical-proxy，严格PIT为BLOCKED_DATA。\n\n'
        f'同时观察到起点和终点、时长在12—18个月的12月强度领先段：二级{len(long[long.level.eq("L2")])}段、三级{len(long[long.level.eq("L3")])}段。'
        '有些段缺完整市值排名，不能给它们伪造前三；全部段和缺失都留在明细中。\n\n' + table(display) +
        '\n这更贴近“确实出现长行情时，前三是否普遍受益”的事后问题。组合中位收益提高，'
        '但三股同时正收益仍非普遍，且不能把正收益称作已经达到“涨幅不错”。'
        '累计盈利保持9个月也不等于连续9个月每月上涨。\n\n'
        '以下列出排名完整的全部二级长段，按开始时间排序，同时保留上涨和下跌案例；公司名称只作当前展示。\n\n' +
        table(shown) + '\n[全部长段含缺失](../outputs/metrics/retrospective_long_segments.csv)；'
        '[汇总与分母](../outputs/metrics/retrospective_long_summary.csv)。\n')
    (EP / 'reports/05_retrospective_long_segments.md').write_text(text)
    overview = EP / 'reports/first_observation.md'
    overview.write_text(overview.read_text().split('\n追加观察A01：')[0])
    with overview.open('a') as stream:
        stream.write('\n追加观察A01：[事后12—18月长段与前三的全部案例](05_retrospective_long_segments.md)。'
                     '该分组含未来选择，只用于描述现象。\n\n' + table(display))
    figures = EP / 'reports/figures'
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    for ax, level in zip(axes, ['L2', 'L3']):
        for window in [1, 6, 12]:
            f = runs[(runs.level == level) & (runs.window == window) & ~runs.left_censored & ~runs.right_censored]
            ax.hist(f.months, bins=np.arange(.5, 26.5), histtype='step', label=f'{window}m lookback', linewidth=1.5)
        ax.axvspan(11.5, 18.5, alpha=.12, color='green')
        ax.set(title=level + ': completed price-leading runs', xlabel='Consecutive months', ylabel='Count', yscale='log')
        ax.legend()
    fig.savefig(figures / 'duration_distribution.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    for ax, level in zip(axes, ['L2', 'L3']):
        valid = outcomes[(outcomes.level == level) & outcomes.horizon.eq(12) & outcomes.mature & outcomes.complete & outcomes.members.ge(5)]
        future = joined[joined.level.eq(level) & joined.horizon.eq(12) & joined.mature & joined.complete & joined.members.ge(5)]
        for label, f in [('All complete-ranked months', valid), ('Leading entry events', valid[valid.entry_event]),
                         ('12-18m runs (hindsight)', future)]:
            x = np.sort(f.mean_return.dropna())
            ax.step(x, np.arange(1, len(x) + 1) / len(x), where='post', label=label)
        ax.set(title=level + ': top-3 12m price returns', xlabel='Return', ylabel='Empirical CDF', xlim=(-1, 2))
        ax.axvline(0, color='grey', linewidth=.7)
        ax.legend(fontsize=8)
    fig.savefig(figures / 'top3_return_distribution.png', dpi=160)
    plt.close(fig)
    price = pd.read_csv(OUT / 'metrics/industry_price_series.csv')
    p = price[price.level.eq('L2')].copy()
    p['rank'] = p.groupby('month').strength12.rank(pct=True)
    mat = p.pivot(index='industry_code', columns='month', values='rank')
    fig, ax = plt.subplots(figsize=(12, 14), layout='constrained')
    im = ax.imshow(mat, aspect='auto', interpolation='nearest', vmin=0, vmax=1, cmap='RdYlBu_r')
    ax.set_yticks(np.arange(len(mat)), mat.index, fontsize=4)
    loc = np.arange(0, len(mat.columns), 6)
    ax.set_xticks(loc, mat.columns[loc], rotation=45)
    ax.set(title='SW L2: trailing-12m relative-strength percentile (historical proxy)', xlabel='Observation month', ylabel='L2 industry index code')
    fig.colorbar(im, ax=ax, label='Cross-sectional percentile; blank = unavailable')
    fig.savefig(figures / 'l2_rotation_heatmap.png', dpi=150)
    plt.close(fig)
    with overview.open('a') as stream:
        stream.write('\n![全部二级行业相对强度](figures/l2_rotation_heatmap.png)\n\n'
                     '![领先段长度分布](figures/duration_distribution.png)\n\n'
                     '![前三收益分布](figures/top3_return_distribution.png)\n')
    print('A01 retrospective description and figures complete')


if __name__ == '__main__':
    main()
