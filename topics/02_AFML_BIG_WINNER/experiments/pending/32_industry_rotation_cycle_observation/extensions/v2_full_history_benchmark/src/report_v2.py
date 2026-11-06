"""Readable benchmark-relative observations and complete retrospective screens."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core import EP, OUT, BENCHMARKS, csv, detail, write_json

NAMES = {'CSI300': '沪深300', 'CSI_ALL': '中证全指', 'ALL_A_EW_PROXY': '全A等权代理'}


def pct(value):
    return '未知' if pd.isna(value) else f'{value * 100:.1f}%'


def pp(value):
    return '未知' if pd.isna(value) else f'{value * 100:+.1f}个百分点'


def md(frame):
    if frame.empty:
        return '没有满足条件且结果已知的观察。\n'
    return ('|' + '|'.join(frame.columns) + '|\n|' + '|'.join(['---'] * len(frame.columns)) + '|\n' +
            '\n'.join('|' + '|'.join(str(x) for x in r) + '|' for r in frame.itertuples(index=False, name=None)) + '\n')


def summary(result, long_result):
    rows = []
    for era_label in ['ALL', 'SW2014', 'SW2021']:
        f = result if era_label == 'ALL' else result[result.era.eq(era_label)]
        lf = long_result if era_label == 'ALL' else long_result[long_result.era.eq(era_label)]
        for (level, benchmark, horizon), g in f.groupby(['level', 'benchmark', 'horizon']):
            groups = [('全部排名完整行业月', g), ('进入领先事件', g[g.entry_event]),
                      ('非领先行业月', g[g.leader.eq(0)]),
                      ('进入且至少10成员', g[g.entry_event & g.members.ge(10)]),
                      ('事后12—18月完整段', lf[lf.level.eq(level) & lf.benchmark.eq(benchmark) & lf.horizon.eq(horizon)])]
            for label, a in groups:
                matured = a[a.mature.eq(True)]
                k = matured[matured.complete.eq(True)]
                kp = k[k.path_complete.eq(True)]
                successes = int(k.all_beat.eq(True).sum())
                rows.append(dict(era=era_label, level=level, benchmark=benchmark, horizon=int(horizon), group=label,
                    origins=len(a), mature=len(matured), known=len(k), unknown=len(matured) - len(k),
                    censored=int(a.mature.eq(False).sum()), unique_origin_months=a.month.nunique(),
                    industry_beat_rate=k.industry_excess.dropna().gt(0).mean(),
                    portfolio_beat_rate=k.portfolio_excess.gt(0).mean(), all_three_beat_rate=k.all_beat.eq(True).mean(),
                    all_positive_rate=k.all_positive.eq(True).mean(),
                    positive_and_all_beat_rate=(k.all_positive.eq(True) & k.all_beat.eq(True)).mean(),
                    median_return=k.mean_return.median(), median_excess=k.portfolio_excess.median(),
                    median_worst_excess=k.worst_excess.median(),
                    all_beat_lower=successes / len(matured) if len(matured) else np.nan,
                    all_beat_upper=(~matured.any_known_fail_beat.eq(True)).mean(),
                    known_paths=len(kp), unknown_paths=len(k) - len(kp),
                    joint_excess_ge9_rate=kp.joint_excess_run.ge(9).mean(),
                    joint_excess_from_first_ge9_rate=kp.joint_excess_from_first.ge(9).mean(),
                    joint_excess_median=kp.joint_excess_run.median()))
    return pd.DataFrame(rows)


def display_summary(s, group, era='ALL', horizon=12):
    a = s[s.group.eq(group) & s.era.eq(era) & s.horizon.eq(horizon)]
    a = a[a.benchmark.isin(['CSI300', 'CSI_ALL'])].sort_values(['level', 'benchmark'])
    return pd.DataFrame({'层级': a.level, '基准': a.benchmark.map(NAMES), '成熟/完整': a.mature.astype(str) + '/' + a.known.astype(str),
        '组合超额中位': a.median_excess.map(pp), '组合跑赢': a.portfolio_beat_rate.map(pct),
        '三只全部跑赢': a.all_three_beat_rate.map(pct), '三只均涨且跑赢': a.positive_and_all_beat_rate.map(pct),
        '共同超额≥9月': a.joint_excess_ge9_rate.map(pct)})


def build(result, state, runs, source):
    reports = EP / 'reports'
    reports.mkdir(parents=True, exist_ok=True)
    # Complete observed start and end required. Future duration is an outcome label.
    lr = runs[~runs.left_censored & ~runs.right_censored & runs.months.between(12, 18)]
    long = lr.rename(columns={'months': 'run_months'}).merge(result,
        left_on=['era', 'level', 'industry_code', 'benchmark', 'start'],
        right_on=['era', 'level', 'industry_code', 'benchmark', 'month'], how='left', suffixes=('_run', ''))
    long['selected_with_future_duration'] = True
    detail('retrospective_long_segments', long)
    s = summary(result, long)
    csv('metrics/summary', s)
    entries = result[result.entry_event].copy()
    csv('metrics/all_entry_events', entries)
    passed = entries[entries.mature & entries.complete & entries.industry_excess.gt(0) & entries.portfolio_excess.gt(0)].copy()
    passed['selected_using_future_returns'] = True
    csv('screens/industry_and_portfolio_beat', passed)
    strict = passed[passed.all_beat.eq(True)].copy()
    csv('screens/industry_and_all_three_beat', strict)
    stocks = []
    for r in strict.itertuples():
        for rank, (instrument, name) in enumerate(zip(r.top3.split(';'), r.display_names_current.split(';')), start=1):
            stocks.append(dict(era=r.era, level=r.level, industry_code=r.industry_code,
                industry_name=r.industry_name, month=r.month, horizon=r.horizon, benchmark=r.benchmark,
                rank=rank, instrument=instrument, display_name_current=name,
                stock_return=getattr(r, f'stock{rank}_return'), benchmark_return=r.benchmark_return,
                stock_excess=getattr(r, f'stock{rank}_excess'), selected_using_future_returns=True))
    csv('screens/stock_level_all_three_beat', pd.DataFrame(stocks))
    persistent = strict[strict.path_complete & strict.joint_excess_run.ge(9)].copy()
    csv('screens/industry_all_three_beat_and_9m', persistent)
    long_passed = long[long.mature.eq(True) & long.complete.eq(True) & long.industry_excess.gt(0) & long.all_beat.eq(True)].copy()
    csv('screens/long_segment_industry_and_all_three_beat', long_passed)
    duration = []
    for (era, level, bm), g in runs.groupby(['era', 'level', 'benchmark']):
        complete = g[~g.left_censored & ~g.right_censored]
        duration.append(dict(era=era, level=level, benchmark=bm, observed=len(g), complete=len(complete),
            left_censored=int(g.left_censored.sum()), right_censored=int(g.right_censored.sum()),
            median_complete_months=complete.months.median(),
            complete_12_18=int(complete.months.between(12, 18).sum()),
            complete_19plus=int(complete.months.gt(18).sum())))
    durations = pd.DataFrame(duration)
    csv('metrics/duration_summary', durations)
    boundary = ('本轮是历史代理观察（Historical-proxy），严格PIT仍为BLOCKED_DATA：股本known_at缺失，行业纳入/剔除及分类字典缺首次版本存证。'
        '前复权价格是价格变化推断，不是实际结算收益；指数也按价格指数比较，不混用含息回报。\n\n')
    timing = (f'行情覆盖从{source["first_session"]}开始，完整月份为{source["first_month"]}—{source["last_complete_month"]}，'
        f'共{source["months"]}个月。2017-01—2021-11用申万2014版二/三级，2022-01以后用2021版；'
        '2021-12为分类过渡缺口，不产生行业信号。两版不拼接状态；每版开始的12个月用于积累，不能伪造此前历史。'
        '固定起点成员的9/12个月标签可跨分类边界，但不随未来分类重选股票。\n\n')
    method = ('超额收益=同一入口、同一终点的累计收益差，以百分点报告。观察月末后市场下一交易日开盘作为假设入口，'
        '9/12个自然月后的月末收盘作为终点；基准使用完全相同日期。'
        '沪深300、中证全指（全A宽基代理）并列为主，全A等权股票总体代理作为诊断；后者不是官方指数。'
        '原始股价×最近有效历史总股本选前三，排名缺失不强行选股。\n\n'
        '过去12月行业收益高于对应基准且横截面进入前25%才称“超额领先”。这是价格状态，不是基本面景气。'
        '超额为正仍可能绝对下跌，绝对正收益另列；组合跑赢也不等于三只全部跑赢。\n\n')
    (reports / '01_full_history_and_benchmarks.md').write_text('# 历史起点、分类版本与基准\n\n' + boundary + timing + method +
        '[逐月成员覆盖](../outputs/audits/membership_by_month.csv)；[基准日期](../outputs/audits/benchmark_dates.csv)；'
        '[采集回执](../outputs/audits/acquisition.json)；[原数据核验](../outputs/audits/inputs.json)。\n')
    (reports / '02_entry_event_excess.md').write_text('# 进入超额领先之后，前三能否跑赢市场\n\n' + boundary + method +
        '12个月结果：\n\n' + md(display_summary(s, '进入领先事件')) + '\n9个月结果：\n\n' +
        md(display_summary(s, '进入领先事件', horizon=9)) +
        '\n“成熟/完整”分母含未知，但各已知比例只用该指标可计算样本；缺失最宽界与路径完整数见汇总。'
        '三股共同超额≥9月的分母只含三个标的各月端点和基准全部已知的路径。另表记录从第一个观察月起连续跑赢的长度，'
        '避免把后半程重新跑赢说成从一开始持续跑赢。\n\n'
        '[全部进入事件](../outputs/metrics/all_entry_events.csv)；[全部分制度/对照汇总](../outputs/metrics/summary.csv)。\n')
    (reports / '03_retrospective_long_segments.md').write_text('# 事后完整持续12—18个月的超额领先段\n\n' + boundary +
        '**按未来才知道的完整时长选组，是现象描述，不能当成事前选行业方法。** 未结束段、左删失段不混入已完成12—18月组。'
        '起点市值前三保持不变，仍以起点后的固定9/12个月终点评价。\n\n' +
        md(display_summary(s, '事后12—18月完整段')) +
        '\n分类制度分别统计长度，不能把2014版和2021版同名行业接成长段。横截面有大量重叠，不把行业数当独立周期数。\n\n'
        '[全部长段含缺失（gzip CSV）](../outputs/details/retrospective_long_segments.csv.gz)；'
        '[长度和删失汇总](../outputs/metrics/duration_summary.csv)；[满足超额条件的长段](../outputs/screens/long_segment_industry_and_all_three_beat.csv)。\n')
    # The displayed list is complete; no selection of the largest winning examples.
    shown = long_passed[long_passed.level.eq('L2') & long_passed.horizon.eq(12) &
                        long_passed.benchmark.isin(['CSI300', 'CSI_ALL'])].sort_values(['era', 'start', 'industry_code', 'benchmark'])
    shown = pd.DataFrame({'制度': shown.era, '行业': shown.industry_name, '起点': shown.start,
        '领先月数': shown.run_months, '基准': shown.benchmark.map(NAMES),
        '前三/当前名称': shown.display_names_current, '组合收益': shown.mean_return.map(pct),
        '基准收益': shown.benchmark_return.map(pct), '组合超额': shown.portfolio_excess.map(pp),
        '最差股超额': shown.worst_excess.map(pp), '共同超额最长/月': shown.joint_excess_run})
    (reports / '04_screened_cases.md').write_text('# 挑出跑赢基准的行业与前三\n\n'
        '**全部名单均使用未来已实现收益筛选，是事后观察名单，不是当时可知的买入名单。**'
        '原始全样本、失败、未知与未到期分母均保留。公司名称是当前展示名称，不能冒充历史已知名称。\n\n'
        '- [行业及前三组合跑赢](../outputs/screens/industry_and_portfolio_beat.csv)\n'
        '- [行业及三只全部跑赢](../outputs/screens/industry_and_all_three_beat.csv)\n'
        '- [上述每只标的的同期涨幅及超额明细](../outputs/screens/stock_level_all_three_beat.csv)\n'
        '- [进一步要求三只共同正超额至少9个月](../outputs/screens/industry_all_three_beat_and_9m.csv)\n'
        '- [完整12—18月长段中，行业和三只全部跑赢](../outputs/screens/long_segment_industry_and_all_three_beat.csv)\n\n'
        '下表完整列出最后一组中二级、12个月、两个真实指数基准的案例，不按收益大小挑选：\n\n' + md(shown))
    overview = ('# EP32 V2：完整历史与市场超额观察\n\n' + timing +
        '**本版回答“是否跑赢同期市场”，不把绝对上涨当作超额收益，也不把价格领先当作景气机制。**\n\n' + boundary +
        '进入超额领先事件，后续12个月：\n\n' + md(display_summary(s, '进入领先事件')) +
        '\n事后完整12—18个月长段，起点后的12个月：\n\n' + md(display_summary(s, '事后12—18月完整段')) +
        '\n旧、新制度分别看：\n\n' + md(display_summary(s, '进入领先事件', era='SW2014')) + '\n' +
        md(display_summary(s, '进入领先事件', era='SW2021')) +
        '\n方法和完整名单：[历史及基准](01_full_history_and_benchmarks.md)、[进入事件](02_entry_event_excess.md)、'
        '[长段观察](03_retrospective_long_segments.md)、[跑赢基准名单](04_screened_cases.md)。\n\n'
        '两版数据分别积累状态，2021-12过渡月空缺；未到期与未知不补零。事后筛选不能证明预测能力，'
        '本轮没有确认性p值或交易授权，原V1及旧实验保留。\n')
    (reports / 'full_history_observation.md').write_text(overview)
    (EP / 'README.md').write_text('# EP32 V2：完整历史与基准收益差\n\n'
        '[本轮方案](research_plan.md)；[完整报告](reports/full_history_observation.md)；'
        '[跑赢基准名单](reports/04_screened_cases.md)。V1保持不变，工作结果可修订。\n\n'
        '从仓库根目录，使用 `topics/02_AFML_BIG_WINNER/.venv/bin/python`，依次执行本目录：'
        '`src/acquire.py`、`src/run.py --build-panel`、`src/validate_v2.py`。'
        '已有完整、哈希匹配面板时，`src/run.py`可复用私有面板；只读前代输入。\n')
    figures = reports / 'figures'
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    for ax, level in zip(axes, ['L2', 'L3']):
        g = result[result.level.eq(level) & result.entry_event & result.horizon.eq(12) & result.mature & result.complete]
        for name in ['CSI300', 'CSI_ALL', 'ALL_A_EW_PROXY']:
            values = np.sort(g[g.benchmark.eq(name)].portfolio_excess.dropna())
            if len(values):
                ax.step(values * 100, np.arange(1, len(values) + 1) / len(values), where='post', label=name)
        ax.axvline(0, color='grey', linewidth=.8)
        ax.set(title=level + ': top-3 entry-event 12m excess', xlabel='Return difference (percentage points)', ylabel='Empirical CDF', xlim=(-100, 150))
        ax.legend(fontsize=8)
    fig.savefig(figures / 'entry_excess_distributions.png', dpi=150)
    plt.close(fig)
    with (reports / 'full_history_observation.md').open('a') as f:
        f.write('\n![完整历史的组合超额分布](figures/entry_excess_distributions.png)\n')
    write_json(OUT / 'audits/findings.json', dict(status='DESCRIPTIVE_ONLY',
        strict_PIT='BLOCKED_DATA', beta_meaning='same_period_return_difference',
        summary=json_safe(s)))


def json_safe(frame):
    import json
    return json.loads(frame.to_json(orient='records'))
