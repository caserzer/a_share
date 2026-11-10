"""Frozen V28 true detections: first early signal close to ex-post cycle peak.

No model training or policy change. Exact-boundary unions are descriptive
deduplication, not a newly backtested ensemble or independent event sample.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT.parent
CACHE = Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
OUT = ROOT / 'outputs'
TASK = ['frequency', 'threshold', 'benchmark', 'level']
PATH_KEY = ['era', 'level', 'industry_code', 'block']
CYCLE = PATH_KEY + ['start_date', 'peak_date']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False, default=str) + '\n')


def stats(frame):
    return dict(cycles=len(frame), mean_return=float(frame.return_to_peak.mean()),
                median_return=float(frame.return_to_peak.median()),
                mean_days=float(frame.days_to_peak.mean()),
                median_days=float(frame.days_to_peak.median()))


def table(rows):
    header = '|口径|周期记录数|平均涨幅|中位涨幅|平均自然日|中位自然日|\n|---|---:|---:|---:|---:|---:|\n'
    return header + '\n'.join(
        f"|{r['scope']}|{r['cycles']}|{r['mean_return']:.2%}|{r['median_return']:.2%}|{r['mean_days']:.2f}|{r['median_days']:.2f}|"
        for r in rows) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []

    def check(name, condition):
        assert bool(condition), name
        checks.append(name)

    previous = EXT / 'v28_aggregate_acceptance'
    manifest = json.loads((previous / 'outputs/manifest.json').read_text())
    frozen = {previous / f['path']: f['sha256'] for f in manifest['files']}
    frozen[previous / 'outputs/manifest.json'] = sha(previous / 'outputs/manifest.json')
    check('V28 frozen artifacts unchanged', all(sha(p) == h for p, h in frozen.items()))
    refs = json.loads((EXT / 'v27_regime_threshold_review/outputs/frozen_policy.json').read_text())
    audit = json.loads((EXT / 'v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text())
    sources = {
        previous / 'outputs/historical_alerts.csv.gz': None,
        CACHE / 'stage_b_labels.parquet': refs['labels_sha256'],
        CACHE / 'daily_phases.parquet': refs['phases_sha256'],
        CACHE / 'daily_industries.parquet': audit['daily_sha256'],
    }
    for path, expected in sources.items():
        actual = sha(path)
        check('input hash ' + path.name, expected is None or actual == expected)
        sources[path] = actual
    alerts = pd.read_csv(previous / 'outputs/historical_alerts.csv.gz', parse_dates=['date'])
    labels = pd.read_parquet(CACHE / 'stage_b_labels.parquet')
    phases = pd.read_parquet(CACHE / 'daily_phases.parquet')
    daily = pd.read_parquet(CACHE / 'daily_industries.parquet')
    check('original alert population', len(alerts) == 20308 and alerts.date.between('2021-01-01', '2024-09-30').all())
    joined = alerts.merge(labels, on=['row_id', 'threshold', 'benchmark'], validate='one_to_one')
    joined.loc[joined.label_available_at.gt(joined.date + pd.DateOffset(months=24)), 'y'] = np.nan
    counts = dict(alerts=len(joined), known=int(joined.y.notna().sum()),
                  unknown=int(joined.y.isna().sum()), positive=int(joined.y.eq(1).sum()),
                  negative=int(joined.y.eq(0).sum()))
    check('same known and unknown labels as acceptance', counts['known'] == 11841 and counts['unknown'] == 8467)
    positive = joined[joined.y.eq(1)].copy()
    # First positive alert per task/phase; no repeated weekly alerts in an event.
    hits = positive.sort_values(['date', 'row_id']).drop_duplicates(TASK + ['event_or_witness_id'])
    expected = pd.read_csv(previous / 'outputs/independent_metrics.csv').query("model == 'accepted'")
    actual = hits.groupby(TASK).size().rename('computed').reset_index().merge(expected, on=TASK, validate='one_to_one')
    check('all 36 task event counts reproduce V28', len(actual) == 36 and actual.computed.eq(actual.detected_events).all())
    hits = hits.merge(phases, left_on=['event_or_witness_id', 'era', 'level', 'industry_code', 'threshold'],
                      right_on=['phase_id', 'era', 'level', 'industry_code', 'threshold'], validate='many_to_one')
    check('only qualified confirmed phases', hits.status.eq('CONFIRMED').all() and
          (~hits.left_censored).all() and hits.in_range_6_18.all() and
          all(row['qualified_' + row['benchmark']] for row in hits.to_dict('records')))
    check('first hit within early 3 calendar months',
          hits.start_date.le(hits.date).all() and hits.start_date.gt(hits.date - pd.DateOffset(months=3)).all())
    check('peak is stage end', hits.peak_date.eq(hits.end_date).all())
    price_columns = PATH_KEY + ['date', 'nav']
    check('daily path keys unique', not daily.duplicated(PATH_KEY + ['date']).any())
    for date_column, nav_column in [('date', 'signal_nav'), ('start_date', 'start_nav'), ('peak_date', 'peak_nav')]:
        prices = daily[price_columns].rename(columns={'date': date_column, 'nav': nav_column})
        hits = hits.merge(prices, on=PATH_KEY + [date_column], how='left', validate='many_to_one')
    check('all price endpoints exist and positive', hits[['signal_nav', 'start_nav', 'peak_nav']].notna().all().all()
          and hits[['signal_nav', 'start_nav', 'peak_nav']].gt(0).all().all())
    hits['return_to_peak'] = hits.peak_nav / hits.signal_nav - 1
    hits['days_to_peak'] = (hits.peak_date - hits.date).dt.days
    hits['signal_delay_days'] = (hits.date - hits.start_date).dt.days
    check('return matches independently stored whole-phase return', np.allclose(
        hits.return_to_peak, (1 + hits.industry_return) / (hits.signal_nav / hits.start_nav) - 1,
        atol=1e-12, rtol=1e-12))
    check('positive remaining duration and nonnegative return', hits.days_to_peak.gt(0).all() and hits.return_to_peak.ge(-1e-12).all())
    paths = {key: frame.set_index('date').nav.sort_index() for key, frame in daily.groupby(PATH_KEY)}
    peak_checks = []
    for row in hits.to_dict('records'):
        path = paths[tuple(row[k] for k in PATH_KEY)]
        peak_checks.append(np.isclose(path.loc[row['start_date']:row['peak_date']].max(), row['peak_nav'], atol=1e-12, rtol=1e-12))
    check('all peaks equal maximum of original within-cycle daily path', all(peak_checks))

    order = ['date', 'frequency', 'threshold', 'benchmark', 'row_id']
    unique = hits.sort_values(order).drop_duplicates(CYCLE).copy()
    per_frequency = hits.sort_values(order).drop_duplicates(['frequency'] + CYCLE).copy()
    check('exact-boundary union unique', not unique.duplicated(CYCLE).any())
    rows = [dict(scope='全部频率合并、相同起止去重', **stats(unique))]
    for frequency, name in [('W', '周度'), ('BW', '双周'), ('M', '月度')]:
        rows.append(dict(scope=name + '、相同起止去重', **stats(per_frequency[per_frequency.frequency.eq(frequency)])))
    pd.DataFrame(rows).to_csv(OUT / 'summary.csv', index=False)
    task_rows = [dict(zip(TASK, key), **stats(frame)) for key, frame in hits.groupby(TASK)]
    task_summary = pd.DataFrame(task_rows)
    task_summary.to_csv(OUT / 'task_summary.csv', index=False)
    pooled = dict(scope='36任务周期记录直接合并', **stats(hits))
    equal_task = task_summary[['mean_return', 'median_return', 'mean_days', 'median_days']].mean().to_dict()
    write_json(OUT / 'aggregation_sensitivity.json', dict(pooled_task_events=pooled, equal_task_means=equal_task,
        note='equal_task_means median fields are averages of task medians, not pooled medians'))
    fields = TASK + ['era', 'industry_code', 'industry_name', 'block', 'phase_id', 'date', 'start_date',
                     'peak_date', 'end_confirmed_at', 'signal_nav', 'peak_nav', 'return_to_peak',
                     'days_to_peak', 'signal_delay_days', 'score']
    for name, frame in [('task_event_outcomes', hits), ('unique_cycle_outcomes', unique), ('frequency_cycle_outcomes', per_frequency)]:
        frame[fields].to_csv(OUT / (name + '.csv.gz'), index=False, compression={'method': 'gzip', 'mtime': 0})
    write_json(OUT / 'input_receipt.json', dict(inputs={str(p): h for p, h in sources.items()},
        source_counts=counts, task_events=len(hits), exact_boundary_cycles=len(unique),
        code_sha256=sha(__file__), strict_PIT='BLOCKED_DATA', independent_forward_validation='FORWARD_PENDING'))
    report = '''# EP32 V29：成功捕捉行业从首次信号到周期最高点

复用冻结V28方案，不训练模型、不改变0.11门槛或市场过滤。观察日沿用2021-01-01至2024-09-30、每条标签24个月成熟限制；底层冻结数据截至2026-10-21。

## 统计口径

只统计已确认合格的6—18个月价格景气周期，且模型在其前3个月内至少正确报警一次。每个原任务/周期取最早正确报警日，重复报警不增加权重。涨幅为周期最高点行业篮子收盘净值/信号日收盘净值−1；时间为最高点日期−信号日期，单位自然日。这是峰值的事后测量，不是已执行的买卖回报；信号在收盘后生成，同日收盘价只作观察基准。

主表按分类版本、行业层级、行业代码、连续数据块、周期起点和最高点日期完全相同去重，取可用设置中最早的正确报警。分频率表只在该频率内合并双基准与三阈值；总表再合并三个频率。因此总表是历史捕捉范围的并集描述，不是新的可执行多模型组合，也不表示36个任务分别都取得该结果。不同阈值产生起止不同但重叠的行情仍分别保留；二级与三级存在成员重叠，记录数不是独立经济事件数。

''' + table(rows) + f'''
## 与原36任务口径的对照

{counts['positive']:,}条正确报警，按原任务/周期首次命中后为{len(hits):,}条任务周期记录；36项检出周期数逐项与V28相同。主表合并相同起止后为{len(unique)}条周期记录。直接合并原任务周期记录，平均涨幅{pooled['mean_return']:.2%}、中位涨幅{pooled['median_return']:.2%}，平均剩余{pooled['mean_days']:.2f}天、中位{pooled['median_days']:.2f}天。该口径会重复计入不同频率、阈值、基准捕捉的相同周期。

若继续采用原报告36任务等权，任务平均涨幅的平均为{equal_task['mean_return']:.2%}，任务中位涨幅的平均为{equal_task['median_return']:.2%}；任务平均剩余时间的平均为{equal_task['mean_days']:.2f}天，任务中位剩余时间的平均为{equal_task['median_days']:.2f}天。后两个中位汇总项均是“各任务中位数的平均”，不能称为所有周期的总体中位数。

## 适用边界

原{counts['alerts']:,}条报警中，{counts['positive']:,}条为正例、{counts['negative']:,}条为已知负例、{counts['unknown']:,}条未知。本次回答“捕捉到的周期还有多少上涨空间”，只对成功捕捉条件化，未把误报或未知填零。不能以主表涨幅代表所有信号的期望收益，也不能直接乘24.65%的precision推算策略收益：两者分母和权重不同，且失败收益尚未在此计算。

最高点来自未来确认的周期峰值，未建立实时卖出规则，未计交易成本；不是任意无限未来最高价，也不是三只龙头个股收益。价格与成员仍为Historical-proxy，严格PIT BLOCKED_DATA，独立前瞻FORWARD_PENDING。

[精确起止去重周期明细](../outputs/unique_cycle_outcomes.csv.gz) · [分频率明细](../outputs/frequency_cycle_outcomes.csv.gz) · [36任务首次命中明细](../outputs/task_event_outcomes.csv.gz) · [汇总](../outputs/summary.csv) · [核验](../outputs/validation.json)
'''
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/signal_to_peak.md').write_text(report)
    check('V28 artifacts unchanged after analysis', all(sha(p) == h for p, h in frozen.items()))
    check('input bytes unchanged after analysis', all(sha(p) == h for p, h in sources.items()))
    write_json(OUT / 'validation.json', dict(status='PASS', checks=checks, checks_count=len(checks)))
    files = [dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size)
             for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts]
    write_json(OUT / 'manifest.json', dict(files=files, file_count=len(files)))
    print(pd.DataFrame(rows).to_string(index=False))
    print('PASS', len(checks), 'checks; counts', counts)


if __name__ == '__main__':
    main()
