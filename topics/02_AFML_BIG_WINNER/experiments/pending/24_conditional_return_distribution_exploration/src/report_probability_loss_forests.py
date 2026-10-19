"""R40 reconstruct mature losses, leaf probabilities and every new forecast."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP
from build_margin_information import digest
from run_probability_loss_forests import DEST, CACHE, PANEL, PLAN, REFERENCE, MODELS, PARAMS, CONTROL
from run_issuer_calibration import priors
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from conditional_forests import training_impute
from run_direct_probability import classes
from run_joint_information import frame_digest, score
from probability_loss_forests import loss_targets, leaf_means, leaf_probabilities
from evaluate_improvement_search import evaluate, METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {'extra_reference': '原分类森林混合对照', 'ordinal_raw': '有序损失独立',
    'ordinal_mixed': '有序损失混合', 'joint_raw': '联合概率损失独立', 'joint_mixed': '联合概率损失混合'}
PAIRS = [(name, 'extra_reference', name) for name in MODELS]
PAIRS += [(k+'_raw', k+'_mixed', k+'_raw_increment') for k in ['ordinal', 'joint']]
PAIRS += [('joint_'+k, 'ordinal_'+k, 'joint_'+k+'_loss_increment') for k in ['raw', 'mixed']]


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert spec['models'] == {k:list(v) for k, v in MODELS.items()}
    assert spec['parameters'] == PARAMS and spec['features'] == CONTROL
    assert digest(PANEL) == spec['panel_sha256'] and digest(PLAN) == spec['plan_sha256']
    for receipt in json.loads((DEST/'source_receipts.json').read_text()):
        assert digest(Path(receipt['path'])) == receipt['sha256']
    contract = json.loads((TARGET/'target_contract.json').read_text())
    panel = pd.read_parquet(PANEL); fits = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fits) == 384 and not fits.duplicated(['months', 'date', 'kind']).any()
    checked=0; reconstructed=0; receipts=[]; diagnostics=[]; reliability=[]; calibration=[]
    for item in contract['files']:
        h = item['months']; bp = Path(item['path']); assert digest(bp) == item['sha256']
        base = pd.read_parquet(bp); base = base[base.model.eq('B')]
        rp = REFERENCE/f'predictions_{h}m.parquet'
        sr = next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name)); assert digest(rp) == sr['sha256']
        ref = pd.read_parquet(rp); ref = ref[ref.model.eq('extra_reference')]
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path); assert set(data.model) == set(LABELS)
        pd.testing.assert_frame_equal(data[data.model.eq('extra_reference')].reset_index(drop=True), ref.reset_index(drop=True))
        for name, g in data.groupby('model'):
            j = g.merge(base[['date', 'instrument', 'actual', 'label_end', 'target_date']],
                on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(j) == len(g) == 27600
            np.testing.assert_allclose(j.actual, j.actual_base, equal_nan=True)
            for c in ['label_end', 'target_date']: pd.testing.assert_series_equal(j[c], j[c+'_base'], check_names=False)
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date', 'instrument']]; stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stem}_keys.parquet'), keys)
            distributions, _ = priors(h, date, base, ref, keys); template, ba, bw = distributions['base']
            train = select_training(panel, h, date, None); w = observation_weights(train, date, True, None)
            y = train[f'y_{h}'].to_numpy(); labels = classes(y)
            atoms, _ = weighted_class_distribution(y, labels, np.full((1, 7), 1/7), w)
            tx, qx, medians = training_impute(train[CONTROL], test[CONTROL])
            for kind in ['ordinal', 'joint']:
                r = fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits.kind.eq(kind)]
                assert len(r) == 1; r = r.iloc[0]
                assert len(train) == r.training_rows and train.date.nunique() == r.training_months
                assert train[f'end_{h}'].max() == pd.Timestamp(r.last_training_label) < date
                assert len(test) == r.test_rows; np.testing.assert_allclose(w.sum(), r.total_weight)
                assert frame_digest(train[CONTROL]) == r.train_features_sha256 and frame_digest(test[CONTROL]) == r.test_features_sha256
                assert hashlib.sha256(tx.tobytes()).hexdigest() == r.imputed_train_sha256
                assert hashlib.sha256(qx.tobytes()).hexdigest() == r.imputed_test_sha256
                targets, metadata = loss_targets(y, w, kind)
                assert hashlib.sha256(targets.tobytes()).hexdigest() == r.targets_sha256
                assert targets.shape[1] == r.target_dimensions
                cp = CACHE/f'{stem}_{kind}.npz'; assert digest(cp) == r.cache_sha256
                with np.load(cp) as payload:
                    np.testing.assert_array_equal(payload['class_atoms'], atoms[0]); np.testing.assert_array_equal(payload['medians'], medians)
                    for key, value in metadata.items(): np.testing.assert_array_equal(payload[key], value)
                    tr, te = payload['train_leaves'], payload['test_leaves']
                    assert tr.shape == (len(train), 96) and te.shape == (len(test), 96)
                    assert tr.min() >= 0 and tr.max() < 127 and te.min() >= 0 and te.max() < 127
                    p = leaf_probabilities(tr, te, y, w)
                    np.testing.assert_allclose(p, payload['probabilities'], atol=1e-12, rtol=1e-12)
                    np.testing.assert_allclose(leaf_means(tr, te, targets, w), payload['predicted_targets'], atol=1e-11, rtol=1e-11)
                    if kind == 'ordinal':
                        np.testing.assert_allclose(p.cumsum(axis=1)[:, :6], payload['predicted_targets'], atol=1e-12)
                    else:
                        expected_marginals = np.column_stack([p[:, 4:].sum(axis=1), p[:, 0], p[:, 1], p[:, 2:5].sum(axis=1), p[:, 5], p[:, 6]])
                        np.testing.assert_allclose(expected_marginals, payload['predicted_targets'][:, :6]/metadata['scales'][:6], atol=1e-12)
                checked += 1
                for mode, fraction in [('raw', 1.), ('mixed', .5)]:
                    expected = score(template, ba, bw, np.tile(atoms[0], (len(test), 1)), p, fraction)
                    g = data[data.date.eq(date)&data.model.eq(f'{kind}_{mode}')].reset_index(drop=True)
                    pd.testing.assert_frame_equal(g[['date', 'instrument']], keys)
                    np.testing.assert_allclose(g[expected.columns], expected, atol=1e-12, rtol=1e-12, equal_nan=True)
                    assert np.array_equal(g.p_up.gt(g.p_down), expected.p_up.gt(expected.p_down))
                    reconstructed += len(g)
        for name, g in pd.concat([data, base]).groupby('model'):
            cells, summary = probability_reliability(g)
            reliability.append(cells.assign(months=h, model=name)); calibration.append(dict(months=h, model=name, **summary))
            for date, m in g.groupby('date'):
                m = m[m.actual.notna()&m.actual.ne(0)]
                if not len(m): continue
                y = m.actual.gt(0)
                diagnostics.append(dict(months=h, date=date, model=name, accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(), within_month_auc=roc_auc_score(y, m.p_up-m.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=digest(path))); print(h, 'reconstructed', flush=True)
    assert checked == 384 and reconstructed == 331200
    pd.DataFrame(diagnostics).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability, ignore_index=True).to_csv(DEST/'probability_reliability.csv', index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv', index=False)
    evaluate(DEST)
    monthly = pd.read_csv(DEST/'monthly_scores.csv'); pairs=[]
    for h, group in monthly.groupby('months'):
        for metric in METRICS:
            wide = group.pivot(index='date', columns='model', values=metric)
            for new, old, name in PAIRS:
                a, b = wide[new].mean(), wide[old].mean(); lo, hi = paired_interval(wide[new], wide[old], metric)
                pairs.append(dict(months=h, comparison=name, metric=metric, relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,
                    improvement_lower95=lo, improvement_upper95=hi))
    paired = pd.DataFrame(pairs); paired.to_csv(DEST/'paired_comparisons.csv', index=False)
    scores = pd.read_csv(DEST/'target_scoreboard.csv'); new = scores[scores.model.isin(MODELS)]
    assert len(scores) == 60 and len(new) == 48
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=4,
        cumulative_complete_candidates=139, original_stock_dates_per_model=27600, maturity_loss_leaf_checks=checked,
        all_new_prediction_rows_reconstructed=reconstructed, passed_point_gates=int(new.point_target_met.sum()),
        candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '点估计有达标候选，仍需验证审核。'
    lines = ['# R40：用概率损失选择森林分裂', '', f'**{result}** 四个新增候选，累计139个完整评分候选。原B、27,600股票月、1/3/6月全部12项门槛不变。', '',
        '保持原38项输入、96棵树、深度6、最小叶150、月份等权及成熟标签，改用有序累计概率损失或联合三项概率损失选择分裂。联合项按训练无条件误差归一化，CRPS用32个训练分位区间的中点积分近似。各树叶内按原样本权重还原七档概率，幅度仍为训练全局分位点；分别报告独立和50%原B混合。没有预测收益点值后冒充概率。', '',
        '|期限|候选|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            v = scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines += ['', '上表相对原B。下表同名候选相对原分类森林混合对照；“独立增量”相对同损失混合版，“联合增量”相对相同混合比例有序版。正值为改善。', '',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|', '|---|---|---|---|---|---|']
    extras = {'ordinal_raw_increment':'有序独立增量', 'joint_raw_increment':'联合独立增量',
        'joint_raw_loss_increment':'独立版联合增量', 'joint_mixed_loss_increment':'混合版联合增量'}
    for h in [1, 3, 6]:
        for new_name, old_name, name in PAIRS:
            v = paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            label = LABELS.get(name, extras.get(name, name))
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines += ['', f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。158项测试、384次成熟训练/损失/叶概率核验和331,200条新预测重建通过。技术通过不等于目标通过。', '',
        '联合训练CRPS只是有限网格近似，最终报告评分为输出离散分布的精确CRPS。树的贪心分裂、有限容量及全局幅度表示仍可能限制效果。本轮是同一历史窗口上的重复探索，不是独立验证；12个月不在本轮双20%验收中。', '',
        '结果解读：联合损失混合版1/3/6个月命中率为53.42%/57.48%/51.06%，相对原B提高2.77%/7.97%/2.07%。6个月相对原分类森林命中率49.65%→51.06%，增加1.41个百分点，配对95%区间为+0.49至+2.36个百分点；三项概率误差点估计相对改善0.61%/0.10%/0.28%，但各自增量区间均跨零。分阶段看，2021–2023三项概率误差均差于原对照，2024年后才改善。1个月三项误差均差于原对照，3个月五档误差也变差。该结果支持继续研究长期方向损失，尚不支持整体替换，也不能把局部方向提升算作双20%达标。', '',
        '明细：[评分前方案](notes/r40_probability_loss_forests.md)、[目标评分](outputs/r40_probability_loss_forests/target_scoreboard.csv)、[配对区间](outputs/r40_probability_loss_forests/paired_comparisons.csv)、[分阶段](outputs/r40_probability_loss_forests/phase_scores.csv)、[完整核验](outputs/r40_probability_loss_forests/research_integrity_audit.json)。', '']
    (EP/'probability_loss_forests_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'}, indent=2))


if __name__ == '__main__': run()
