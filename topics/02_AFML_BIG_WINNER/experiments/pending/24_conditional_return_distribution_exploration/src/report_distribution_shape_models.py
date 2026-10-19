"""R24 complete-population audit and matched distribution-shape comparisons."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT, DATA
from run_distribution_shape_models import DEST, CACHE, PANEL, SOURCE, FITS, MODELS, REFERENCES, ALPHAS, GRID, risk_scale, training_target, quantile_atoms
from run_market_time_models import select_training, observation_weights
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import weighted_stats
from report_earnings_revisions import paired_interval, METRICS
from diagnose_prediction_target import DEST as TARGET

LABELS = {'r23_class_control': '多类别对照（原样参考）', 'r23_class_paths': '多类别加路径（原样参考）',
    'quantile_control_mixed': '分位数、混合', 'quantile_control_unmixed': '分位数、独立',
    'quantile_scaled_mixed': '风险标准化、混合', 'quantile_scaled_unmixed': '风险标准化、独立',
    'quantile_paths_mixed': '分位数加路径、混合', 'quantile_paths_unmixed': '分位数加路径、独立'}
PAIRS = [('quantile_control_mixed', 'r23_class_control', 'quantile_vs_class_control'),
    ('quantile_paths_mixed', 'r23_class_paths', 'quantile_vs_class_paths'),
    ('quantile_scaled_mixed', 'quantile_control_mixed', 'risk_scaling_mixed'),
    ('quantile_paths_mixed', 'quantile_control_mixed', 'path_features_mixed'),
    ('quantile_scaled_unmixed', 'quantile_control_unmixed', 'risk_scaling_unmixed'),
    ('quantile_paths_unmixed', 'quantile_control_unmixed', 'path_features_unmixed'),
    *[(f'{name}_unmixed', f'{name}_mixed', f'remove_blend_{name}') for name in FITS]]


def probability_reliability(frame):
    """Fixed-bin descriptive reliability; total weight is equal per origin month."""
    g = frame[frame.actual.notna()].copy()
    if g.empty:
        raise ValueError('Observed outcomes are required for reliability diagnostics')
    if not np.isfinite(g.p_up).all() or not g.p_up.between(-1e-10, 1+1e-10).all():
        raise ValueError('Invalid probability')
    g['weight'] = 1/g.groupby('date').date.transform('size')
    g['bucket'] = np.floor(g.p_up.clip(0, 1)*10).clip(upper=9).astype(int)
    total = g.weight.sum(); rows = []
    for bucket, group in g.groupby('bucket'):
        mass = group.weight.sum()
        predicted = np.average(group.p_up, weights=group.weight)
        observed = np.average(group.actual.gt(0), weights=group.weight)
        rows.append(dict(bucket=int(bucket), probability_lower=bucket/10, probability_upper=(bucket+1)/10,
            stock_dates=len(group), origin_months=group.date.nunique(), population_weight=mass/total,
            predicted=float(predicted), observed=float(observed), observed_minus_predicted=float(observed-predicted)))
    cells = pd.DataFrame(rows)
    return cells, dict(observed_rows=len(g), origin_months=g.date.nunique(),
        bin_ece=float((cells.population_weight*cells.observed_minus_predicted.abs()).sum()),
        mean_predicted=float(np.average(g.p_up, weights=g.weight)),
        mean_observed=float(np.average(g.actual.gt(0), weights=g.weight)))


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert hashlib.sha256(PANEL.read_bytes()).hexdigest() == spec['feature_sha256']
    assert hashlib.sha256((EP/'notes/r24_distribution_shape.md').read_bytes()).hexdigest() == spec['note_sha256']
    np.testing.assert_array_equal(spec['alphas'], ALPHAS)
    np.testing.assert_array_equal(spec['grid'], GRID)
    panel = pd.read_parquet(PANEL); keys = ['date', 'instrument']
    calendar = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt', header=None)[0]))
    unit_checks = []
    for stock in ['SH600004', 'SZ000001', 'SZ300001']:
        row = panel[panel.instrument.eq(stock) & panel.date.ge('2021-01-01')].sort_values('date').iloc[0]
        path = DATA/f'raw/akshare/day/qfq/{stock}.csv'
        bars = pd.read_csv(path, parse_dates=['date']).set_index('date').reindex(calendar[calendar <= row.date])
        daily = bars.close.where(bars.close.gt(0)).pct_change(fill_method=None).tail(63)
        assert daily.notna().all()
        np.testing.assert_allclose(row.vol63, daily.std()*np.sqrt(252), rtol=1e-10)
        for h in [1, 3, 6]:
            np.testing.assert_allclose(risk_scale([row.vol63], h), [daily.std()*np.sqrt(21*h)], rtol=1e-10)
        unit_checks.append(dict(instrument=stock, date=str(row.date.date()), annual_vol63=float(row.vol63),
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 576 and not fit.duplicated(['months', 'date', 'fit']).any()
    assert set(fit.fit) == set(FITS)
    reused = fit[fit.reused_unscaled_cache]
    if spec['reuse_manifest_sha256'] is not None:
        path = DEST/'cache_reuse_manifest.json'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec['reuse_manifest_sha256']
        reuse = json.loads(path.read_text())
        assert len(reused) == len(reuse['reusable'])
        assert not reused.fit.eq('quantile_scaled').any()
        for item in reuse['reusable']:
            assert hashlib.sha256((CACHE/Path(item['path']).name).read_bytes()).hexdigest() == item['sha256']
            assert hashlib.sha256((CACHE/Path(item['keys_path']).name).read_bytes()).hexdigest() == item['keys_sha256']
    assert fit.groupby(['months', 'date'])[['training_rows', 'training_months', 'last_training_label', 'test_rows', 'adjusted_rows']].nunique().eq(1).all().all()
    for (h, date), g in fit.groupby(['months', 'date']):
        date = pd.Timestamp(date); train = select_training(panel, h, date, None); r = g.iloc[0]
        assert len(train) == r.training_rows and train.date.nunique() == r.training_months
        assert train[f'end_{h}'].max() == pd.Timestamp(r.last_training_label) < date
        np.testing.assert_allclose(g.total_weight, observation_weights(train, date, True, None).sum())
        training_target(train[f'y_{h}'], risk_scale(train.vol63, h))
    contract = json.loads((TARGET/'target_contract.json').read_text())
    receipts = []; diagnostic = []; tails = []; reconstructed = 0; reliability = []; calibration = []
    pcols = ['p_up', 'p_down', 'p_zero', 'p_loss_over20', 'p_loss5_20', 'p_near_flat', 'p_gain5_20', 'p_gain_over20']
    for item in contract['files']:
        h = item['months']; basepath = Path(item['path'])
        assert hashlib.sha256(basepath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(basepath); base = base[base.model.eq('B')]
        oldpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(oldpath.read_bytes()).hexdigest() == receipt['sha256']
        old = pd.read_parquet(oldpath)
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        for name, previous in REFERENCES.items():
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True), old[old.model.eq(previous)].assign(model=name).reset_index(drop=True))
        for name, group in data.groupby('model'):
            joined = group.merge(base[keys+['actual', 'label_end', 'target_date']], on=keys, suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
            for c in ['label_end', 'target_date']:
                pd.testing.assert_series_equal(joined[c], joined[c+'_base'], check_names=False)
        for date, dated in data.groupby('date'):
            saved_keys = pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            test = saved_keys.merge(panel, on=keys, validate='one_to_one')
            assert len(test) == len(saved_keys)
            ba, bw = load_distribution(OUT/'local_cache/r15_distributions', h, date, 'B', saved_keys)
            for name, (_, scaled) in FITS.items():
                active = fit[fit.months.eq(h) & fit.date.eq(str(date.date())) & fit.fit.eq(name)].adjusted_rows.iloc[0]
                if active:
                    with np.load(CACHE/f'{h}_{date.date()}_{name}.npz') as payload:
                        raw, scale = payload['raw_quantiles'], payload['query_scale']
                    np.testing.assert_array_equal(scale, risk_scale(test.vol63, h) if scaled else np.ones(len(test)))
                    a, w = quantile_atoms(raw, scale if scaled else None)
                    assert (a >= -1).all() and np.isfinite(a).all()
                    r = fit[fit.months.eq(h) & fit.date.eq(str(date.date())) & fit.fit.eq(name)].iloc[0]
                    np.testing.assert_allclose(r.crossing_fraction, (np.diff(raw, axis=1)<0).any(axis=1).mean())
                    y = dated[dated.model.eq(f'{name}_unmixed')].actual.to_numpy()
                    observed = np.isfinite(y)
                    tails.append(dict(months=h, date=date, fit=name, observed=int(observed.sum()),
                        below_min=float((y[observed]<a[observed, 0]).mean()) if observed.any() else np.nan,
                        above_max=float((y[observed]>a[observed, -1]).mean()) if observed.any() else np.nan))
                for suffix, fraction in [('mixed', .5), ('unmixed', 1.)]:
                    model_name = f'{name}_{suffix}'; group = dated[dated.model.eq(model_name)].reset_index(drop=True)
                    pd.testing.assert_frame_equal(group[keys], saved_keys)
                    if not active:
                        pd.testing.assert_frame_equal(group, base[base.date.eq(date)].assign(model=model_name).reset_index(drop=True))
                        continue
                    aa, ww = combine_distributions([(ba, bw), (a, w)], [1-fraction, fraction]) if fraction < 1 else (a, w)
                    expected = weighted_stats(aa, ww, group.actual)
                    np.testing.assert_allclose(group[expected.columns], expected, atol=1e-12, rtol=1e-12, equal_nan=True)
                    reconstructed += len(group)
        assert np.isfinite(data[pcols]).all().all() and data[pcols].ge(0).all().all()
        np.testing.assert_allclose(data[pcols[:3]].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[pcols[3:]].sum(axis=1), 1, atol=1e-10)
        for name, group in pd.concat([data, base]).groupby('model'):
            cells, summary = probability_reliability(group)
            reliability.append(cells.assign(months=h, model=name))
            interval = group[group.actual.notna()].groupby('date')[['coverage90', 'below_q05']].mean().mean()
            calibration.append(dict(months=h, model=name, **summary, coverage90=interval.coverage90, below_q05=interval.below_q05))
        for (name, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostic.append(dict(months=h, date=date, model=name,
                accuracy=((group.p_up > group.p_down) == y).mean(), up_call_rate=(group.p_up > group.p_down).mean(),
                always_down=(~y).mean(), within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(diagnostic).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.DataFrame(tails).to_csv(DEST/'endpoint_tail_diagnostics.csv', index=False)
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
    score = pd.read_csv(DEST/'target_scoreboard.csv'); assert len(score) == 96
    new = score[score.model.isin(MODELS)]; assert len(new) == 72
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=6,
        original_population_per_model=27600, all_labels_and_target_dates_unchanged=True, training_maturity_verified=True,
        prior_references_unchanged=True, all_quantile_scales_verified=True, prediction_rows_fully_reconstructed=reconstructed,
        annual_volatility_units_verified_from_prices=unit_checks, reused_unscaled_fits=len(reused),
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需验证审核，不能直接宣布完成。'
    lines = ['# R24：分位数分布与风险标准化', '', f'**{result}** 本轮6个新候选、2个原样参考。冻结B、27,600股票月、1/3/6月四项20%门槛均保持不变。', '',
        '直接估计25个分位点并重建一致的200原子概率分布。三组拟合分别使用R23对照输入、相同输入并按已知历史波动率标准化对数标签、对照输入追加量价路径；分别报告独立分布和与B各50%混合。输出仍是上涨/下跌和涨跌幅区间概率。', '',
        'R10曾检验季度重训、旧输入下的分位数树并发现过度自信。本轮检验新增信息集与月份等权条件下的表现，不把旧方法称为首次提出。深度/树数与两个R23参考相同，损失和参数维度不同。详见[事前方案](notes/r24_distribution_shape.md)及[CatBoost目标说明](https://catboost.ai/docs/en/concepts/loss-functions-regression)。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 | 实际命中率 |', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            values = score[score.months.eq(h) & score.model.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+f' | {values.loc["accuracy", "value"]:.2%} |')
    coverage = pd.DataFrame(calibration).set_index(['months', 'model'])
    lines += ['', '名义90%预测区间的实际覆盖率（月份等权）：', '',
        '| 期限 | 原B | 独立直接分位数 | 风险标准化、混合 |', '|---|---|---|---|']
    for h in [1, 3, 6]:
        lines.append(f'| {h}个月 | '+' | '.join(f'{coverage.loc[(h, name), "coverage90"]:.2%}' for name in ['B', 'quantile_control_unmixed', 'quantile_scaled_mixed'])+' |')
    lines += ['', '正数是改善、负数是变差。不能拼接不同模型的最好指标。方向规则继续使用上涨概率大于下跌概率；确切零收益只在方向命中率中排除。', '',
        '另用固定10个百分点概率组比较预测概率与实际上涨频率，各起点月份总权重相同。分组校准误差ECE仅作描述，不替代原Brier/CRPS门槛，也不构成可信度证明。名义90%区间的实际覆盖率以及最小/最大预测原子之外的频率单独报告。', '',
        '技术核验涵盖全部源/方案哈希、原参考逐值不变、同人群/标签/目标日期、每次训练已成熟标签，以及所有新预测从原始分位点和当时风险尺度重建后的概率、CRPS和其他评分。技术通过不代表有效提升。', '',
        '首次运行在评分前发现年化波动率的期限换算错误，已停止、纠正并隔离44个受影响缓存；89个不涉及风险标准化的拟合经输入、参数、键和文件哈希核验后复用。最终另从三只股票原始日线核对年化单位和各期限尺度，旧错误版本不进入成绩或候选数。', '',
        '25分位点的两端采取常值延展，因此无法识别最极端2%的真实形状；端点之外的实际频率单独报告。排序处理分位点交叉不保证校准。风险标准化改变损失权重，未使用未来波动率。仍是同一历史窗口反复探索，原股票池偏差和历史版本问题尚未解决，12月双20%未验证。', '',
        '明细：[目标评分](outputs/r24_distribution_shape/target_scoreboard.csv)、[匹配比较](outputs/r24_distribution_shape/paired_comparisons.csv)、[分阶段](outputs/r24_distribution_shape/phase_scores.csv)、[方向诊断](outputs/r24_distribution_shape/direction_diagnostics.csv)、[概率分组](outputs/r24_distribution_shape/probability_reliability.csv)、[校准及区间覆盖](outputs/r24_distribution_shape/calibration_summary.csv)、[尾端诊断](outputs/r24_distribution_shape/endpoint_tail_diagnostics.csv)、[技术核验](outputs/r24_distribution_shape/research_integrity_audit.json)。', '']
    (EP/'distribution_shape_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
