"""R23 feature-prefix, matched-population and probability reconstruction audit."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import DATA, EP, OUT
from build_price_volume_features import DEST, PANEL, ACTIVITY, PATH, EVENTS, daily_features
from run_price_volume_models import SOURCE, CACHE, REFERENCE, MODELS
from run_market_time_models import load_panel, select_training, observation_weights
from run_prequential_search import load_distribution
from run_direct_probability import classes
from report_market_time_models import event_probabilities
from report_earnings_revisions import paired_interval, METRICS
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE: 'R21月份等权参考', 'activity_means_control': '已有成交均值对照',
    'activity_interactions': '量价交互', 'intraday_paths': '价格路径', 'activity_and_paths': '量价加路径',
    'activity_means_depth4': '较大模型、均值对照', 'activity_and_paths_depth4': '较大模型、量价加路径'}
PAIRS = [('activity_means_control', REFERENCE, 'existing_activity_means'),
    ('activity_interactions', 'activity_means_control', 'activity_signal'),
    ('intraday_paths', 'activity_means_control', 'path_signal'),
    ('activity_and_paths', 'activity_means_control', 'combined_signal'),
    ('activity_means_depth4', 'activity_means_control', 'capacity_control'),
    ('activity_and_paths_depth4', 'activity_means_depth4', 'combined_signal_depth4'),
    ('activity_and_paths_depth4', 'activity_and_paths', 'capacity_combined')]


def run():
    fa = json.loads((DEST/'feature_audit.json').read_text()); spec = json.loads((DEST/'spec.json').read_text())
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == fa['feature_sha256'] == spec['feature_sha256']
    assert hashlib.sha256(EVENTS.read_bytes()).hexdigest() == fa['events_sha256']
    panel = pd.read_parquet(PANEL); original = load_panel(); keys = ['date', 'instrument']
    pd.testing.assert_frame_equal(panel.sort_values(keys)[original.columns].reset_index(drop=True), original.sort_values(keys).reset_index(drop=True))
    source_receipts = pd.read_csv(DEST/'source_receipts.csv')
    assert len(source_receipts) == 2*fa['stocks'] and not source_receipts.path.duplicated().any()
    for r in source_receipts.itertuples():
        assert hashlib.sha256(Path(r.path).read_bytes()).hexdigest() == r.sha256
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    cutoff = pd.Timestamp('2022-06-30'); past_calendar = calendar[calendar <= cutoff]
    events = pd.read_csv(EVENTS, parse_dates=['date']); prefix_checks = []
    for stock in ['SH600004', 'SZ000001', 'SZ300001']:
        raw = pd.read_csv(DATA/f'raw/akshare/day/raw/{stock}.csv', parse_dates=['date']).set_index('date').loc[:cutoff]
        qfq = pd.read_csv(DATA/f'raw/akshare/day/qfq/{stock}.csv', parse_dates=['date']).set_index('date').loc[:cutoff]
        f, _ = daily_features(raw, qfq, past_calendar, events.loc[events.instrument.eq(stock) & events.date.le(cutoff), 'date'])
        saved = panel[panel.instrument.eq(stock) & panel.date.le(cutoff)]
        assert len(saved) > 0 and saved[ACTIVITY+PATH].notna().any().all(), 'Prefix check needs actual eligible rows and observed features'
        np.testing.assert_allclose(saved[ACTIVITY+PATH], f.reindex(saved.date)[ACTIVITY+PATH], atol=1e-12, equal_nan=True)
        prefix_checks.append(dict(instrument=stock, cutoff=str(cutoff.date()), checked_stock_dates=len(saved)))
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 1152 and not fit.duplicated(['months', 'date', 'model']).any()
    assert fit.groupby(['months', 'date'])[['training_rows', 'training_months', 'last_training_label', 'test_rows', 'adjusted_rows']].nunique().eq(1).all().all()
    for (h, date), g in fit.groupby(['months', 'date']):
        date = pd.Timestamp(date); r = g.iloc[0]; train = select_training(panel, h, date, None)
        assert len(train) == r.training_rows and train.date.nunique() == r.training_months
        assert train[f'end_{h}'].max() == pd.Timestamp(r.last_training_label) < date
        np.testing.assert_allclose(g.total_weight, observation_weights(train, date, True, None).sum())
    contract = json.loads((TARGET/'target_contract.json').read_text()); receipts = []; diagnostic = []
    pcols = ['p_up', 'p_down', 'p_zero', 'p_loss_over20', 'p_loss5_20', 'p_near_flat', 'p_gain5_20', 'p_gain_over20']
    for item in contract['files']:
        h = item['months']; bpath = Path(item['path'])
        assert hashlib.sha256(bpath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(bpath); base = base[base.model.eq('B')]
        oldpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(oldpath.read_bytes()).hexdigest() == receipt['sha256']
        ref = pd.read_parquet(oldpath); ref = ref[ref.model.eq('market_month_balanced')].assign(model=REFERENCE)
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        pd.testing.assert_frame_equal(ref.reset_index(drop=True), data[data.model.eq(REFERENCE)].reset_index(drop=True))
        for name, group in data.groupby('model'):
            joined = group.merge(base[['date', 'instrument', 'actual']], on=keys, suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
        for date, dated in data.groupby('date'):
            saved_keys = pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', saved_keys)
            labels = classes(ba); bp = np.column_stack([(bw*(labels == k)).sum(axis=1) for k in range(7)])
            shared_atoms = None
            for name in MODELS:
                group = dated[dated.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(group[keys], saved_keys)
                active = fit[fit.months.eq(h) & fit.date.eq(str(date.date())) & fit.model.eq(name)].adjusted_rows.iloc[0]
                if not active:
                    pd.testing.assert_frame_equal(group, base[base.date.eq(date)].assign(model=name).reset_index(drop=True))
                    continue
                with np.load(CACHE/f'{h}_{date.date()}_{name}.npz') as payload:
                    p, a = payload['probabilities'], payload['class_atoms']
                np.testing.assert_array_equal(classes(a), np.repeat(np.arange(7), 32))
                assert (np.diff(a) >= 0).all()
                if shared_atoms is not None: np.testing.assert_array_equal(a, shared_atoms)
                shared_atoms = a
                np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-10)
                np.testing.assert_allclose(group[pcols], event_probabilities(.5*bp+.5*p), atol=1e-10)
        assert np.isfinite(data[pcols]).all().all() and data[pcols].ge(0).all().all()
        np.testing.assert_allclose(data[pcols[:3]].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[pcols[3:]].sum(axis=1), 1, atol=1e-10)
        known = data.actual.notna()
        np.testing.assert_allclose(data.loc[known, 'brier'], (data.loc[known, 'p_up']-data.loc[known, 'actual'].gt(0))**2)
        assert data.loc[~known, METRICS[:3]].isna().all().all()
        for (name, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostic.append(dict(months=h, model=name, date=date,
                accuracy=((group.p_up > group.p_down) == y).mean(), up_call_rate=(group.p_up > group.p_down).mean(),
                always_down=(~y).mean(), within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(diagnostic).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
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
    score = pd.read_csv(DEST/'target_scoreboard.csv'); assert len(score) == 84
    new = score[score.model.isin(MODELS)]; decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=6,
        prediction_rows_per_model=27600, all_original_features_and_labels_unchanged=True, same_training_and_class_atoms=True,
        real_source_prefix_checks=prefix_checks, source_files_hashed=len(source_receipts), all_event_probabilities_reconstructed=True,
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需验证审核，不能直接宣布完成。'
    lines = ['# R23：量价交互、价格路径与模型容量', '', f'**{result}** 本轮6个新候选和1个原样保留的R21参考，累计53候选。原27,600股票月、冻结R15 B与1/3/6月四项20%门槛不变。', '',
        f'读取{fa["stocks"]:,}只历史股票的raw/qfq日线，核验{fa["quality_totals"]["raw_rows"]:,}条原价记录；单位或成交均价关系不符的{fa["quality_totals"]["unit_or_vwap_rejected_rows"]:,}条记录不用于相关成交特征。16个新特征每个在测试人群中缺失0—{max(fa["missing_test_rows"].values())}行；所有股票仍参与预测，缺失输入不填成市场数值。', '',
        '8个量价特征涵盖活跃度变化、量价相关、签名成交额、非流动性代理和成交额加权日内收益；8个路径特征涵盖日内/隔夜收益、区间位置、振幅、收益自相关和集中度。只使用当时及此前完整21/63交易日；已知复权异常仅屏蔽依赖该日跨日收益的输入。签名成交额不代表已识别投资者资金流。', '',
        '对照保留原市场/盈利输入及既有换手率、成交额均值。浅层组为深度2/100棵/L2=20；较大模型组为深度4/200棵/L2=50，各自设相同容量的均值对照。所有新模型同样本、同月份权重、同类别内分布，与B各占50%。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            values = score[(score.months == h) & score.model.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+' |')
    lines += ['', '正数是改善，负数是变差。相同容量下的新特征增量、容量变化及相对旧参考的配对比较另报，不能拼接最好指标。', '',
        '下表单独比较两种容量内“加入全部新特征”与“仅保留既有成交均值”，因此基准不同于上表冻结B。区间为按起点月份进行12月块自助法的95%配对区间，方向单位为百分点；未作多次探索校正。', '',
        '| 期限 | 模型容量 | 上涨Brier相对改善 | 五档相对改善 | CRPS相对改善 | 方向相对改善 | 方向绝对改善95%区间 |',
        '|---|---|---|---|---|---|---|']
    paired = pd.DataFrame(pairs)
    for h in [1, 3, 6]:
        for comparison, label in [('combined_signal', '深度2'), ('combined_signal_depth4', '深度4')]:
            values = paired[paired.months.eq(h) & paired.comparison.eq(comparison)].set_index('metric')
            r = values.loc['accuracy']
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+
                f' | [{100*r.improvement_lower95:+.2f}, {100*r.improvement_upper95:+.2f}] |')
    lines += ['', '实际命中率与目标：', '',
        '| 期限 | 原B | 深度2全部新特征 | 深度4全部新特征 | 20%目标 |', '|---|---|---|---|---|']
    for h in [1, 3, 6]:
        values = score[score.months.eq(h) & score.metric.eq('accuracy')].set_index('model')
        b = values.baseline.iloc[0]
        lines.append(f'| {h}个月 | {b:.2%} | {values.loc["activity_and_paths", "value"]:.2%} | {values.loc["activity_and_paths_depth4", "value"]:.2%} | {1.2*b:.2%} |')
    lines += ['',
        '核验全部原字段和标签逐值不变、日线源哈希、真实样例只读截至2022-06-30数据仍重建相同历史特征、各模型训练样本/类别原子完全一致、全部事件概率可重建。这些技术证据不代表预测有效；仍是同一历史区间的多次探索，未解决原股票池偏差或历史数据修订问题，也未验证12个月双20%。', '',
        '明细：[目标评分](outputs/r23_price_volume_features/target_scoreboard.csv)、[配对消融](outputs/r23_price_volume_features/paired_comparisons.csv)、[阶段表现](outputs/r23_price_volume_features/phase_scores.csv)、[方向诊断](outputs/r23_price_volume_features/direction_diagnostics.csv)、[数据质量](outputs/r23_price_volume_features/daily_quality.csv)、[特征覆盖](outputs/r23_price_volume_features/feature_coverage.csv)、[技术核验](outputs/r23_price_volume_features/research_integrity_audit.json)。', '']
    (EP/'price_volume_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
