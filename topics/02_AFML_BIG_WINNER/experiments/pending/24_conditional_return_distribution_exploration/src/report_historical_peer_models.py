"""R25 original-population scoring audit and own-momentum matched ablation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from build_historical_peers import DEST, PANEL, BASE_PANEL, MEMBERS_PANEL, MEMBERSHIPS, EVENTS
from run_historical_peer_models import SOURCE, CACHE, REFERENCE, MODELS
from run_market_time_models import select_training, observation_weights
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import weighted_stats, classes
from report_earnings_revisions import paired_interval, METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE: 'R23成交均值参考', 'own_momentum_control': '自身动量对照',
    'current_linked_peers': '加当日形成关系', 'lagged_linked_peers': '加提前63日形成关系',
    'both_linked_peers': '两种关系同时加入'}
PAIRS = [('own_momentum_control', REFERENCE, 'own_momentum'),
    ('current_linked_peers', 'own_momentum_control', 'current_peers'),
    ('lagged_linked_peers', 'own_momentum_control', 'lagged_peers'),
    ('both_linked_peers', 'own_momentum_control', 'both_peers'),
    ('lagged_linked_peers', 'current_linked_peers', 'earlier_formation')]


def run():
    fa = json.loads((DEST/'feature_audit.json').read_text()); spec = json.loads((DEST/'spec.json').read_text())
    fi = json.loads((DEST/'feature_integrity_audit.json').read_text())
    assert fi['technical_feature_integrity_passed']
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == fa['feature_sha256'] == fi['feature_sha256'] == spec['feature_sha256']
    for path, key in [(BASE_PANEL, 'base_sha256'), (MEMBERS_PANEL, 'members_sha256'),
                      (MEMBERSHIPS, 'membership_cache_sha256'), (EVENTS, 'events_sha256'),
                      (EP/'notes/r25_historical_peers.md', 'plan_sha256')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == fa[key]
    panel = pd.read_parquet(PANEL); original = pd.read_parquet(BASE_PANEL)
    pd.testing.assert_frame_equal(panel[original.columns], original)
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 768 and not fit.duplicated(['months', 'date', 'model']).any()
    assert set(fit.model) == set(MODELS)
    assert fit.groupby(['months', 'date'])[['training_rows', 'training_months', 'last_training_label', 'test_rows', 'adjusted_rows']].nunique().eq(1).all().all()
    for (h, date), group in fit.groupby(['months', 'date']):
        date = pd.Timestamp(date); train = select_training(panel, h, date, None); r = group.iloc[0]
        assert len(train) == r.training_rows and train.date.nunique() == r.training_months
        assert train[f'end_{h}'].max() == pd.Timestamp(r.last_training_label) < date
        np.testing.assert_allclose(group.total_weight, observation_weights(train, date, True, None).sum())
    contract = json.loads((TARGET/'target_contract.json').read_text())
    receipts = []; reconstructed = 0; diagnostic = []; reliability = []; calibration = []
    keys = ['date', 'instrument']
    for item in contract['files']:
        h = item['months']; bpath = Path(item['path'])
        assert hashlib.sha256(bpath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(bpath); base = base[base.model.eq('B')]
        oldpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(oldpath.read_bytes()).hexdigest() == receipt['sha256']
        old = pd.read_parquet(oldpath); old = old[old.model.eq('activity_means_control')].assign(model=REFERENCE)
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        pd.testing.assert_frame_equal(data[data.model.eq(REFERENCE)].reset_index(drop=True), old.reset_index(drop=True))
        for name, group in data.groupby('model'):
            joined = group.merge(base[keys+['actual', 'label_end', 'target_date']], on=keys, suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
            for c in ['label_end', 'target_date']: pd.testing.assert_series_equal(joined[c], joined[c+'_base'], check_names=False)
        for date, dated in data.groupby('date'):
            saved_keys = pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', saved_keys)
            shared = None
            for name in MODELS:
                group = dated[dated.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(group[keys], saved_keys)
                active = fit[fit.months.eq(h) & fit.date.eq(str(date.date())) & fit.model.eq(name)].adjusted_rows.iloc[0]
                if not active:
                    pd.testing.assert_frame_equal(group, base[base.date.eq(date)].assign(model=name).reset_index(drop=True))
                    continue
                with np.load(CACHE/f'{h}_{date.date()}_{name}.npz') as payload:
                    atoms, p = payload['class_atoms'], payload['probabilities']
                assert np.isfinite(atoms).all() and (np.diff(atoms)>=0).all()
                np.testing.assert_array_equal(classes(atoms), np.repeat(np.arange(7), 32))
                if shared is not None: np.testing.assert_array_equal(atoms, shared)
                shared = atoms
                assert np.isfinite(p).all() and (p >= 0).all()
                np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-10)
                a, w = combine_distributions([(ba, bw), (np.tile(atoms, (len(p), 1)), np.repeat(p/32, 32, axis=1))], [.5, .5])
                expected = weighted_stats(a, w, group.actual)
                np.testing.assert_allclose(group[expected.columns], expected, atol=1e-12, rtol=1e-12, equal_nan=True)
                reconstructed += len(group)
        for name, group in pd.concat([data, base]).groupby('model'):
            cells, summary = probability_reliability(group)
            reliability.append(cells.assign(months=h, model=name)); calibration.append(dict(months=h, model=name, **summary))
        for (name, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostic.append(dict(months=h, date=date, model=name,
                accuracy=((group.p_up > group.p_down) == y).mean(), up_call_rate=(group.p_up > group.p_down).mean(),
                always_down=(~y).mean(), within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
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
        original_stock_dates_per_model=27600, all_original_features_and_labels_unchanged=True,
        all_training_maturity_checked=True, training_rows_and_class_atoms_matched=True,
        all_new_prediction_rows_reconstructed=reconstructed, feature_integrity_sha256=hashlib.sha256((DEST/'feature_integrity_audit.json').read_bytes()).hexdigest(),
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需完整验证审核，不能直接宣布完成。'
    lines = ['# R25：历史联动股票信息的匹配消融', '', f'**{result}** 本轮4个新候选和1个原样参考。固定原B、27,600股票月与1/3/6月四项20%门槛。', '',
        f'构建{fa["historical_months"]}个月、{fa["historical_member_stocks"]}只历史股票的已知行情关系。原测试人群中窗口0/63至少10只联动股票的覆盖为{fa["test_available_by_gap"]["0"]/27600:.2%}/{fa["test_available_by_gap"]["63"]/27600:.2%}。没有关系的股票继续预测，不以缺失数据删除样本。', '',
        '先在原浅层成交均值模型中加入个股自身21/63/126日动量，作为匹配对照；再分别加入两种形成窗口的联动股票近期动量、相关度、数量与可用标记。窗口63的关系形成结束于最近63个交易日之前，近期动量仍取决策日已知值。所有模型同训练行、同月份权重、同类别内分布，与B各50%。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 | 实际命中率 |', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            v = score[score.months.eq(h) & score.model.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{v.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+f' | {v.loc["accuracy", "value"]:.2%} |')
    direction = score[score.months.eq(1) & score.metric.eq('accuracy')].set_index('model').value
    lines += ['', f'1个月当日联动版本命中率为{direction.current_linked_peers:.2%}，相对自身动量对照变动{100*(direction.current_linked_peers-direction.own_momentum_control):+.2f}个百分点；相对原样保留的R23参考仅变动{100*(direction.current_linked_peers-direction[REFERENCE]):+.2f}个百分点。因此需同时看匹配对照和原参考，不能把对照变弱后的恢复幅度全部当作新增优势。', '',
        '相对自身动量对照的6个月概率误差增量：', '',
        '| 新增输入 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 |', '|---|---|---|---|']
    paired = pd.DataFrame(pairs)
    for name, label in [('current_peers', '当日形成关系'), ('lagged_peers', '提前63日形成关系')]:
        v = paired[paired.months.eq(6) & paired.comparison.eq(name)].set_index('metric')
        lines.append(f'| {label} | '+' | '.join(f'{v.loc[m, "relative_improvement"]:+.2%}' for m in METRICS[:3])+' |')
    lines += ['', '正数表示改善，负数表示变差。相似走势关系不是官方行业，也不是预测有效的证据。单独比较相似股票版本与自身动量对照，才能评估额外股票信息的增量；配对月份块区间和分阶段结果另报，不拼接不同模型的最好指标。', '',
        '核验所有原字段/标签、成员和窗口时点、排除自身、真实历史前缀重建、同人群/训练行/类别原子、原参考不变以及全部新预测的概率和评分缓存重建。此类技术核验不构成有效性证明。仍为反复历史探索，股票池和价格修订偏差保留，12个月双20%未验证。', '',
        '明细：[事前方案](notes/r25_historical_peers.md)、[目标评分](outputs/r25_historical_peers/target_scoreboard.csv)、[配对消融](outputs/r25_historical_peers/paired_comparisons.csv)、[分阶段](outputs/r25_historical_peers/phase_scores.csv)、[概率校准](outputs/r25_historical_peers/calibration_summary.csv)、[方向诊断](outputs/r25_historical_peers/direction_diagnostics.csv)、[特征核验](outputs/r25_historical_peers/feature_integrity_audit.json)、[预测核验](outputs/r25_historical_peers/research_integrity_audit.json)。', '']
    (EP/'historical_peer_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
