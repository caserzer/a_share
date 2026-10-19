"""R19 same-population audit and report, runnable only after full scoring."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP
from fetch_eps_reports import DEST
from build_eps_panel import PANEL
from diagnose_prediction_target import DEST as TARGET_DIR
from run_eps_ablation import GROUPS
from run_four_horizons import BIN_NAMES

LABELS = {
    'eps_historical_control': '同覆盖历史盈利对照',
    'eps_forecast_capped': '原始EPS预测、30%截断',
    'eps_forecast_raw': '原始EPS预测、不作30%截断',
    'earnings_forecast_raw': 'EPS加净利润代理近邻',
    'earnings_forecast_classes': 'EPS加净利润代理分类',
}
METRICS = ['brier', 'multiclass_brier', 'crps', 'accuracy']


def run():
    source = pd.read_parquet(DEST/'validated_extractions.parquet')
    selection = json.loads((DEST/'selection.json').read_text())
    selected = pd.read_parquet(DEST/'selected_reports.parquet')
    assert len(source) == selection['selected_reports'] == len(selected)
    assert not source.infoCode.duplicated().any()
    assert set(source.infoCode) == set(selected.infoCode)
    assert not source.status.eq('fetch_failed').any()
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 960 and not fit.duplicated(['months', 'date', 'model']).any()
    label_dates = pd.to_datetime(fit.last_training_label, errors='coerce')
    assert label_dates.isna().eq(fit.training_rows.eq(0)).all()
    assert (label_dates[fit.training_rows.gt(0)] < pd.to_datetime(fit.loc[fit.training_rows.gt(0), 'date'])).all()
    assert (fit.adjusted_rows <= fit.test_rows).all()
    controls = fit[fit.model.isin(list(GROUPS)[:3])]
    assert controls.groupby(['months', 'date'])[['training_rows', 'test_rows', 'adjusted_rows']].nunique().eq(1).all().all()
    panel = pd.read_parquet(PANEL)
    features = panel[panel.common_eligible & (panel.date >= '2021-01-01')]
    assert len(features) == 27600
    available = features.earnings_pair_available
    assert (pd.to_datetime(features.loc[available, 'available_date']) < features.loc[available, 'date']).all()
    assert features.loc[available, 'forecast_age_days'].between(1, 180).all()
    contract = json.loads((TARGET_DIR/'target_contract.json').read_text())
    numeric = ['p_up', 'p_down', 'p_zero', 'brier', 'multiclass_brier', 'crps', 'q05', 'q50', 'q95', 'mean'] + [f'p_{x}' for x in BIN_NAMES]
    receipts = []
    adjusted = []
    for item in contract['files']:
        baseline_path = Path(item['path'])
        assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(baseline_path); base = base[base.model.eq('B')]
        path = DEST/f'predictions_{item["months"]}m.parquet'
        data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        for model, group in data.groupby('model'):
            joined = group.merge(base, on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
            flag = GROUPS[model][0] if model in GROUPS else 'earnings_pair_available'
            joined = joined.merge(features[['date', 'instrument', flag]], on=['date', 'instrument'], validate='one_to_one')
            training = fit[(fit.months == item['months']) & fit.model.eq(model)].set_index('date').training_rows
            sizes = joined.date.dt.strftime('%Y-%m-%d').map(training)
            assert sizes.notna().all()
            fallback = ~joined[flag] | sizes.lt(1000)
            np.testing.assert_array_equal(joined.loc[fallback, numeric].to_numpy(), joined.loc[fallback, [f'{x}_base' for x in numeric]].to_numpy())
            expected_count = fit.loc[(fit.months == item['months']) & fit.model.eq(model), 'adjusted_rows'].sum()
            assert (~fallback).sum() == expected_count
            adjusted.append(dict(months=item['months'], model=model, adjusted_rows=int(expected_count), fallback_rows=int(fallback.sum())))
        direction = ['p_up', 'p_down', 'p_zero']; bins = [f'p_{x}' for x in BIN_NAMES]
        assert np.isfinite(data[direction+bins]).all().all()
        assert data[direction+bins].ge(0).all().all() and data[direction+bins].le(1+1e-10).all().all()
        np.testing.assert_allclose(data[direction].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[bins].sum(axis=1), 1, atol=1e-10)
        observed = data.actual.notna()
        np.testing.assert_allclose(data.loc[observed, 'brier'], (data.loc[observed, 'p_up']-(data.loc[observed, 'actual'] > 0))**2)
        assert data.loc[~observed, METRICS[:3]].isna().all().all()
        assert data.q05.le(data.q50+1e-10).all() and data.q50.le(data.q95+1e-10).all()
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    scores = pd.read_csv(DEST/'target_scoreboard.csv')
    assert len(scores) == 60 and set(scores.months) == {1, 3, 6}
    decisions = scores.groupby('model').point_target_met.all().to_dict()
    # Pairwise source ablation: same adjusted rows, monthly equal weighting.
    monthly = pd.read_csv(DEST/'monthly_scores.csv')
    pairwise = []
    for horizon, group in monthly.groupby('months'):
        for metric in METRICS:
            wide = group.pivot(index='date', columns='model', values=metric)
            for candidate in ['eps_forecast_capped', 'eps_forecast_raw']:
                control = wide.eps_historical_control.mean(); value = wide[candidate].mean()
                improvement = value/control-1 if metric == 'accuracy' else 1-value/control
                pairwise.append(dict(months=horizon, model=candidate, metric=metric, historical_control=control,
                                     forecast_value=value, relative_improvement=improvement))
    pd.DataFrame(pairwise).to_csv(DEST/'matched_source_ablation.csv', index=False)
    pd.DataFrame(adjusted).to_csv(DEST/'adjusted_coverage.csv', index=False)
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active',
        candidates_passing_all_point_gates=decisions, passed_point_gates=int(scores.point_target_met.sum()),
        candidate_count=5, prediction_rows_per_model=27600, source_reports=len(source),
        unchanged_fallback_verified=True, matched_eps_controls_verified=True, receipts=receipts,
        feature_sha256=hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        evidence='Repeated retrospective exploration. Single latest public original report, not full consensus or immutable vintages.')
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    fa = json.loads((DEST/'feature_audit.json').read_text())
    from analyze_eps_ceiling import analyze
    ceiling = analyze()
    result = '尚无方法达到原定双20%目标。' if not any(decisions.values()) else '存在通过历史点估计门槛的候选，尚需独立验证，不能宣布目标完成。'
    lines = ['# R19：原始盈利预测与历史盈利代理消融', '', f'**{result}** 本轮5个候选，累计29个。固定R15 B、27,600个股票月和1/3/6个月；上涨Brier、五档Brier、CRPS均降低20%，方向命中率相对提高20%，逐期限同时验收。', '',
        f'已取得全部{len(source):,}篇选定原文。解析状态：'+json.dumps(fa['source_statuses'], ensure_ascii=False)+'。', '',
        f'测试股票月有明确财政年度EPS对{fa["eps_available"]:,}行，其中两年均为正数{fa["eps_positive"]:,}行；允许归母净利润代理后有盈利预测对{fa["earnings_available"]:,}行。没有数据的行仍保留，并逐值回退B；训练不足1000行也回退B。实际参与调整的行数见覆盖文件。', '',
        '只使用严格早于决策日、180日内最新报告；报告年份和数值由正文明确给出。输入是决策日所在财政年与下一财政年预测增长，并非未来实际收益标签，也不是滚动12个月一致预期。单篇报告有选择偏差，公开历史页面也不是不可修改版本。', '',
        '前三个模型使用相同的EPS正值训练与查询行：历史盈利增长代理、原始EPS增长但沿用±30%截断、原始EPS增长不作该截断。其余两个使用EPS，缺EPS时使用单独标记的归母净利润增长代理。所有有效新分布与B各混合50%。', '',
        '| 期限 | 方法 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |', '|---|---|---|---|---|---|']
    for horizon in [1, 3, 6]:
        for model, label in LABELS.items():
            values = scores[(scores.months == horizon) & scores.model.eq(model)].set_index('metric')
            formatted = [f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS]
            lines.append(f'| {horizon}个月 | {label} | '+' | '.join(formatted)+' |')
    lines += ['', '正数为改善，负数为恶化；以上均相对冻结B，不能拼接不同模型的最好指标。原始EPS与同覆盖历史盈利对照的直接差异另见消融明细。', '',
        '## 结果解释', '',
        '同覆盖来源消融显示，将历史盈利增长换成原始EPS预测，概率评分改善仅约0.00%—0.04%，方向命中率变化不到0.1%。解除±30%截断也没有带来明显改善。这不支持把原来的主要问题简单归因于缺少分析师EPS或增长截断。', '',
        '浅层分类模型6个月方向命中率由50.02%升至51.59%（相对+3.13%）；上涨Brier、五档Brier、CRPS分别改善0.65%、0.27%、0.43%。但该模型同时使用波动、规模、动量、信用、估值等输入，不能把这部分改善单独归因于EPS：尚缺同架构、同覆盖、移除盈利输入的分类对照。', '',
        '分阶段看，该分类模型2024年以后的6个月方向命中率仅42.41%（B为40.75%），五档误差和CRPS略变差。因此总体小幅改善不构成稳定预测优势。下一步应先补分类模型的匹配消融，再检验盈利预期的修正信息；本轮静态增长水平没有提供足够增量。', '',
        '解析试验180篇，人工核对25篇，并剔除一个附加调整口径利润样例。扩展检查发现尾随公告年份被当作预测值、跨年度与季度的错误绑定，已修正规则并在训练前重新解析全部缓存。另有两篇原文数字与同句增速或PE关系不一致，保留缺失而不猜测小数点；排除依据与原文哈希见extraction_validation.json。2018、2019抽样正文为空，属于该来源缺口；未识别的表达保留缺失，不能解释为报告没有盈利预测。EPS与净利润使用不同口径标记；亏损不强制改为正数。', '',
        '全量来源检查补充：所选2018年191篇、2019年1,479篇的HTML正文全部为空；2020年1,601篇中1,144篇为空。这只说明本次所选报告在此HTML来源的缺口，并不证明其他渠道或原PDF同样不可用。见[source_body_coverage.csv](outputs/r19_eps_expectations/source_body_coverage.csv)。', '',
        '这仍是反复查看同一历史区间的探索，不能当作新的独立验证。12个月尚未纳入本轮20%比较。技术核验通过不等于预测有效。', '',
        f'另核对固定50%混合与实际回退范围带来的理论上限：假设新候选能完全知道每个未来结果，仍有{int((~ceiling.twenty_percent_possible).sum())}个“模型×期限×指标”组合无法达到20%。这是利用真实结果的oracle诊断，不是预测成绩；仅用于判断下一步是否需要改变混合/覆盖结构。明细见[结构上限](outputs/r19_eps_expectations/mixture_ceiling_oracle_only.csv)。', '',
        '明细：[目标评分](outputs/r19_eps_expectations/target_scoreboard.csv)、[同覆盖来源消融](outputs/r19_eps_expectations/matched_source_ablation.csv)、[分阶段结果](outputs/r19_eps_expectations/phase_scores.csv)、[实际调整覆盖](outputs/r19_eps_expectations/adjusted_coverage.csv)、[技术核验](outputs/r19_eps_expectations/research_integrity_audit.json)。', '']
    (EP/'eps_expectations_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
