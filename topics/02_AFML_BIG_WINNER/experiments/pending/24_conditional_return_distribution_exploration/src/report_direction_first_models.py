"""R26 verify conditional labels, frozen shapes and unchanged sign marginals."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from run_direction_first_models import DEST, CACHE, SOURCE, SOURCE_CACHE, PANEL, REFERENCE, MODELS
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from hierarchical_probabilities import sign_classes, conditional_magnitudes, assemble_classes, stable_sign_scores, validate_probabilities
from report_distribution_shape_models import probability_reliability
from report_earnings_revisions import METRICS, paired_interval
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE: 'R25原样参考', 'sign_reweight_mixed': '方向重加权、混合',
    'sign_reweight_unmixed': '方向重加权、独立', 'sign_hierarchy_mixed': '分层幅度、混合',
    'sign_hierarchy_unmixed': '分层幅度、独立'}
PAIRS = [('sign_reweight_mixed', REFERENCE, 'direct_sign'),
    ('sign_hierarchy_mixed', 'sign_reweight_mixed', 'conditional_magnitude_mixed'),
    ('sign_hierarchy_unmixed', 'sign_reweight_unmixed', 'conditional_magnitude_unmixed'),
    ('sign_reweight_unmixed', 'sign_reweight_mixed', 'remove_blend_sign'),
    ('sign_hierarchy_unmixed', 'sign_hierarchy_mixed', 'remove_blend_hierarchy')]


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == spec['feature_sha256']
    assert hashlib.sha256((EP/'notes/r26_direction_first.md').read_bytes()).hexdigest() == spec['plan_sha256']
    panel = pd.read_parquet(PANEL); keys = ['date', 'instrument']
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 192 and not fit.duplicated(['months', 'date']).any()
    source_receipts = pd.read_csv(DEST/'source_cache_receipts.csv')
    assert len(source_receipts) == 384 and not source_receipts.path.duplicated().any()
    for r in source_receipts.itertuples():
        assert hashlib.sha256(Path(r.path).read_bytes()).hexdigest() == r.sha256
    contract = json.loads((TARGET/'target_contract.json').read_text())
    receipts = []; diagnostic = []; calibration = []; reliability = []; reconstructed = 0; marginal_max_error = 0.
    for item in contract['files']:
        h = item['months']; bpath = Path(item['path'])
        assert hashlib.sha256(bpath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(bpath); base = base[base.model.eq('B')]
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        oldpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(oldpath.read_bytes()).hexdigest() == receipt['sha256']
        old = pd.read_parquet(oldpath); old = old[old.model.eq('own_momentum_control')].assign(model=REFERENCE)
        pd.testing.assert_frame_equal(data[data.model.eq(REFERENCE)].reset_index(drop=True), old.reset_index(drop=True))
        for name, group in data.groupby('model'):
            j = group.merge(base[keys+['actual', 'label_end', 'target_date']], on=keys, suffixes=('', '_base'), validate='one_to_one')
            assert len(j) == len(group) == 27600
            np.testing.assert_allclose(j.actual, j.actual_base, equal_nan=True)
            for c in ['label_end', 'target_date']: pd.testing.assert_series_equal(j[c], j[c+'_base'], check_names=False)
        for date, dated in data.groupby('date'):
            r = fit[fit.months.eq(h) & fit.date.eq(str(date.date()))].iloc[0]
            train = select_training(panel, h, date, None); weights = observation_weights(train, date, True, None)
            y = train[f'y_{h}'].to_numpy(); c = classes(y); signs = sign_classes(y)
            assert len(train) == r.training_rows and train.date.nunique() == r.training_months
            assert train[f'end_{h}'].max() == pd.Timestamp(r.last_training_label) < date
            assert r.negative_rows == (y < 0).sum() and r.zero_rows == (y == 0).sum() and r.positive_rows == (y > 0).sum()
            np.testing.assert_allclose([r.total_weight, r.negative_weight, r.positive_weight], [weights.sum(), weights[y < 0].sum(), weights[y > 0].sum()])
            saved_keys = pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', saved_keys)
            baseline_sign = np.column_stack([(bw*(ba < 0)).sum(axis=1), (bw*(ba == 0)).sum(axis=1), (bw*(ba > 0)).sum(axis=1)])
            if r.adjusted_rows:
                with np.load(CACHE/f'{h}_{date.date()}.npz') as payload:
                    sign, negative, positive, prior, atoms = [payload[k] for k in ['sign', 'negative', 'positive', 'prior', 'class_atoms']]
                for arr in [sign, negative, positive]: validate_probabilities(arr, 3)
                np.testing.assert_allclose(prior, np.bincount(c, weights=weights, minlength=7)/weights.sum())
                with np.load(SOURCE_CACHE/f'{h}_{date.date()}_own_momentum_control.npz') as payload:
                    flat = payload['probabilities']; np.testing.assert_array_equal(atoms, payload['class_atoms'])
                expected, _ = weighted_class_distribution(y, c, np.full((1, 7), 1/7), weights)
                np.testing.assert_array_equal(atoms, expected[0])
                for label, mask, target, prob, minimum in [('sign', np.ones(len(y), dtype=bool), signs, sign, 1000),
                    ('negative', y < 0, c[y < 0], negative, 300), ('positive', y > 0, c[y > 0]-4, positive, 300)]:
                    mode = getattr(r, label+'_mode')
                    fallback = mask.sum() < minimum or len(np.unique(target)) < 2
                    assert mode == ('mature_weighted_frequency' if fallback else 'classifier')
                    if fallback:
                        frequency = np.bincount(target, weights=weights[mask], minlength=3)
                        frequency = frequency/frequency.sum() if frequency.sum() > 0 else np.full(3, 1/3)
                        np.testing.assert_allclose(prob, np.tile(frequency, (len(saved_keys), 1)))
                    elif len(np.unique(target)) < 3:
                        assert (prob[:, list(set(range(3))-set(target))] == 0).all()
                old_neg, old_pos = conditional_magnitudes(flat, prior)
                predictions = {'sign_reweight': assemble_classes(sign, old_neg, old_pos), 'sign_hierarchy': assemble_classes(sign, negative, positive)}
            for name, (kind, fraction) in MODELS.items():
                group = dated[dated.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(group[keys], saved_keys)
                if not r.adjusted_rows:
                    pd.testing.assert_frame_equal(group, base[base.date.eq(date)].assign(model=name).reset_index(drop=True))
                    continue
                a = np.tile(atoms, (len(group), 1)); w = np.repeat(predictions[kind]/32, 32, axis=1)
                aa, ww = combine_distributions([(ba, bw), (a, w)], [1-fraction, fraction]) if fraction < 1 else (a, w)
                raw = weighted_stats(aa, ww, group.actual)
                stable = stable_sign_scores(raw, sign, baseline_sign, fraction, group.actual)
                np.testing.assert_allclose(stable[['p_up', 'p_down', 'p_zero']], raw[['p_up', 'p_down', 'p_zero']], atol=1e-12, rtol=0)
                marginal_max_error = max(marginal_max_error, float(np.abs(stable[['p_up', 'p_down', 'p_zero']].to_numpy()-raw[['p_up', 'p_down', 'p_zero']].to_numpy()).max()))
                np.testing.assert_allclose(group[stable.columns], stable, atol=1e-12, rtol=1e-12, equal_nan=True)
                reconstructed += len(group)
            for suffix in ['mixed', 'unmixed']:
                a = dated[dated.model.eq('sign_reweight_'+suffix)].reset_index(drop=True)
                b = dated[dated.model.eq('sign_hierarchy_'+suffix)].reset_index(drop=True)
                np.testing.assert_array_equal(a[['p_up', 'p_down', 'p_zero', 'brier']], b[['p_up', 'p_down', 'p_zero', 'brier']])
                np.testing.assert_array_equal(a.p_up > a.p_down, b.p_up > b.p_down)
        for name, group in pd.concat([data, base]).groupby('model'):
            cells, summary = probability_reliability(group)
            reliability.append(cells.assign(months=h, model=name)); calibration.append(dict(months=h, model=name, **summary))
        for (name, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostic.append(dict(months=h, date=date, model=name, accuracy=((group.p_up > group.p_down) == y).mean(),
                up_call_rate=(group.p_up > group.p_down).mean(), always_down=(~y).mean(),
                within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(diagnostic).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability, ignore_index=True).to_csv(DEST/'probability_reliability.csv', index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv', index=False)
    monthly = pd.read_csv(DEST/'monthly_scores.csv'); pairs = []
    for h, group in monthly.groupby('months'):
        for metric in METRICS:
            wide = group.pivot(index='date', columns='model', values=metric)
            for new, old, comparison in PAIRS:
                a, b = wide[new].mean(), wide[old].mean(); lo, hi = paired_interval(wide[new], wide[old], metric)
                pairs.append(dict(months=h, comparison=comparison, metric=metric,
                    relative_improvement=a/b-1 if metric == 'accuracy' else 1-a/b,
                    improvement_lower95=lo, improvement_upper95=hi))
    pd.DataFrame(pairs).to_csv(DEST/'paired_comparisons.csv', index=False)
    score = pd.read_csv(DEST/'target_scoreboard.csv'); assert len(score) == 60
    new = score[score.model.isin(MODELS)]; assert len(new) == 48
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=4,
        original_rows_per_model=27600, mature_training_and_conditional_labels_checked=True,
        original_labels_and_reference_unchanged=True, frozen_class_atoms_and_source_cache_verified=True,
        shared_sign_probabilities_and_decisions_exactly_equal=True, analytic_vs_atom_sign_max_error=marginal_max_error,
        fully_reconstructed_new_prediction_rows=reconstructed, passed_point_gates=int(new.point_target_met.sum()),
        candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需验证审核，不能直接宣布完成。'
    lines = ['# R26：直接方向学习与分层分布', '', f'**{result}** 本轮4个新候选和1个原样参考。原B、27,600股票月、三期限四项20%门槛不变。', '',
        '使用R25自身动量对照的同38个输入和相同成熟训练行，直接拟合下跌/持平/上涨；再保留原正负幅度比例，或分别学习正负幅度。每个结构报告独立分布与50%B混合。幅度结构共用方向概率，不能通过另选方向阈值提升命中率。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 | 实际命中率 |', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            v = score[score.months.eq(h) & score.model.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{v.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+f' | {v.loc["accuracy", "value"]:.2%} |')
    phase = pd.read_csv(DEST/'phase_scores.csv')
    direction = pd.DataFrame(diagnostic).groupby(['months', 'model']).mean(numeric_only=True)
    lines += ['', f'6个月独立方向版本命中率{direction.loc[(6, "sign_reweight_unmixed"), "accuracy"]:.2%}，仍低于始终判断下跌的描述性参考{direction.loc[(6, "B"), "always_down"]:.2%}。这不是改换验收基线；原B与20%门槛保持不变。该模型上涨判定占比{direction.loc[(6, "sign_reweight_unmixed"), "up_call_rate"]:.2%}，不能将其表现归因于单纯全判下跌。', '',
        '6个月同一独立方向版本的分阶段命中率：', '', '| 阶段 | 原B | 独立方向重加权 |', '|---|---|---|']
    for period in ['2021_2023', '2024_plus']:
        v = phase[phase.months.eq(6) & phase.phase.eq(period)].set_index('model')
        lines.append(f'| {period} | {v.loc["frozen_B", "accuracy"]:.2%} | {v.loc["sign_reweight_unmixed", "accuracy"]:.2%} |')
    lines += ['', '正数为改善，负数为变差。共享方向模型的两个幅度版本，其上涨Brier和方向命中率完全相同；五档与CRPS的区别用于判断幅度学习增量。不同结构拟合数量不同，不能归因于仅改变损失且容量完全一致。', '',
        f'核验全部原人群/标签/目标日期、成熟条件标签与权重、来源缓存哈希、旧参考和类内原子不变、全部{reconstructed:,}条新预测概率与评分重建。解析方向边际与原子边际最大浮点差{marginal_max_error:.2e}，两个幅度结构的方向概率和决策逐值一致。技术核验不等于预测有效。', '',
        '仍是反复历史探索，原数据版本与股票池偏差未解决，未验证12月双20%。不能将不同模型的最好指标拼接成达标结果。', '',
        '明细：[事前方案](notes/r26_direction_first.md)、[目标评分](outputs/r26_direction_first/target_scoreboard.csv)、[匹配对照](outputs/r26_direction_first/paired_comparisons.csv)、[分阶段](outputs/r26_direction_first/phase_scores.csv)、[概率校准](outputs/r26_direction_first/calibration_summary.csv)、[方向诊断](outputs/r26_direction_first/direction_diagnostics.csv)、[核验](outputs/r26_direction_first/research_integrity_audit.json)。', '']
    (EP/'direction_first_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
