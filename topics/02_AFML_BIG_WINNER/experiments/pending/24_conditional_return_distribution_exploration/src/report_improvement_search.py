"""Combine R16 results without declaring a failed research target complete."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from diagnose_prediction_target import DEST
from prepare_panel import EP, OUT
from run_four_horizons import BINS, BIN_NAMES

ROUNDS = ['round1', 'market_residual', 'prequential', 'rank_residual']
METRICS = ['brier', 'multiclass_brier', 'crps', 'accuracy']
LABELS = {
    'richer_peers': '更丰富的近邻', 'vol_normalized_global': '波动标准化历史分布',
    'vol_normalized_peers': '波动标准化近邻', 'shallow_classes': '浅层多分类',
    'shallow_classes_shrunk': '收缩的浅层多分类',
    'market_empirical_residual': '市场历史分布＋个股残差',
    'market_state_residual': '市场状态近邻＋个股残差',
    'market_momentum_residual': '市场动量＋个股残差',
    'market_empirical_pit': '市场残差模型再校准', 'uniform_mixture': '九模型等权组合',
    'prequential_mixture': '已到期成绩动态组合', 'prequential_gate': '已到期成绩择模',
    'rank_value_residual': '估值质量排序残差', 'rank_technical_residual': '行情排序残差',
    'rank_combined_residual': '综合排序残差',
}


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delta_interval(new, base, direction=False):
    difference = new - base if direction else base - new
    n = len(difference)
    rng = np.random.default_rng(24)
    starts = rng.integers(0, n, size=(2000, int(np.ceil(n / 12))))
    ix = ((starts[:, :, None] + np.arange(12)) % n).reshape(2000, -1)[:, :n]
    return np.quantile(difference[ix].mean(axis=1), [.025, .975])


def run():
    contract = json.loads((DEST / 'target_contract.json').read_text())
    scoreboards, summaries, phases, diagnostics, intervals, receipts = [], [], [], [], [], []
    baseline = {}
    for item in contract['files']:
        path = Path(item['path'])
        assert hash_file(path) == item['sha256']
        base = pd.read_parquet(path)
        baseline[item['months']] = base[base.model == 'B'].copy()
    for name in ROUNDS:
        folder = DEST / name
        board = pd.read_csv(folder / 'target_scoreboard.csv'); board['round'] = name
        scoreboards.append(board)
        summaries.append(pd.read_csv(folder / 'summary.csv'))
        phases.append(pd.read_csv(folder / 'phase_scores.csv'))
        audit = pd.read_csv(folder / 'fit_audit.csv')
        assert len(audit) == 192 and set(audit.months) == {1, 3, 6}
        columns = {'round1': ['last_training_label'],
                   'market_residual': ['last_stock_label', 'last_market_label'],
                   'prequential': ['latest_history_label'],
                   'rank_residual': ['last_stock_label', 'last_market_label']}[name]
        for column in columns:
            labels = pd.to_datetime(audit[column])
            if name != 'prequential':
                assert labels.notna().all()
            else:
                assert labels.isna().eq(audit.history_months == 0).all()
            assert ((labels < pd.to_datetime(audit.date)) | labels.isna()).all()
        if name == 'prequential':
            assert (audit.history_months <= 36).all()
            assert audit.loc[audit.history_months < 12, 'gate_model'].eq('B').all()
            weights = pd.read_csv(folder / 'mixture_weights.csv')
            np.testing.assert_allclose(weights.groupby(['months', 'date']).weight.sum(), 1)
        monthly = pd.read_csv(folder / 'monthly_scores.csv')
        for (h, model), m in monthly[monthly.model != 'frozen_B'].groupby(['months', 'model']):
            b = monthly[(monthly.months == h) & (monthly.model == 'frozen_B')]
            paired = m.merge(b, on='date', suffixes=('_new', '_base'), validate='one_to_one')
            for metric in METRICS:
                lo, hi = delta_interval(paired[f'{metric}_new'].to_numpy(), paired[f'{metric}_base'].to_numpy(), metric == 'accuracy')
                intervals.append(dict(months=h, model=model, metric=metric, improvement_lower95=lo, improvement_upper95=hi))
        for h in [1, 3, 6]:
            path = folder / f'predictions_{h}m.parquet'
            d = pd.read_parquet(path)
            receipts.append(dict(path=str(path.relative_to(EP)), sha256=hash_file(path), rows=len(d)))
            for model, g in d.groupby('model'):
                matched = g.merge(baseline[h][['date', 'instrument', 'actual']], on=['date', 'instrument'],
                                  suffixes=('', '_base'), validate='one_to_one')
                assert len(matched) == len(baseline[h]) == 27600
                np.testing.assert_allclose(matched.actual, matched.actual_base, equal_nan=True)
            pcols = ['p_up', 'p_down', 'p_zero']
            bincols = [f'p_{x}' for x in BIN_NAMES]
            assert np.isfinite(d[pcols + bincols]).all().all()
            assert (d[pcols + bincols] >= -1e-12).all().all()
            np.testing.assert_allclose(d[pcols].sum(axis=1), 1, atol=1e-10)
            np.testing.assert_allclose(d[bincols].sum(axis=1), 1, atol=1e-10)
            assert (d.q05 <= d.q50).all() and (d.q50 <= d.q95).all()
            observed = d.actual.notna()
            assert d.loc[~observed, METRICS[:-1]].isna().all().all()
            expected_brier = (d.loc[observed, 'p_up'] - (d.loc[observed, 'actual'] > 0)) ** 2
            np.testing.assert_allclose(d.loc[observed, 'brier'], expected_brier)
            actual_bin = np.searchsorted(BINS, d.loc[observed, 'actual'], side='right')
            expected_multi = ((d.loc[observed, bincols].to_numpy() - np.eye(5)[actual_bin]) ** 2).sum(axis=1)
            np.testing.assert_allclose(d.loc[observed, 'multiclass_brier'], expected_multi)
            for (date, model), g in d[observed & (d.actual != 0)].groupby(['date', 'model']):
                y = (g.actual > 0).to_numpy()
                diagnostics.append(dict(months=h, date=date, model=model, up_call_fraction=float((g.p_up > g.p_down).mean()),
                    realized_up_fraction=y.mean(), constant_up_accuracy=y.mean(), constant_down_accuracy=1-y.mean(),
                    within_month_auc=roc_auc_score(y, g.p_up) if len(np.unique(y)) == 2 else np.nan))
    scores = pd.concat(scoreboards, ignore_index=True)
    summary = pd.concat(summaries, ignore_index=True).drop_duplicates(['months', 'model'])
    phase = pd.concat(phases, ignore_index=True).drop_duplicates(['months', 'phase', 'model'])
    diag = pd.DataFrame(diagnostics)
    diag.groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST / 'direction_diagnostics.csv')
    scores.to_csv(DEST / 'all_target_scores.csv', index=False)
    summary.to_csv(DEST / 'all_summary.csv', index=False)
    phase.to_csv(DEST / 'all_phase_scores.csv', index=False)
    pd.DataFrame(intervals).to_csv(DEST / 'paired_improvement_intervals.csv', index=False)
    decisions = []
    for model, g in scores.groupby('model'):
        assert len(g) == 12 and set(g.months) == {1, 3, 6}
        decisions.append(dict(model=model, all_point_targets_met=bool(g.point_target_met.all()),
                              all_confidence_targets_met=bool(g.confidence_target_met.all())))
    result = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active',
                  candidate_count=len(decisions), gates_per_candidate=12, candidates=decisions,
                  passed_point_gates=int(scores.point_target_met.sum()), total_point_gates=len(scores),
                  validation='Repeated retrospective exploration; no new independent holdout; no multiplicity correction',
                  source_files=receipts, baseline_contract_sha256=hash_file(DEST / 'target_contract.json'))
    # Passing point scores would still require an explicit independent-evidence review.
    (DEST / 'research_integrity_audit.json').write_text(json.dumps(result, indent=2) + '\n')

    lines = ['# R16：概率误差与方向命中率双目标探索', '',
             f'已完成{len(decisions)}个候选方法的1、3、6个月历史滚动比较；**没有方法同时满足双目标，20%目标仍为活动状态。** 技术核验通过只表示样本、时点与概率计算符合约定，不代表模型有效。', '',
             '## 固定验收线', '',
             '基线固定为R15的B风险/市值模型；每期限同一批27,600个股票—预测日期，2021年1月至2026年4月、64个预测月。行情标签截止2026-05-29。已到期有效样本分别27,138/26,703/25,413条，对应63/62/59个预测月。评分先在每月内平均，再对月份等权。', '',
             '“提高20%”为相对改善：命中率乘1.2，概率误差乘0.8。上涨Brier、五档Brier、CRPS均需过线；方向按P(上涨)>P(下跌)判上涨，否则判下跌，实际恰好不变从所有模型的方向评分中一致排除。没有换基线、挑股票或挑月份。12个月保留此前研究结果，本轮沿用已确认的1/3/6个月滚动比较范围，尚未执行12个月20%目标检验。', '',
             '| 期限 | 上涨Brier：基线→目标 | 五档Brier：基线→目标 | CRPS：基线→目标 | 方向命中率：基线→目标 |',
             '|---|---|---|---|---|']
    targets = pd.read_csv(DEST / 'frozen_targets.csv')
    for h in [1, 3, 6]:
        t = targets[targets.months == h].set_index('metric')
        fields = [f'{t.loc[m,"baseline"]:.4f}→{t.loc[m,"target"]:.4f}' for m in METRICS[:-1]]
        fields.append(f'{t.loc["accuracy","baseline"]:.2%}→{t.loc["accuracy","target"]:.2%}')
        lines.append(f'| {h}个月 | ' + ' | '.join(fields) + ' |')
    lines += ['', '## 所有方法的结果', '',
              '表中每格为“**三项概率误差改善中最小值 / 命中率相对改善**”；正数较好，负数变差。一格只有两者均≥20%才达到该期限目标，三个期限均满足才通过点估计门槛。没有把不同方法各自最好的指标拼成一个模型。', '',
              '| 方法 | 1个月 | 3个月 | 6个月 |', '|---|---|---|---|']
    for model in LABELS:
        fields = []
        for h in [1, 3, 6]:
            g = scores[(scores.months == h) & (scores.model == model)].set_index('metric')
            fields.append(f'{g.loc[METRICS[:-1],"relative_improvement"].min()*100:+.2f}% / {g.loc["accuracy","relative_improvement"]*100:+.2f}%')
        lines.append(f'| {LABELS[model]} | ' + ' | '.join(fields) + ' |')
    lines += ['', '## 改善的含义与稳定性', '',
              '以“市场历史分布＋个股残差”为例，分解方法有一些历史平均改善；以下完整展示同一个模型，不能只看它最好的方向指标。', '',
              '| 期限 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率 | 始终预测下跌的命中率（诊断对照） |', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        model = 'market_empirical_residual'
        g = scores[(scores.months == h) & (scores.model == model)].set_index('metric')
        fields = [f'{g.loc[m,"relative_improvement"]:.2%}' for m in METRICS[:-1]]
        constant = diag[(diag.months == h) & (diag.model == model)].constant_down_accuracy.mean()
        fields += [f'{g.loc["accuracy","value"]:.2%}', f'{constant:.2%}']
        lines.append(f'| {h}个月 | ' + ' | '.join(fields) + ' |')
    late = phase[(phase.months == 6) & (phase.phase == '2024_plus')].set_index('model')
    six_diagnostic = diag[(diag.months == 6) & (diag.model == 'market_empirical_residual')]
    lines += ['',
              f'6个月该模型在2024年以后命中率为{late.loc["market_empirical_residual","accuracy"]:.2%}，基线为{late.loc["frozen_B","accuracy"]:.2%}；五档Brier由基线{late.loc["frozen_B","multiclass_brier"]:.4f}变为{late.loc["market_empirical_residual","multiclass_brier"]:.4f}，CRPS也变差。因此全时段平均改善不等于稳定优势。始终预测下跌仅为固定方向诊断，不能替代概率分布模型；其命中率说明类别比例本身可贡献不少方向成绩。', '',
              f'同一个6个月模型平均有{1-six_diagnostic.up_call_fraction.mean():.2%}的有效样本判为下跌，同月区分上涨/下跌股票的AUC平均为{six_diagnostic.within_month_auc.mean():.4f}（0.5为随机排序参照）。结合固定判跌对照，这提示命中率改善很大程度与预测方向偏向有关，尚未体现稳定的个股区分能力。', '',
              '按12个月时间块、2,000次配对重采样记录改善区间和20%目标的余量区间；月份之间存在重叠标签，不能把数万股票月当作数万个独立观测。所有方法都属于反复查看同一历史段后的探索，没有重新包装为独立留出验证；区间未做多重试验修正。', '',
              '## 如何避免未来信息', '',
              '- 所有训练标签终点严格早于预测日期；市场和个股标签分别核验。新增行情特征只使用当日及此前价格，预测输入白名单不含未来市场标签。',
              '- 动态组合、择模和PIT校准只使用已经到期的旧预测，最多36个预测月，至少12个月才启用。混合完整分布，再由同一个分布计算上涨、下跌和五档概率。',
              '- 排序残差模型只对同日已知特征排序；训练标签在各训练月份内去除共同冲击，再用固定正则化学习股票相对差异。残差噪声使用训练内近似，未称作交叉验证噪声。',
              '- 事后“已知实际月度上涨比例”的结果仅作为误差诊断，未加入任何模型或验收表。', '',
              '## 剩余约束与下一步', '',
              '本轮仍未解决公开历史数据修订、上海股票池历史ST筛选偏差、完整公司行动与严格财报初始版本。前瞻收益率仍是历史盈利增长＋估值回归的情景代理；它不是当时分析师一致预期。', '',
              '当前证据只支持小幅、依赖时期的改善，不能承诺能实现20%。下一轮优先增加有时点证据的市场/行业共同信息及更新鲜的盈利预期，而不是继续扩大同一组参数搜索；这些数据尚未接入，也尚未证明能达到目标。新增到期样本若已被看过，只能算补充回溯检验。', '',
              '明细：[全部指标与20%余量](outputs/r16_improvement_search/all_target_scores.csv)、[早晚阶段](outputs/r16_improvement_search/all_phase_scores.csv)、[方向诊断](outputs/r16_improvement_search/direction_diagnostics.csv)、[配对改善区间](outputs/r16_improvement_search/paired_improvement_intervals.csv)、[技术核验](outputs/r16_improvement_search/research_integrity_audit.json)。', '']
    (EP / 'improvement_search_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_files', 'candidates']}, indent=2))


if __name__ == '__main__':
    run()
