"""Descriptive reports; neither a confirmation test nor a business-cycle label."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from observe import EP, OUT, csv, write_json


def pct(x):
    return '未知' if pd.isna(x) else f'{100 * x:.1f}%'


def number(x):
    return '未知' if pd.isna(x) else f'{x:.1f}'


def table(frame):
    if frame.empty:
        return '无可用观察。\n'
    cols = list(frame.columns)
    rows = ['|' + '|'.join(cols) + '|', '|' + '|'.join(['---'] * len(cols)) + '|']
    rows.extend('|' + '|'.join(str(x) for x in row) + '|' for row in frame.itertuples(index=False, name=None))
    return '\n'.join(rows) + '\n'


def summarize(result):
    rows = []
    for (level, horizon), all_group in result.groupby(['level', 'horizon']):
        for group, mask in [('全部完整排名行业月', np.ones(len(all_group), dtype=bool)),
                            ('非领先行业月', all_group.leader.eq(0)),
                            ('进入领先事件', all_group.entry_event),
                            ('进入领先且至少10成员', all_group.entry_event & all_group.members.ge(10))]:
            g = all_group[mask & all_group.members.ge(5)]
            mature = g[g.mature]
            known = mature[mature.complete]
            possible = ~mature.any_known_nonpositive
            successes = known.all_positive.eq(True).sum()
            paired = known.mean_return - known.market_return
            rows.append(dict(level=level, horizon=int(horizon), group=group,
                             origins=len(g), unique_origin_months=g.month.nunique(),
                             mature=len(mature), known=len(known), unknown=len(mature) - len(known),
                             censored=int((~g.mature).sum()),
                             median_return=float(known.mean_return.median()) if len(known) else None,
                             q25_return=float(known.mean_return.quantile(.25)) if len(known) else None,
                             q75_return=float(known.mean_return.quantile(.75)) if len(known) else None,
                             median_worst=float(known.worst_return.median()) if len(known) else None,
                             all_positive_rate=float(known.all_positive.eq(True).mean()) if len(known) else None,
                             all_positive_lower=successes / len(mature) if len(mature) else None,
                             all_positive_upper=float(possible.mean()) if len(mature) else None,
                             median_excess_market=float(paired.median()) if paired.notna().any() else None,
                             median_excess_other=float((known.mean_return - known.other_return).median()) if len(known) else None,
                             median_positive_run=float(known.positive_run.median()) if len(known) else None,
                             median_joint_positive_run=float(known.joint_positive_run.median()) if len(known) else None,
                             median_monthly_up_run=float(known.monthly_up_run.median()) if len(known) else None,
                             median_month_end_drawdown=float(known.max_drawdown.median()) if len(known) else None,
                             known_joint_paths=int(known.joint_positive_run.notna().sum()),
                             unknown_joint_paths=int(known.joint_positive_run.isna().sum()),
                             joint_ge9_fraction=float(known.joint_positive_run.dropna().ge(9).mean())
                             if known.joint_positive_run.notna().any() else None))
    return pd.DataFrame(rows)


def build_report(origin, series, runs, result, source):
    reports = EP / 'reports'
    reports.mkdir(exist_ok=True)
    summary = summarize(result)
    csv('metrics/outcome_summary', summary)
    duration = []
    for (level, window), g in runs.groupby(['level', 'window']):
        full = g[~g.left_censored & ~g.right_censored]
        known_start = g[~g.left_censored]
        duration.append(dict(level=level, window=int(window), observed_runs=len(g),
                             completed=len(full), left_censored=int(g.left_censored.sum()),
                             right_censored=int(g.right_censored.sum()),
                             median_completed_months=float(full.months.median()) if len(full) else None,
                             complete_1_6=int(full.months.le(6).sum()),
                             complete_7_11=int(full.months.between(7, 11).sum()),
                             complete_12_18=int(full.months.between(12, 18).sum()),
                             complete_19plus=int(full.months.ge(19).sum()),
                             observed_ge12_from_known_start=int(known_start.months.ge(12).sum())))
    durations = pd.DataFrame(duration)
    csv('metrics/duration_summary', durations)
    entries = runs[(runs.window == 12) & ~runs.left_censored].copy()
    intervals = []
    for (level, code), g in entries.groupby(['level', 'industry_code']):
        dates = pd.PeriodIndex(g.start, freq='M').sort_values()
        for a, b in zip(dates[:-1], dates[1:]):
            intervals.append(dict(level=level, industry_code=code, first=str(a), next=str(b), months=b.ordinal - a.ordinal))
    csv('metrics/reentry_intervals', pd.DataFrame(intervals))
    coverage = origin.groupby('level').agg(industry_months=('month', 'size'),
        observed_industries=('industry_code', 'nunique'), complete_rank_months=('rank_complete', 'sum'),
        entry_events=('entry_event', 'sum')).reset_index()
    coverage['entry_events_rank_complete'] = coverage.level.map(
        origin[origin.entry_event & origin.rank_complete & origin.members.ge(5)].groupby('level').size()).fillna(0).astype(int)
    csv('audits/observation_coverage', coverage)
    # Same-month nonleader comparator: calendar matching reduces bull-market confounding.
    controls = result[result.mature & result.complete & result.members.ge(5) & result.leader.eq(0)]
    control_mean = controls.groupby(['level', 'horizon', 'month']).mean_return.mean()
    events = result[result.entry_event & result.members.ge(5)].copy()
    events['nonleader_same_month_return'] = [control_mean.get((r.level, r.horizon, r.month), np.nan)
                                            for r in events.itertuples()]
    events['excess_nonleader_same_month'] = events.mean_return - events.nonleader_same_month_return
    csv('metrics/entry_events', events)
    main = summary[summary.group.eq('进入领先事件')]
    display = pd.DataFrame({
        '层级': main.level, '期限/月': main.horizon, '成熟事件': main.mature,
        '已知/未知': main.known.astype(str) + '/' + main.unknown.astype(str),
        '三股均涨': main.all_positive_rate.map(pct), '组合中位涨幅': main.median_return.map(pct),
        '最差股中位涨幅': main.median_worst.map(pct), '中位超额/市场': main.median_excess_market.map(pct),
        '三股共同盈利最长段中位/月': main.median_joint_positive_run.map(number)})
    duration_display = pd.DataFrame({
        '层级': durations.level, '过去窗口/月': durations.window, '完整段': durations.completed,
        '左/右删失': durations.left_censored.astype(str) + '/' + durations.right_censored.astype(str),
        '完整段中位/月': durations.median_completed_months.map(number),
        '完整段12—18月': durations.complete_12_18})
    boundary = (
        '数据质量为 **Historical-proxy**；严格 PIT 为 **BLOCKED_DATA**。行业纳入/剔除日期是回溯供应商记录，'
        '没有首次发布/修订存证；总股本 known_at 缺失。当前下载的2021分类字典也没有逐次历史版本。'
        '股价采用封存前复权价格变化推断，不是实际可执行或现金权益结算收益。'
        '元数据包含历史退出身份，但全市场每日资格仍未认证。\n\n')
    (reports / '01_rotation_duration.md').write_text(
        '# 价格领先与轮动持续时间\n\n' + boundary +
        '按二级、三级分别计算。上一月成员等权收益，至少5成员、80%端点；过去1/6/12月相对市场强度前25%为价格领先。'
        '这里只识别价格相对强弱。12月窗口重叠可机械提高持续性，不能把领先段直接命名为景气周期。\n\n' +
        table(duration_display) + '\n完整段中位数只对两端均观察到的段计算；删失段另列，不能当失败或已结束。'
        '“领先12—18月”和“每12—18月切换”是不同命题，重复进入的间隔见另表，不能互相替代。'
        '本轮从2022年开始，市场时间段很少，行业横截面数量不增加独立宏观周期数。\n\n'
        '[全部持续段](../outputs/metrics/leading_runs.csv)；[再次进入间隔](../outputs/metrics/reentry_intervals.csv)；'
        '[月度行业序列](../outputs/metrics/industry_price_series.csv)。\n')
    (reports / '02_top3_returns.md').write_text(
        '# 进入价格领先后，当时市值前三是否共同上涨\n\n' + boundary +
        '总市值=当月未复权收盘×最近有效总股本。全部可识别行业成员都有有效市值且无未解析成员，才称排名完整；'
        '否则该行业月不进入前三评分。前三按原始身份固定，不按未来重选；名称只是当前展示标签。'
        '下一市场交易日开盘为假设入口，缺开盘不延迟到复牌日。\n\n' + table(display) +
        '\n“三股均涨”只用三股终点均已知的成熟事件；未知不填零，缺失最宽上下界见汇总表。'
        '组合上涨、最差股上涨和三股全部上涨独立列出，不能用平均收益代替“都会涨”。'
        '市场比较为同一时点固定总体的等权价格收益，非某只宽基指数；行业其他成员比较覆盖数另列。'
        '这不是可执行收益。\n\n[含全部对照的汇总](../outputs/metrics/outcome_summary.csv)；'
        '[全部进入事件](../outputs/metrics/entry_events.csv)；[全部完整排名行业月（gzip CSV）](../outputs/metrics/top3_outcomes.csv.gz)。\n')
    sustain = pd.DataFrame({'层级': main.level, '期限/月': main.horizon,
        '三股共同盈利段中位/月': main.median_joint_positive_run.map(number),
        '完整路径/条': main.known_joint_paths,
        '组合连续单月上涨段中位/月': main.median_monthly_up_run.map(number),
        '三股共同盈利段≥9月': main.joint_ge9_fraction.map(pct),
        '组合月末回撤中位': main.median_month_end_drawdown.map(pct)})
    (reports / '03_return_persistence.md').write_text(
        '# 9—12个月持续性\n\n' + boundary + table(sustain) +
        '\n“共同盈利段”指三个固定标的在每个月末相对各自假设入口都为正的连续月份；不要求每月继续涨。'
        '“连续单月上涨段”指组合相邻月末连续上涨，含假设入口到第一个月末。'
        '终点正收益不能替代整个路径；任一中途端点未知，该路径持续长度记未知，比例分母只含完整路径。'
        '月末回撤会漏掉月内跌幅，不能解释成完整风险上限。\n\n'
        '[全部逐股路径](../outputs/metrics/entry_stock_paths.csv)；[持续性明细](../outputs/metrics/entry_events.csv)。\n')
    (reports / '04_business_cycle_gap.md').write_text(
        '# 价格轮动是否代表景气切换\n\n' + boundary +
        '**尚未检验基本面景气机制。** 本轮没有把收入、利润、订单、库存或价格数据的当时已披露变化用作行业周期定义。'
        '股票上涨也可能来自市场整体、估值、风格、政策或情绪；价格领先不能单独识别原因。\n\n'
        '下一阶段需要：细分行业历史成员及分类修订链，原始财报的首次披露与更正版本、时点股本，'
        '再以事前定义的景气指标定位切换。须分别估计行业景气改善、价格反应的先后和滞后，'
        '不能按事后股价峰谷倒推景气起点。确定规则后保留新时间段做独立验证。\n')
    findings = []
    for row in main.itertuples():
        d = durations[(durations.level == row.level) & (durations.window == 12)].iloc[0]
        findings.append(f'- {row.level}：12月强度领先的完整持续段 {d.completed} 段，中位 {number(d.median_completed_months)} 个月；'
                        f'其中12—18月 {d.complete_12_18} 段。进入后{row.horizon}个月有 {row.mature} 个成熟事件，'
                        f'{row.known} 个三股终点完整；三股均涨 {pct(row.all_positive_rate)}，'
                        f'组合中位收益 {pct(row.median_return)}，最差股中位收益 {pct(row.median_worst)}。')
    overview = ('# EP32 第一阶段观察\n\n'
        '研究已启动，采用**申万二级和三级**，按当时总市值前三固定标的，先观察价格现象。'
        '**当前不能据此声称已由严格PIT证实12—18月景气轮动及前三持续9—12月普涨。**\n\n' + boundary +
        f'观察月份：2022-01—{source["complete_month_cutoff"]}，共{source["months"]}个月。'
        '2021体系不回填到更早历史；前12个月只积累状态，随后才产生完整领先判断。'
        '本轮完整使用在列和已剔除成员，不用当前成员反填历史。\n\n' +
        '\n'.join(findings) + '\n\n' + table(display) + '\n' + table(duration_display) +
        '\n以上为探索性样本描述。没有设“不错”的成功阈值，也没有进行预测模型拟合或独立确认。'
        '按行业月观察有高度重叠，不把事件数当独立宏观周期数；同月非领先对照和行业其他成员对照均保留。\n\n'
        '阅读：[轮动长度](01_rotation_duration.md)、[前三涨幅](02_top3_returns.md)、'
        '[持续性](03_return_persistence.md)、[景气缺口](04_business_cycle_gap.md)。\n\n'
        '证据：[来源核验](../outputs/audits/input_verification.json)、'
        '[行业采集](../outputs/audits/industry_acquisition.json)、'
        '[月度成员覆盖](../outputs/audits/monthly_membership.csv)、'
        '[观察覆盖](../outputs/audits/observation_coverage.csv)、[全部汇总](../outputs/metrics/outcome_summary.csv)。\n')
    (reports / 'first_observation.md').write_text(overview)
    (EP / 'README.md').write_text(
        '# EP32：细分行业长周期轮动观察\n\n'
        '[用户问题](GOAL.md)；[观察方案](research_plan.md)；[第一阶段报告](reports/first_observation.md)。\n\n'
        '当前为可修订工作结果，不封存。严格PIT受阻，结果只为Historical-proxy。'
        '私有大表留在 `~/.cache/a_share/ep32/`，旧实验只读。\n\n'
        '从仓库根目录执行：\n\n```bash\n'
        'PY=topics/02_AFML_BIG_WINNER/.venv/bin/python\n'
        'EP=topics/02_AFML_BIG_WINNER/experiments/pending/32_industry_rotation_cycle_observation\n'
        '"$PY" "$EP/src/acquire_industry.py"\n'
        'OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/observe.py"\n'
        '"$PY" "$EP/src/long_segments.py"\n'
        'OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/validate.py"\n'
        '"$PY" -m pytest -q "$EP/tests"\n```\n')
    # Plain JSON with missing values retained as null.
    safe = json.loads(summary.to_json(orient='records'))
    write_json(OUT / 'audits/findings.json', dict(status='DESCRIPTIVE_ONLY', strict_PIT='BLOCKED_DATA',
               business_cycle='NOT_TESTED', independent_prediction='NOT_TESTED', results=safe))
