"""Audit R20 matched ablations, unchanged reference, and original 20% target."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP
from build_eps_panel import pair_for_year
from build_earnings_revisions import DEST, SOURCE, PANEL
from run_earnings_revisions import MODELS, REFERENCE
from run_four_horizons import BIN_NAMES
from diagnose_prediction_target import DEST as TARGET

METRICS = ['brier', 'multiclass_brier', 'crps', 'accuracy']
LABELS = {
    REFERENCE: 'R19盈利分类参考',
    'matched_without_earnings': '同覆盖移除盈利输入',
    'matched_with_revisions': '同覆盖追加预期修正',
    'all_without_earnings': '全量、无盈利输入',
    'all_with_earnings': '全量、盈利输入',
    'all_with_revisions': '全量、盈利及修正',
    'all_with_revisions_unmixed': '全量、盈利及修正、不混合B',
}
PAIRS = [
    (REFERENCE, 'matched_without_earnings', 'matched_earnings'),
    ('matched_with_revisions', REFERENCE, 'matched_revision'),
    ('all_with_earnings', 'all_without_earnings', 'full_earnings'),
    ('all_with_revisions', 'all_with_earnings', 'full_revision'),
    ('all_with_revisions_unmixed', 'all_with_revisions', 'remove_shrinkage'),
]


def paired_interval(new, old, metric):
    n = len(new); rng = np.random.default_rng(24)
    starts = rng.integers(0, n, (2000, int(np.ceil(n/12))))
    ix = ((starts[:, :, None]+np.arange(12)) % n).reshape(2000, -1)[:, :n]
    delta = np.asarray(new)-np.asarray(old) if metric == 'accuracy' else np.asarray(old)-np.asarray(new)
    return np.quantile(delta[ix].mean(axis=1), [.025, .975])


def run():
    features_audit = json.loads((DEST/'feature_audit.json').read_text())
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == features_audit['feature_sha256']
    panel = pd.read_parquet(PANEL)
    test = panel[panel.common_eligible & (panel.date >= '2021-01-01')]
    assert len(test) == 27600
    raw = pd.read_parquet(SOURCE/'validated_extractions.parquet').set_index('infoCode')
    brokers = pd.read_parquet(SOURCE/'selected_reports.parquet').set_index('infoCode').orgCode
    observed_reports = pd.read_parquet(SOURCE/'decision_report_map.parquet').dropna(subset=['infoCode']).groupby('infoCode').date.min()
    for row in panel[panel.revision_available].itertuples():
        current = raw.loc[row.infoCode]; prior = raw.loc[row.previous_report]
        assert current.stockCode == prior.stockCode == row.instrument[2:]
        assert brokers.loc[row.infoCode] == brokers.loc[row.previous_report]
        assert pd.Timestamp(prior.available_date) < pd.Timestamp(current.available_date) < row.date
        assert row.previous_observed_date < row.date
        assert row.previous_observed_date == observed_reports.loc[row.previous_report]
        field = 'profit_forecasts' if row.forecast_basis_profit == 1 else 'forecasts'
        a = pair_for_year(current[field], row.date.year); b = pair_for_year(prior[field], row.date.year)
        assert a is not None and b is not None and (a > 0).all() and (b > 0).all()
        np.testing.assert_allclose(row.growth_revision, np.log(a[1]/a[0])-np.log(b[1]/b[0]), atol=1e-12)
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 1344 and set(fit.model) == set(LABELS)
    assert not fit.duplicated(['months', 'date', 'model']).any()
    dates = pd.to_datetime(fit.last_training_label, errors='coerce')
    assert dates.isna().eq(fit.training_rows.eq(0)).all()
    valid = fit.training_rows.gt(0)
    assert (dates[valid] < pd.to_datetime(fit.loc[valid, 'date'])).all()
    for matched in [[REFERENCE, 'matched_without_earnings', 'matched_with_revisions'], list(MODELS)[2:]]:
        assert fit[fit.model.isin(matched)].groupby(['months', 'date'])[['training_rows', 'test_rows', 'adjusted_rows']].nunique().eq(1).all().all()
    contract = json.loads((TARGET/'target_contract.json').read_text())
    reference_audit = json.loads((SOURCE/'research_integrity_audit.json').read_text())
    numeric = ['p_up', 'p_down', 'p_zero', 'brier', 'multiclass_brier', 'crps', 'q05', 'q50', 'q95', 'mean'] + [f'p_{x}' for x in BIN_NAMES]
    receipts = []; diagnostics = []
    for item in contract['files']:
        h = item['months']; base_path = Path(item['path'])
        assert hashlib.sha256(base_path.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(base_path); base = base[base.model.eq('B')]
        data_path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(data_path)
        assert set(data.model) == set(LABELS)
        ref_path = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in reference_audit['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(ref_path.read_bytes()).hexdigest() == receipt['sha256']
        reference = pd.read_parquet(ref_path); reference = reference[reference.model.eq('earnings_forecast_classes')].copy(); reference['model'] = REFERENCE
        pd.testing.assert_frame_equal(reference.reset_index(drop=True), data[data.model.eq(REFERENCE)].reset_index(drop=True))
        for model, group in data.groupby('model'):
            joined = group.merge(base, on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
            joined = joined.merge(test[['date', 'instrument', 'earnings_pair_available']], on=['date', 'instrument'], validate='one_to_one')
            sizes = fit[(fit.months == h) & fit.model.eq(model)].set_index('date').training_rows
            mature = joined.date.dt.strftime('%Y-%m-%d').map(sizes)
            assert mature.notna().all()
            population = 'matched' if model == REFERENCE else MODELS[model][0]
            fallback = mature.lt(1000) | (~joined.earnings_pair_available if population == 'matched' else False)
            np.testing.assert_array_equal(joined.loc[fallback, numeric].to_numpy(), joined.loc[fallback, [f'{x}_base' for x in numeric]].to_numpy())
            assert int((~fallback).sum()) == fit.loc[(fit.months == h) & fit.model.eq(model), 'adjusted_rows'].sum()
        direction = ['p_up', 'p_down', 'p_zero']; bins = [f'p_{x}' for x in BIN_NAMES]
        assert np.isfinite(data[direction+bins]).all().all() and data[direction+bins].ge(0).all().all()
        np.testing.assert_allclose(data[direction].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[bins].sum(axis=1), 1, atol=1e-10)
        observed = data.actual.notna()
        np.testing.assert_allclose(data.loc[observed, 'brier'], (data.loc[observed, 'p_up']-data.loc[observed, 'actual'].gt(0))**2)
        assert data.loc[~observed, METRICS[:3]].isna().all().all()
        for (model, date), g in pd.concat([data, base]).groupby(['model', 'date']):
            g = g[g.actual.notna() & g.actual.ne(0)]
            if not len(g): continue
            y = g.actual.gt(0)
            diagnostics.append(dict(months=h, model=model, date=date,
                accuracy=((g.p_up > g.p_down) == y).mean(), up_call_rate=(g.p_up > g.p_down).mean(),
                always_up=y.mean(), always_down=(~y).mean(),
                within_month_auc=roc_auc_score(y, g.p_up-g.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(data_path.relative_to(EP)), sha256=hashlib.sha256(data_path.read_bytes()).hexdigest()))
    diagnostic = pd.DataFrame(diagnostics)
    diagnostic.groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    monthly = pd.read_csv(DEST/'monthly_scores.csv'); pairs = []
    for h, group in monthly.groupby('months'):
        for metric in METRICS:
            wide = group.pivot(index='date', columns='model', values=metric)
            for new, old, name in PAIRS:
                a = wide[new].mean(); b = wide[old].mean()
                lo, hi = paired_interval(wide[new], wide[old], metric)
                pairs.append(dict(months=h, ablation=name, candidate=new, control=old, metric=metric,
                    relative_improvement=a/b-1 if metric == 'accuracy' else 1-a/b,
                    improvement_lower95=lo, improvement_upper95=hi))
    pairwise = pd.DataFrame(pairs); pairwise.to_csv(DEST/'matched_ablations.csv', index=False)
    score = pd.read_csv(DEST/'target_scoreboard.csv')
    assert len(score) == 84 and set(score.months) == {1, 3, 6}
    new_scores = score[score.model.isin(MODELS)]
    decisions = new_scores.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=6,
        reused_reference=REFERENCE, prediction_rows_per_model=27600, matched_populations_verified=True,
        prior_reference_unchanged=True, source_revision_arithmetic_verified=True, unchanged_fallback_verified=True,
        passed_point_gates=int(new_scores.point_target_met.sum()), candidates_passing_all_point_gates=decisions,
        feature_sha256=features_audit['feature_sha256'], receipts=receipts,
        evidence='Repeated retrospective exploration; same frozen baseline. Six new candidates and one reused reference, not seven new trials.')
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '仍未达到双20%目标。' if not any(decisions.values()) else '有历史点估计通过目标的候选，尚需独立验证，不能宣布完成。'
    lines = ['# R20：盈利输入的匹配消融与预期修正', '', f'**{result}** 本轮6个新候选，加1个逐值复用的R19参考；累计35个新候选。1/3/6个月分别使用原27,600个股票月、冻结R15 B，所有概率误差降低20%且方向命中率相对提高20%的标准不变。', '',
        f'新增同机构、相同财政年度的增长预期修正，覆盖{features_audit["revision_rows"]:,}个股票月（{features_audit["revision_rows"]/27600:.1%}）。历史仅限更早决策月已观察到的报告，不是完整一致预期，也不是EPS绝对值上调/下调。此前报告与当前报告间隔不超过365日，当前报告不超过180日。', '',
        '第一组保持R19覆盖和同一分类架构，移除盈利增长/估值锚/亏损输入，或追加增长预期修正；第二组保留全部原股票月，分别无盈利、加盈利、再加修正，缺失输入保持为空并提供可用性标记。最后比较相同拟合分布与B混合50%或完全不混合。所有模型均为100棵深度2的七类别树，每月只使用已到期标签。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 方向命中率相对改善 |', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for model, label in LABELS.items():
            values = score[(score.months == h) & score.model.eq(model)].set_index('metric')
            formatted = [f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS]
            lines.append(f'| {h}个月 | {label} | '+' | '.join(formatted)+' |')
    lines += ['', '正数是改善，负数是变差。所有结果按预测月份等权，不删除缺数据的股票月、不拼接不同模型的最好指标。上表相对冻结B；输入是否有增量须另看同覆盖、同架构配对。', '',
        '## 配对消融', '', '| 期限 | 比较 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 方向命中率相对改善 |', '|---|---|---|---|---|---|']
    pair_names = dict(matched_earnings='同覆盖加入盈利', matched_revision='同覆盖再加修正', full_earnings='全量加入盈利', full_revision='全量再加修正', remove_shrinkage='取消50%混合')
    for h in [1, 3, 6]:
        for name, label in pair_names.items():
            values = pairwise[(pairwise.months == h) & pairwise.ablation.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+' |')
    lines += ['', '配对明细包含12个月时间块的95%区间；多次查看同一历史区间仍存在探索偏差，不能声称独立验证。方向诊断另列固定全涨/全跌、上涨判断比例、同月AUC，避免把样本方向比例当成逐股辨别能力。', '',
        '## 结果解释与下一问题', '',
        '6个月同覆盖、无盈利输入模型命中率51.47%；加入盈利后51.59%，再加入增长预期修正为51.76%。后两步分别只增加约0.12和0.17个百分点，配对95%区间均跨零。相比B的50.02%，最终相对改善3.46%，远低于要求的20%。因此上轮+3.13%的结果大部分不能归因于盈利预测本身。', '',
        '全量模型3个月概率误差有不足1%的改善，但6个月扩大覆盖后的命中率约48.2%；取消与B混合后约49.7%，仍不及原B。增加训练/预测覆盖与改变缺失处理是一起发生的，不能把退化单独归因于某一种缺失处理。', '',
        '方向诊断进一步显示：6个月同覆盖修正模型51.76%的命中率低于始终预测下跌的54.29%。全量不混合模型同月AUC约0.537，高于B的0.517，但总体命中率仍更差。这提示在本次历史中，个股相对排序略有信息，而市场整体方向与概率校准依然薄弱；AUC改善不能代替目标。', '',
        '下一步优先检验分类模型中的市场状态输入和训练时段权重，补固定窗口/时间衰减对照，以区分旧样本分布变化与市场方向判断错误。此前其他近邻/市场重加权方法未达标，不能假定这次会有效；此方向尚未运行。本轮没有新的独立留出验证，也没有证明稳定优势。', '',
        '发现一处原文EPS“078”与同句PE关系不一致，排除了该报告的2027年值，未猜测修复；已确认这个第三年值不在R19的当年/次年输入中，因此原参考预测未改动。记录与原字节哈希见feature_audit.json。', '',
        '明细：[目标评分](outputs/r20_earnings_revisions/target_scoreboard.csv)、[配对消融及区间](outputs/r20_earnings_revisions/matched_ablations.csv)、[阶段表现](outputs/r20_earnings_revisions/phase_scores.csv)、[方向诊断](outputs/r20_earnings_revisions/direction_diagnostics.csv)、[技术核验](outputs/r20_earnings_revisions/research_integrity_audit.json)。本轮未检验12个月双20%目标；技术正确不等于预测目标完成。', '']
    (EP/'earnings_revision_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
