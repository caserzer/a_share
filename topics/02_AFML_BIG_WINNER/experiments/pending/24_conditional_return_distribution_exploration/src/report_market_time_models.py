"""R21 integrity, paired changes, and frozen-goal results."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from run_market_time_models import DEST, SOURCE, CACHE, SOURCE_PANEL, MARKET_PANEL, MODELS, REFERENCE, load_panel, select_training, observation_weights
from run_prequential_search import load_distribution
from run_direct_probability import classes
from run_four_horizons import BIN_NAMES
from report_earnings_revisions import paired_interval, METRICS
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE: 'R20无市场状态参考', 'market_rows': '市场状态、股票行等权',
    'market_month_balanced': '市场状态、月份等权', 'market_window36': '市场状态、36月窗口',
    'market_decay24': '市场状态、24月衰减', 'market_decay24_unmixed': '24月衰减、不混合B',
    'window36_without_market': '36月窗口、无市场状态'}
PAIRS = [('market_rows', REFERENCE, 'market_features'),
    ('market_month_balanced', 'market_rows', 'month_balance'),
    ('market_window36', 'market_month_balanced', 'window36'),
    ('market_decay24', 'market_month_balanced', 'decay24'),
    ('market_window36', 'window36_without_market', 'market_features_same_window'),
    ('market_decay24_unmixed', 'market_decay24', 'remove_shrinkage')]


def event_probabilities(p):
    return np.column_stack([p[:, 4:].sum(axis=1), p[:, :3].sum(axis=1), p[:, 3],
        p[:, 0], p[:, 1], p[:, 2:5].sum(axis=1), p[:, 5], p[:, 6]])


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert hashlib.sha256(SOURCE_PANEL.read_bytes()).hexdigest() == spec['source_panel_sha256']
    assert hashlib.sha256(MARKET_PANEL.read_bytes()).hexdigest() == spec['market_panel_sha256']
    panel = load_panel(); fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 1344 and not fit.duplicated(['months', 'date', 'model']).any()
    assert set(fit.model) == set(LABELS)
    for row in fit[fit.model.isin(MODELS)].itertuples():
        date = pd.Timestamp(row.date); _, window, balance, half_life, _ = MODELS[row.model]
        train = select_training(panel, row.months, date, window)
        weights = observation_weights(train, date, balance, half_life)
        monthly = pd.Series(weights, index=train.date).groupby(level=0).sum()
        assert len(train) == row.training_rows and train.date.nunique() == row.training_months
        assert train[f'end_{row.months}'].max() == pd.Timestamp(row.last_training_label) < date
        assert train.date.min() == pd.Timestamp(row.first_training_origin)
        np.testing.assert_allclose([weights.min(), weights.max(), weights.sum(), monthly.sum()**2/(monthly**2).sum()],
            [row.min_row_weight, row.max_row_weight, row.total_weight, row.effective_market_months], atol=1e-10)
        active = len(train) >= 1000 and train.date.nunique() >= 18
        assert row.adjusted_rows == (row.test_rows if active else 0)
    numeric = ['p_up', 'p_down', 'p_zero', 'brier', 'multiclass_brier', 'crps', 'q05', 'q50', 'q95', 'mean'] + [f'p_{n}' for n in BIN_NAMES]
    probability_cols = numeric[:3] + [f'p_{n}' for n in BIN_NAMES]
    contract = json.loads((TARGET/'target_contract.json').read_text()); receipts = []; diagnostics = []
    for item in contract['files']:
        h = item['months']; basepath = Path(item['path'])
        assert hashlib.sha256(basepath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(basepath); base = base[base.model.eq('B')]
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        refpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_prediction_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(refpath.read_bytes()).hexdigest() == receipt['sha256']
        ref = pd.read_parquet(refpath); ref = ref[ref.model.eq('all_with_revisions')].copy(); ref['model'] = REFERENCE
        pd.testing.assert_frame_equal(ref.reset_index(drop=True), data[data.model.eq(REFERENCE)].reset_index(drop=True))
        for name, group in data.groupby('model'):
            merged = group.merge(base, on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(merged) == len(group) == 27600
            np.testing.assert_allclose(merged.actual, merged.actual_base, equal_nan=True)
            empty_dates = fit[(fit.months == h) & fit.model.eq(name) & fit.adjusted_rows.eq(0)].date
            fallback = merged.date.dt.strftime('%Y-%m-%d').isin(empty_dates)
            np.testing.assert_array_equal(merged.loc[fallback, numeric].to_numpy(), merged.loc[fallback, [f'{x}_base' for x in numeric]].to_numpy())
        assert np.isfinite(data[probability_cols]).all().all() and data[probability_cols].ge(0).all().all()
        np.testing.assert_allclose(data[probability_cols[:3]].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[probability_cols[3:]].sum(axis=1), 1, atol=1e-10)
        observed = data.actual.notna()
        np.testing.assert_allclose(data.loc[observed, 'brier'], (data.loc[observed, 'p_up']-data.loc[observed, 'actual'].gt(0))**2)
        assert data.loc[~observed, METRICS[:3]].isna().all().all()
        assert data.q05.le(data.q50).all() and data.q50.le(data.q95).all()
        # Every new row's event probabilities must reconstruct from the saved
        # fitted class probabilities and the unchanged B distribution cache.
        for date, dated in data.groupby('date'):
            keys = pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', keys)
            cls = classes(ba); bp = np.column_stack([(bw*(cls == k)).sum(axis=1) for k in range(7)])
            for name, (_, _, _, _, alpha) in MODELS.items():
                check = dated[dated.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(check[['date', 'instrument']], keys)
                active = fit[(fit.months == h) & fit.date.eq(str(date.date())) & fit.model.eq(name)].adjusted_rows.iloc[0]
                if not active: continue
                cache_name = 'market_decay24' if name == 'market_decay24_unmixed' else name
                payload = np.load(CACHE/f'{h}_{date.date()}_{cache_name}.npz')
                p = payload['probabilities']; ca = payload['class_atoms']
                assert ca.shape == (224,) and (np.diff(ca) >= 0).all()
                np.testing.assert_array_equal(classes(ca), np.repeat(np.arange(7), 32))
                np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-10)
                np.testing.assert_allclose(check[probability_cols], event_probabilities((1-alpha)*bp+alpha*p), atol=1e-10)
        for (model, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostics.append(dict(months=h, model=model, date=date,
                accuracy=((group.p_up > group.p_down) == y).mean(), up_call_rate=(group.p_up > group.p_down).mean(),
                always_down=(~y).mean(), within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(diagnostics).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    monthly = pd.read_csv(DEST/'monthly_scores.csv'); paired = []
    for h, group in monthly.groupby('months'):
        for metric in METRICS:
            wide = group.pivot(index='date', columns='model', values=metric)
            for new, old, comparison in PAIRS:
                a, b = wide[new].mean(), wide[old].mean(); lo, hi = paired_interval(wide[new], wide[old], metric)
                paired.append(dict(months=h, comparison=comparison, metric=metric, candidate=new, control=old,
                    relative_improvement=a/b-1 if metric == 'accuracy' else 1-a/b,
                    improvement_lower95=lo, improvement_upper95=hi))
    pd.DataFrame(paired).to_csv(DEST/'paired_comparisons.csv', index=False)
    score = pd.read_csv(DEST/'target_scoreboard.csv')
    assert len(score) == 84 and set(score.months) == {1, 3, 6}
    new = score[score.model.isin(MODELS)]; decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=6,
        reused_reference=REFERENCE, prediction_rows_per_model=27600, prior_reference_unchanged=True,
        mature_training_windows_and_weights_verified=True, cached_probabilities_reconstructed_all_rows=True,
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需验证审核，尚不能宣布完成。'
    lines = ['# R21：市场状态与训练时段权重', '', f'**{result}** 新增6候选，另逐值复用R20参考；累计41个新候选。固定原27,600股票月、R15 B及1/3/6个月四项20%门槛。', '',
        '检验分类模型中加入市场趋势/波动/利率估值/历史500只研究池广度，以及月份等权、36月窗口、24月半衰期；另比较相同窗口移除市场输入、相同衰减分布不混合B。其他版本均与B各占50%。所有模型保持100棵深度2、同学习率/正则和随机种子。市场广度不是全A股。', '',
        '月份权重同时用于模型训练与七类别内部的分布，统一缩放至平均行权重1以保持正则量级。最少1000行和18个成熟起点月，缺训练则回退B；标签结束日严格早于决策日。实际股票行数不代表独立市场样本数，记录有效月份并按月份时间块比较。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for model, label in LABELS.items():
            values = score[(score.months == h) & score.model.eq(model)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+' |')
    lines += ['', '正数是改善，负数为恶化。不能拼接不同模型的最好指标。配对明细将市场输入、月份平衡、窗口、衰减和混合权重分别比较；方向诊断包含同月AUC及固定始终下跌参考。', '',
        '## 结果解释', '',
        '市场状态加月份等权模型的3个月上涨Brier改善1.27%、五档Brier改善0.31%、CRPS改善0.60%，命中率53.23%→54.45%（相对+2.29%）。这是小幅改善，远未达到20%；同一模型在1个月概率评分和6个月命中率上仍弱于B。', '',
        '固定36月窗口和24月衰减没有带来稳定同步提升。扩大新模型权重也未解决问题：6个月不混合衰减模型同月AUC约0.543，但整体命中率51.61%，低于固定始终下跌的54.29%。相对排序信息不能替代概率校准和总体方向目标。', '',
        '阶段差异明显：3个月月份等权模型在2021—2023年的方向命中率55.30%（B为57.90%），2024年以后53.26%（B为46.77%）。6个月不混合衰减模型在前段49.64%（B为55.95%），后段54.70%（B为40.75%）。这些是观察到的历史分段，不能据此事后挑选适用时段或宣布完整目标达成。', '',
        '下一步可对本轮已冻结分布进行严格预序列校准或组合：每次只使用当时已到期的旧预测，检验是否能适应阶段性偏差，保留完整测试时期。此前R16对其他模型的校准未达标，本轮更换输入来源也不能预先假定有效；该新校准尚未运行。', '',
        '逐行核验保存的类别概率与B缓存可以重构最终上涨、下跌、零收益和五档概率；同时核验全量成熟标签、窗口、训练权重和旧参考逐值不变。该技术核验不等于预测有效；这里仍是反复查看同一历史区间的探索，尚无新的独立验证。本轮未验证12个月双20%。', '',
        '明细：[目标评分](outputs/r21_market_time_models/target_scoreboard.csv)、[配对比较](outputs/r21_market_time_models/paired_comparisons.csv)、[分阶段](outputs/r21_market_time_models/phase_scores.csv)、[方向诊断](outputs/r21_market_time_models/direction_diagnostics.csv)、[训练权重](outputs/r21_market_time_models/fit_audit.csv)、[技术核验](outputs/r21_market_time_models/research_integrity_audit.json)。', '']
    (EP/'market_time_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
