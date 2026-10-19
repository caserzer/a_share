"""R27 financing-information scoring audit and matched ablation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from build_margin_information import DEST, PANEL, SOURCE as BASE_PANEL, CACHE as FEATURE_CACHE, INDIVIDUAL, MARKET, digest, dates_and_panel
from run_margin_information_models import SOURCE, CACHE, REFERENCE, MODELS
from run_market_time_models import select_training, observation_weights
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import weighted_stats, classes
from report_earnings_revisions import paired_interval, METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE: '自身动量对照', 'individual_margin': '加个股两融',
    'market_margin': '加市场两融', 'both_margin': '同时加两组'}
PAIRS = [(n, REFERENCE, n) for n in MODELS]


def run():
    fa = json.loads((DEST/'feature_audit.json').read_text()); spec = json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert digest(PANEL) == fa['feature_sha256'] == spec['feature_sha256']
    assert digest(BASE_PANEL) == fa['source_sha256']
    assert digest(EP/'notes/r27_margin_information.md') == fa['plan_sha256'] == spec['plan_sha256']
    for r in fa['raw_receipts']:
        receipt = Path(r['path'])
        assert digest(receipt) == r['receipt_sha256']
        assert digest(receipt.with_suffix('').with_suffix('.body')) == r['sha256']
    for r in fa['price_receipts']: assert digest(Path(r['path'])) == r['sha256']
    for name in ['detail', 'market']:
        assert digest(FEATURE_CACHE/f'normalized_{name}.parquet') == fa[f'normalized_{name}_sha256']
    panel = pd.read_parquet(PANEL); original = pd.read_parquet(BASE_PANEL)
    pd.testing.assert_frame_equal(panel[original.columns], original)
    _, dates = dates_and_panel()
    observed = panel.margin_observed.eq(1)
    pd.testing.assert_series_equal(panel.loc[observed, 'snapshot_date'].astype('datetime64[ns]'),
        panel.loc[observed, 'date'].map(dates).astype('datetime64[ns]'), check_names=False)
    assert panel.loc[~observed, [c for c in INDIVIDUAL if c != 'margin_observed']].isna().all().all()
    detail = pd.read_parquet(FEATURE_CACHE/'normalized_detail.parquet')
    market = pd.read_parquet(FEATURE_CACHE/'normalized_market.parquet').sort_values('date')
    check = panel[['date','instrument','total_market_cap_cny']].merge(detail, on=['date','instrument'], how='left', validate='one_to_one')
    cap = check.total_market_cap_cny.where(check.total_market_cap_cny.gt(0))
    np.testing.assert_array_equal(panel.margin_observed, check.financing.notna().astype(float))
    np.testing.assert_allclose(panel.margin_financing_cap, check.financing/cap, equal_nan=True)
    np.testing.assert_allclose(panel.margin_buy_balance, check.buy/check.financing.where(check.financing.gt(0)), equal_nan=True)
    previous = dict(zip(list(dates)[1:], list(dates)[:-1]))
    lookup = detail.set_index(['date','instrument']).financing
    prior = lookup.reindex(pd.MultiIndex.from_arrays([check.date.map(previous), check.instrument])).to_numpy()
    np.testing.assert_allclose(panel.margin_financing_change_cap, (check.financing-prior)/cap, equal_nan=True)
    lending = check.lending_value.copy()
    price_files = {Path(r['path']).stem:Path(r['path']) for r in fa['price_receipts']}
    for instrument, group in check[check.instrument.str.startswith('SH')].groupby('instrument'):
        if instrument not in price_files:
            continue
        raw_price = pd.read_csv(price_files[instrument], usecols=['date','close'])
        prices = pd.Series(raw_price.close.to_numpy(), index=pd.to_datetime(raw_price.date))
        value = group.lending_quantity*group.snapshot_date.map(prices)
        lending.loc[group.index] = value.mask(group.lending_quantity.eq(0), 0)
    np.testing.assert_allclose(panel.margin_lending_cap, lending/cap, equal_nan=True)
    expected_market = pd.DataFrame({'date':market.date,
        MARKET[0]:np.log(market.financing/market.financing.shift(1)),
        MARKET[1]:market.buy/market.financing,
        MARKET[2]:market.lending_value/(market.financing+market.lending_value)})
    expected_market = panel[['date']].merge(expected_market, on='date', how='left', validate='many_to_one')
    np.testing.assert_allclose(panel[MARKET], expected_market[MARKET], equal_nan=True)
    fit = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit) == 576 and not fit.duplicated(['months', 'date', 'model']).any()
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
        old = pd.read_parquet(oldpath); old = old[old.model.eq('own_momentum_control')].assign(model=REFERENCE)
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
                with np.load(OUT/f'local_cache/r25_class_distributions/{h}_{date.date()}_own_momentum_control.npz') as payload:
                    np.testing.assert_array_equal(atoms, payload['class_atoms'])
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
    score = pd.read_csv(DEST/'target_scoreboard.csv'); assert len(score) == 48
    new = score[score.model.isin(MODELS)]; assert len(new) == 36
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=3,
        original_stock_dates_per_model=27600, all_original_features_and_labels_unchanged=True,
        all_training_maturity_checked=True, training_rows_and_class_atoms_matched=True,
        all_new_prediction_rows_reconstructed=reconstructed, feature_integrity_sha256=digest(DEST/'feature_audit.json'),
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '有历史点估计达标候选，仍需完整验证审核，不能直接宣布完成。'
    coverage = panel[panel.date.ge('2021-01-01')].margin_observed.mean()
    lines = ['# R27：融资融券公开信息的消融', '', f'**{result}** 本轮3个新候选及1个冻结对照；累计70个候选。原B、27,600股票月、1/3/6个月四项20%门槛不变。', '',
        f'读取{fa["origins"]}个月末对应的交易所历史快照，均滞后两个交易日。测试样本个股明细覆盖{coverage:.2%}，缺失仍参与原样本预测。深交所个股使用精确Excel，展示网页只核验日期、条数及数值；两市汇总的深市部分保留公开展示精度。', '',
        '同一38项输入对照，分别加入5项个股两融、3项市场两融或两组。相同成熟训练行、月份权重、七分类参数及50%原B混合。信用利差、PE分位和前瞻代理仍在既有输入中。', '',
        '| 期限 | 模型 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 | 实际命中率 |', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            v = score[score.months.eq(h) & score.model.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{v.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+f' | {v.loc["accuracy", "value"]:.2%} |')
    lines += ['', '相对同一自身动量对照的增量：', '',
        '| 期限 | 新增信息 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |', '|---|---|---|---|---|---|']
    paired = pd.DataFrame(pairs)
    for h in [1,3,6]:
        for name in MODELS:
            v = paired[paired.months.eq(h) & paired.comparison.eq(name)].set_index('metric')
            lines.append(f'| {h}个月 | {LABELS[name]} | '+' | '.join(f'{v.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+' |')
    lines += ['', '正值为改善，负值为变差。主表相对原B，增量表相对同参数对照，不能互相替换。误差改善20%与命中率相对改善20%必须由一个模型在三个期限全部满足。', '',
        '已核验全部原字段/标签、所有原始文件哈希、快照滞后、缺失处理、训练标签成熟日期、原参考不变及全部新增预测的概率与评分重建。技术核验不代表预测有效。公开历史数据未证明原始版本，较早记录可能后续更正；两融明细不是市场全量融资，缺席不等于余额零。仍为反复历史探索，12个月双20%未验证。', '',
        '明细：[事前方案](notes/r27_margin_information.md)、[目标评分](outputs/r27_margin_information/target_scoreboard.csv)、[配对消融](outputs/r27_margin_information/paired_comparisons.csv)、[分阶段](outputs/r27_margin_information/phase_scores.csv)、[概率校准](outputs/r27_margin_information/calibration_summary.csv)、[方向诊断](outputs/r27_margin_information/direction_diagnostics.csv)、[特征核验](outputs/r27_margin_information/feature_audit.json)、[预测核验](outputs/r27_margin_information/research_integrity_audit.json)。', '']
    (EP/'margin_information_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
