"""Parallel threshold/valuation summaries with full exclusions and stage lists."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from context import EP, OUT, THRESHOLDS, POLICIES, csv, js, detail

NAMES = {'CSI300': '沪深300', 'CSI_ALL': '中证全指'}


def pct(value):
    return '未知' if pd.isna(value) else f'{100*value:.1f}%'


def pp(value):
    return '未知' if pd.isna(value) else f'{100*value:+.1f}'


def md(frame):
    if frame.empty:
        return '没有符合该条件的可计算阶段。\n'
    return '|' + '|'.join(frame.columns) + '|\n|' + '|'.join(['---']*len(frame.columns)) + '|\n' + '\n'.join(
        '|' + '|'.join(str(v) for v in row) + '|' for row in frame.itertuples(index=False, name=None)) + '\n'


def build(phases, scores, stocks, paths, source):
    reports = EP / 'reports'
    reports.mkdir(parents=True, exist_ok=True)
    rows = []
    for (threshold, level), g in phases.groupby(['drawdown_threshold', 'level']):
        complete = g[g.status.eq('CONFIRMED') & ~g.left_censored]
        rows.append(dict(threshold=threshold, level=level, all_stages=len(g),
            left_censored=int(g.left_censored.sum()), right_censored=int(g.right_censored.sum()),
            confirmed_known_start=len(complete), short_lt6=int(complete.duration_months.lt(6).sum()),
            completed_6_18=int(complete.duration_months.between(6,18).sum()),
            long_gt18=int(complete.duration_months.gt(18).sum()),
            median_completed_months=complete.duration_months.median()))
    counts = pd.DataFrame(rows)
    csv('metrics/natural_stage_counts', counts)
    byduration = phases[phases.status.eq('CONFIRMED') & ~phases.left_censored].groupby(
        ['drawdown_threshold', 'level', 'duration_months']).size().rename('stages').reset_index()
    csv('metrics/duration_distribution', byduration)
    result = []
    # Industry candidate counts do not depend on whether a top-three rank can be computed.
    for (threshold, level, benchmark, policy), g in scores.groupby(['threshold', 'level', 'benchmark', 'policy']):
        candidate = g[g.primary_stage]
        known = candidate[candidate.complete]
        path_known = known[known.path_complete]
        successes = int(known.all_positive_and_beat.eq(True).sum())
        result.append(dict(threshold=threshold, level=level, benchmark=benchmark, policy=policy,
            industry_candidate_stages=len(candidate), rank_known=int(candidate.rank_complete.sum()),
            endpoint_known=len(known), unknown=len(candidate)-len(known),
            known_paths=len(path_known), median_duration=candidate.duration_months.median(),
            median_industry_excess=candidate.industry_excess.median(),
            median_portfolio_return=known.portfolio_return.median(), median_portfolio_excess=known.portfolio_excess.median(),
            median_worst_excess=known.worst_stock_excess.median(),
            portfolio_beat_rate=known.portfolio_excess.gt(0).mean(), all_three_beat_rate=known.all_beat.eq(True).mean(),
            all_three_positive_and_beat_rate=known.all_positive_and_beat.eq(True).mean(),
            success_lower=successes/len(candidate) if len(candidate) else np.nan,
            success_upper=(successes+len(candidate)-len(known))/len(candidate) if len(candidate) else np.nan,
            median_joint_excess_months=path_known.joint_excess_longest.median(),
            joint_excess_at_least6_rate=path_known.joint_excess_longest.ge(6).mean(),
            full_path_joint_excess_rate=path_known.all_months_joint_excess.eq(True).mean()))
    summary = pd.DataFrame(result)
    csv('metrics/candidate_summary', summary)
    csv('metrics/summary_by_duration', scores[scores.primary_stage].groupby(
        ['threshold','level','benchmark','policy','duration_months']).agg(stages=('phase_id','size'),
            endpoint_known=('complete','sum'), rank_known=('rank_complete','sum')).reset_index())
    industry_list = scores[scores.policy.eq('EXACT') & scores.primary_stage].copy()
    csv('screens/industry_up_and_beat_6_18', industry_list)
    for threshold in THRESHOLDS:
        tag = str(int(threshold*100))
        g = scores[scores.threshold.eq(threshold) & scores.primary_stage]
        csv('screens/all_candidate_stages_T'+tag, g)
        passing = g[g.complete & g.all_positive_and_beat.eq(True)]
        csv('screens/all_three_positive_and_beat_T'+tag, passing)
        selected_keys = passing[['phase_id', 'policy', 'benchmark']].drop_duplicates()
        selected_stocks = stocks[stocks.threshold.eq(threshold)].merge(selected_keys,
            on=['phase_id', 'policy', 'benchmark'], how='inner', validate='many_to_one')
        detail('screened_stocks_T'+tag, selected_stocks)
    focus_codes = ['801081.SI','801102.SI','851024.SI','850818.SI']
    focus = scores[scores.industry_code.isin(focus_codes) & scores.start_month.ge('2023-01')].copy()
    csv('cases/recent_semiconductor_communications_all_stages', focus)
    # Valuation policies share precisely the same underlying stages and phase endpoints.
    condition = scores[['phase_id','benchmark','policy','rank_complete','complete','primary_stage','selected_stale_marks','any_member_stale_marks']]
    csv('audits/valuation_policy_coverage', condition.groupby(['policy','primary_stage']).agg(
        stage_benchmark_rows=('phase_id','size'), ranks=('rank_complete','sum'), endpoints=('complete','sum'),
        selected_stale_mark_count=('selected_stale_marks','sum'), any_stale_mark_count=('any_member_stale_marks','sum')).reset_index())
    showcounts = pd.DataFrame({'回撤阈值': counts.threshold.map(pct), '层级': counts.level,
        '确认且起点已知': counts.confirmed_known_start, '短于6月': counts.short_lt6,
        '6—18月': counts.completed_6_18, '超过18月不拆': counts.long_gt18,
        '左删失': counts.left_censored, '未结束': counts.right_censored})
    main = summary[summary.policy.eq('EXACT')]
    display = pd.DataFrame({'回撤阈值': main.threshold.map(pct), '层级': main.level,
        '基准': main.benchmark.map(NAMES), '行业候选段': main.industry_candidate_stages,
        '前三终点已知/未知': main.endpoint_known.astype(str)+'/'+main.unknown.astype(str),
        '组合超额中位/百分点': main.median_portfolio_excess.map(pp),
        '三只均涨且跑赢': main.all_three_positive_and_beat_rate.map(pct)})
    value_display = summary[summary.level.eq('L2') & summary.benchmark.eq('CSI300')]
    value_display = pd.DataFrame({'回撤阈值': value_display.threshold.map(pct), '估值层': value_display.policy,
        '候选段': value_display.industry_candidate_stages, '排名完整': value_display.rank_known,
        '终点完整': value_display.endpoint_known, '未知': value_display.unknown,
        '组合超额中位/百分点': value_display.median_portfolio_excess.map(pp),
        '三只均涨且跑赢': value_display.all_three_positive_and_beat_rate.map(pct)})
    boundary = ('输入覆盖2017-01-03—2026-10-21；行业价格按月末观察，最早月末锚点为2017-01。'
        '2026-10-21为部分月尾端，可确认此前峰值回撤，不冒充完整10月。旧、新行业制度分别计算，'
        '2021-12和价格覆盖缺口断开。所有结果仍为Historical-proxy，严格PIT为BLOCKED_DATA。\n\n')
    method = ('用行业价格而非横截面前25%寻找自然段：从低点上涨10%/15%/20%进入上涨状态，'
        '从高点回撤相同幅度后才确认高点为段末。三套阈值并列；阶段起点和终点使用未来才知道的转折，'
        '**不是当时可交易信号**。段长由转折月决定，不再固定9或12个月。超过18个月原段保留，绝不切割。\n\n'
        '“行业自身上涨”部分来自阶段定义，不能把上涨率当新发现。候选还须同期跑赢基准；'
        '行业价格路径按历史当时成员月度等权更新，不是官方行业指数。只有至少5成员、80%端点可比较时才形成收益，'
        '缺口断开，不补零。\n\n')
    valuation = ('行业阶段不依赖前三能否排名。精确起点报价缺失时，另算近7/31自然日最后有效成交估值，'
        '保留报价年龄，属于估值诊断；缺少停牌证明时不能称作起点真实市值。它们**不写入交易开盘或收益**。'
        '三股仍用起点后首个市场交易日开盘到实际段末收盘，基准用同样日期；缺开盘不换复牌日、不换第四名。'
        '排名未知、收益未知不按失败计入比例，分别给出完整分母及最宽缺失界。\n\n')
    (reports/'01_method_and_boundaries.md').write_text('# 全期间与自然阶段方法\n\n'+boundary+method+valuation+
        '段的低点/高点、起点确认/终点确认日期都保留。未结束段用最后观察日作暂时评价，'
        '与已确认完整段分开；左删失说明真实起点可能早于连续数据块。不同阈值阶段重叠，不能合并成独立样本。\n\n'
        '[方案](../research_plan.md)；[输入核验](../outputs/audits/inputs.json)；[全部自然段](../outputs/details/all_natural_stages.csv.gz)。\n')
    (reports/'02_stage_duration_inventory.md').write_text('# 自然阶段长度与删失\n\n'+boundary+method+md(showcounts)+
        '\n主时长统计不含左删失或未结束段。6、7、…、18个月分别列出，短段和超过18个月段全部保留。'
        '部分月尾端只会出现在未结束阶段的暂时评价或确认时点，不形成已确认的部分月峰值。\n\n'
        '[逐月长度分布](../outputs/metrics/duration_distribution.csv)；[全部6—18月完整段](../outputs/stages/completed_6_18.csv)；'
        '[超过18个月且未拆分](../outputs/stages/over_18_not_split.csv)；[全部未结束段](../outputs/stages/open_stages.csv)。\n')
    (reports/'03_top3_and_missing_valuations.md').write_text('# 阶段内市值前三与缺失边界\n\n'+boundary+valuation+
        '精确起点报价层，按自然阶段实际长度评价：\n\n'+md(display)+
        '\n二级行业、沪深300的三种估值层对比：\n\n'+md(value_display)+
        '\n后三股“组合跑赢”“三只全跑赢”“三只全涨且跑赢”分别记录。路径连续性使用完整路径分母，'
        '最长共同正超额与从第一月起共同正超额不混淆。估值补充使样本覆盖不同，不可挑最好一层作确认结论。\n\n'
        '[全部汇总与缺失界](../outputs/metrics/candidate_summary.csv)；[估值覆盖](../outputs/audits/valuation_policy_coverage.csv)。\n')
    focus_view = focus[focus.policy.eq('EXACT') & focus.benchmark.eq('CSI300')]
    fv = pd.DataFrame({'回撤':focus_view.threshold.map(pct),'行业':focus_view.industry_name,
        '起点':focus_view.start_month,'端点':focus_view.end_month,'月数':focus_view.duration_months,
        '状态':focus_view.phase_status,'长度分类':focus_view.length_class,'左删失':focus_view.left_censored,
        '行业超额/百分点':focus_view.industry_excess.map(pp),'排名完整':focus_view.rank_complete,
        '前三组合超额/百分点':focus_view.portfolio_excess.map(pp)})
    (reports/'04_recent_case_audit.md').write_text('# 近期半导体、通信相关行业：全部自然段\n\n'+boundary+
        '下表列出2023年后起点的相关行业段，含短段、超过18月、未结束、排名未知及失败，'
        '不将已知行情强行切成6—18个月。光通信没有在此新建PIT主题池，通信网络设备及器件仍是较宽代理分类。\n\n'+md(fv)+
        '\n[两基准及三估值层完整明细](../outputs/cases/recent_semiconductor_communications_all_stages.csv)。\n')
    overview = ('# EP32 V4：全历史、6—18个月自然上涨阶段\n\n'
        '已按用户新要求重做：行业自身上涨且跑赢基准，起止由自然转折确定；超过18个月不拆分。'
        '未沿用固定9/12月持有期、前25%新进入条件或整行业市值齐全才能观察的门槛。\n\n'+boundary+method+
        '全部自然段的长度与删失：\n\n'+md(showcounts)+
        '\n精确报价层：已确认、起点已知、6—18个月且行业上涨并跑赢基准的阶段：\n\n'+md(display)+
        '\n这些是事后条件观察，不是行业轮动预测或景气机制的确认。不同回撤阈值结果须并列看，'
        '不能从行业上涨段已被选中，再推导可提前选中上涨行业。\n\n'
        '阅读：[方法与时点](01_method_and_boundaries.md)、[全部阶段长度](02_stage_duration_inventory.md)、'
        '[前三与估值缺失](03_top3_and_missing_valuations.md)、[近期全部案例](04_recent_case_audit.md)、'
        '[逐层汇总](../outputs/metrics/candidate_summary.csv)。\n\n'
        '完整名单：[行业上涨且跑赢的6—18月阶段](../outputs/screens/industry_up_and_beat_6_18.csv)；'
        '三只均涨且跑赢：[10%口径](../outputs/screens/all_three_positive_and_beat_T10.csv)、'
        '[15%口径](../outputs/screens/all_three_positive_and_beat_T15.csv)、'
        '[20%口径](../outputs/screens/all_three_positive_and_beat_T20.csv)。\n')
    (reports/'adaptive_stage_observation.md').write_text(overview)
    (EP/'README.md').write_text('# EP32 V4：全期间自适应6—18月阶段\n\n'
        '[完整报告](reports/adaptive_stage_observation.md)；[本轮方案](research_plan.md)。'
        '原V1—V3保持原字节。结果为可修订工作观察，不是独立确认。\n\n'
        '使用项目虚拟环境，依次运行本目录 `src/run.py --prepare`、`src/validate.py`。'
        '输入哈希匹配时可省略`--prepare`复用本轮私有面板。私有数据在`~/.cache/a_share/ep32/adaptive_v4/`。\n')
    fig, axes = plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for ax, level in zip(axes,['L2','L3']):
        for t in THRESHOLDS:
            g=phases[phases.level.eq(level)&phases.drawdown_threshold.eq(t)&phases.status.eq('CONFIRMED')&~phases.left_censored]
            ax.hist(g.duration_months,bins=np.arange(.5,60.5),histtype='step',label=f'{t:.0%} drawdown')
        ax.axvspan(5.5,18.5,color='green',alpha=.12)
        ax.set(title=level+': natural completed upswing durations',xlabel='Months',ylabel='Count',yscale='log')
        ax.legend(fontsize=8)
    figures=reports/'figures';figures.mkdir(exist_ok=True)
    fig.savefig(figures/'natural_stage_durations.png',dpi=150);plt.close(fig)
    with (reports/'adaptive_stage_observation.md').open('a') as f:
        f.write('\n![自然上涨段长度分布](figures/natural_stage_durations.png)\n')
    js('audits/findings',dict(status='DESCRIPTIVE_EX_POST',strict_PIT='BLOCKED_DATA',
        bounds=[6,18],long_stages_split=False,summary=json.loads(summary.to_json(orient='records'))))
