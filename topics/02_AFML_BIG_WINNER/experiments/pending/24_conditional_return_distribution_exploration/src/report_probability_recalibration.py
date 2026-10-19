"""R22 audit of temporal calibration boundaries, reconstruction and goal scores."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from run_probability_recalibration import DEST, SOURCE, STREAMS, REFERENCE, CALIBRATORS, MIXTURES, MIN_MONTHS, source_distributions
from probability_recalibration import calibration_history, class_probabilities, transform
from run_direct_probability import classes
from report_earnings_revisions import METRICS, paired_interval
from diagnose_prediction_target import DEST as TARGET

LABELS = dict(r21_month_reference='R21月份等权参考', r21_decay_reference='R21衰减不混合参考',
    month_calibration_expanding='月份等权源、扩展校准', month_calibration_recent24='月份等权源、24月校准',
    decay_calibration_expanding='衰减源、扩展校准', decay_calibration_recent24='衰减源、24月校准',
    uniform_frozen_mix='三源固定平均', learned_frozen_mix='三源预序列学习组合')
PAIRS = [(name, REFERENCE[source], name) for name, (source, _) in CALIBRATORS.items()] + [
    ('month_calibration_recent24', 'month_calibration_expanding', 'month_recent_vs_expanding'),
    ('decay_calibration_recent24', 'decay_calibration_expanding', 'decay_recent_vs_expanding'),
    ('learned_frozen_mix', 'uniform_frozen_mix', 'learned_vs_uniform')]


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    fit = pd.read_csv(DEST/'fit_audit.csv'); params = pd.read_csv(DEST/'calibration_parameters.csv')
    mixtures = pd.read_csv(DEST/'mixture_weights.csv')
    assert len(fit) == 1152 and not fit.duplicated(['months', 'date', 'model']).any()
    assert len(mixtures) == 384 and not mixtures.duplicated(['months', 'date', 'model']).any()
    active_cal = fit[fit.model.isin(CALIBRATORS) & fit.active]
    assert set(map(tuple, active_cal[['months', 'date', 'model']].to_numpy())) == set(map(tuple, params[['months', 'date', 'model']].to_numpy()))
    assert len(active_cal) == len(params) and not params.duplicated(['months', 'date', 'model']).any()
    assert params.scale.between(.25, 4).all() and params[[f'intercept_{k}' for k in range(7)]].abs().le(2+1e-12).all().all()
    assert (params.penalized_loss <= params.identity_penalized_loss+1e-8).all()
    np.testing.assert_allclose(mixtures[['B', 'month', 'decay']].sum(axis=1), 1, atol=1e-10)
    assert mixtures[['B', 'month', 'decay']].ge(0).all().all()
    caches = pd.read_csv(DEST/'input_cache_receipts.csv')
    for row in caches.itertuples():
        assert hashlib.sha256(Path(row.path).read_bytes()).hexdigest() == row.sha256
    contract = json.loads((TARGET/'target_contract.json').read_text()); receipts = []; diagnostics = []
    for item in contract['files']:
        h = item['months']; basepath = Path(item['path'])
        assert hashlib.sha256(basepath.read_bytes()).hexdigest() == item['sha256']
        base = pd.read_parquet(basepath); base = base[base.model.eq('B')]
        oldpath = SOURCE/f'predictions_{h}m.parquet'
        receipt = next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert hashlib.sha256(oldpath.read_bytes()).hexdigest() == receipt['sha256']
        old = pd.read_parquet(oldpath)
        originals = {key: old[old.model.eq(model)].copy() for key, model in STREAMS.items()}
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        for stream, reference in REFERENCE.items():
            pd.testing.assert_frame_equal(originals[stream].assign(model=reference).reset_index(drop=True), data[data.model.eq(reference)].reset_index(drop=True))
        for name, group in data.groupby('model'):
            joined = group.merge(base[['date', 'instrument', 'actual']], on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(joined) == len(group) == 27600
            np.testing.assert_allclose(joined.actual, joined.actual_base, equal_nan=True)
        for row in fit[fit.months.eq(h)].itertuples():
            date = pd.Timestamp(row.date)
            if row.model == 'uniform_frozen_mix':
                assert row.active and row.history_rows == row.history_months == 0
                continue
            window = CALIBRATORS[row.model][1] if row.model in CALIBRATORS else 24
            history = calibration_history(base, date, window)
            assert len(history) == row.history_rows and history.date.nunique() == row.history_months
            assert bool(row.active) == (history.date.nunique() >= MIN_MONTHS)
            if len(history):
                assert history.label_end.max() == pd.Timestamp(row.latest_history_label) < date
                assert history.date.min() == pd.Timestamp(row.first_origin)
            else:
                assert pd.isna(pd.to_datetime(row.latest_history_label))
            if not row.active:
                reference = originals[CALIBRATORS[row.model][0]] if row.model in CALIBRATORS else base
                expected = reference[reference.date.eq(date)].assign(model=row.model).reset_index(drop=True)
                actual = data[data.model.eq(row.model) & data.date.eq(date)].reset_index(drop=True)
                pd.testing.assert_frame_equal(expected, actual)
        for date, dated in data.groupby('date'):
            base_now = base[base.date.eq(date)].reset_index(drop=True)
            keys = base_now[['date', 'instrument']]
            distributions, _, _ = source_distributions(h, date, keys)
            ba, bw = distributions['B']; bclass = classes(ba)
            probabilities = dict(B=np.column_stack([(bw*(bclass == k)).sum(axis=1) for k in range(7)]))
            probabilities.update({key: class_probabilities(value[value.date.eq(date)]) for key, value in originals.items()})
            for name, (stream, _) in CALIBRATORS.items():
                pars = params[params.months.eq(h) & params.date.eq(str(date.date())) & params.model.eq(name)]
                if pars.empty: continue
                values = pars[['scale']+[f'intercept_{k}' for k in range(7)]].iloc[0].to_numpy()
                expected = transform(probabilities[stream], values)
                actual = class_probabilities(dated[dated.model.eq(name)])
                np.testing.assert_allclose(actual, expected, atol=1e-10)
            for name in MIXTURES:
                weights = mixtures[mixtures.months.eq(h) & mixtures.date.eq(str(date.date())) & mixtures.model.eq(name)].iloc[0]
                active = fit[fit.months.eq(h) & fit.date.eq(str(date.date())) & fit.model.eq(name)].active.iloc[0]
                if not active: continue  # exact original B already verified above
                expected = sum(weights[k]*probabilities[k] for k in ['B', 'month', 'decay'])
                np.testing.assert_allclose(class_probabilities(dated[dated.model.eq(name)]), expected, atol=1e-10)
        pcols = ['p_up', 'p_down', 'p_zero']; bins = ['p_loss_over20', 'p_loss5_20', 'p_near_flat', 'p_gain5_20', 'p_gain_over20']
        assert np.isfinite(data[pcols+bins]).all().all() and data[pcols+bins].ge(0).all().all()
        np.testing.assert_allclose(data[pcols].sum(axis=1), 1, atol=1e-10)
        np.testing.assert_allclose(data[bins].sum(axis=1), 1, atol=1e-10)
        observed = data.actual.notna()
        np.testing.assert_allclose(data.loc[observed, 'brier'], (data.loc[observed, 'p_up']-data.loc[observed, 'actual'].gt(0))**2)
        assert data.loc[~observed, METRICS[:3]].isna().all().all()
        assert data.q05.le(data.q50).all() and data.q50.le(data.q95).all()
        for (model, date), group in pd.concat([data, base]).groupby(['model', 'date']):
            group = group[group.actual.notna() & group.actual.ne(0)]
            if not len(group): continue
            y = group.actual.gt(0)
            diagnostics.append(dict(months=h, model=model, date=date,
                accuracy=((group.p_up > group.p_down) == y).mean(), up_call_rate=(group.p_up > group.p_down).mean(),
                always_down=(~y).mean(), within_month_auc=roc_auc_score(y, group.p_up-group.p_down) if y.nunique() == 2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(diagnostics).groupby(['months', 'model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
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
    new = score[score.model.isin(list(CALIBRATORS)+MIXTURES)]; assert len(new) == 72
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active', new_candidates=6,
        unchanged_references=list(REFERENCE.values()), prediction_rows_per_model=27600,
        maturity_and_burn_in_verified=True, all_event_probabilities_reconstructed=True,
        calibrated_folds=len(params), passed_point_gates=int(new.point_target_met.sum()),
        candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '仍未达到双20%目标。' if not any(decisions.values()) else '存在历史点估计达标候选，仍需验证审核，尚不能宣布完成。'
    lines = ['# R22：已到期预测的概率校准与组合', '', f'**{result}** 本轮6个新候选、2个原样保留的R21参考，累计47候选。原27,600股票月、冻结B、1/3/6个月四项20%门槛保持不变。', '',
        '每月只使用起点和标签结束日都严格早于当前日期的旧预测；至少12个已到期起点月才拟合。两条源分别采用扩展历史或最近24个可用已到期起点月校准。温度斜率与七类截距向恒等变换收缩，保持类别内原分布；不是用当前真实涨跌率修正当前预测。', '',
        '另比较B和两条源固定各1/3的完整分布组合，以及只从最近24个已到期月份学习的非负组合。所有校准与拟合都按月份等权。历史不足时，校准逐值保留原源，学习组合逐值保留B，固定组合仍按固定规则运行。', '',
        '| 期限 | 方法 | 上涨Brier改善 | 五档Brier改善 | CRPS改善 | 命中率相对改善 |', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for model, label in LABELS.items():
            values = score[(score.months == h) & score.model.eq(model)].set_index('metric')
            lines.append(f'| {h}个月 | {label} | '+' | '.join(f'{values.loc[m, "relative_improvement"]:+.2%}' for m in METRICS)+' |')
    lines += ['', '正数为改善，负数为变差。相对原源和近期/扩展窗口的配对比较另报，不能把不同方法或不同阶段的最好指标拼接。', '',
        '## 结果解释', '',
        '四个校准版本没有把阶段性偏差转化为稳定优势，多数概率评分反而变差。例：月份等权源3月原命中率54.45%，扩展校准后52.51%、近期校准后52.71%，且概率评分均不如原源。增加校准不等于增加可预测信息。', '',
        '学习组合6月命中率50.02%→51.38%，相对改善2.72%；上涨Brier、五档Brier、CRPS分别改善0.93%、0.30%、0.55%，仍远低于20%。三个期限平均B权重约92.7%、87.8%、88.1%，这些均值包括历史不足时100%B的月份。固定平均组合也未达标。', '',
        '本轮完成584次有效校准拟合，历史不足的月份保留原预测，未删除早期难预测月份。方向诊断仍显示少量同月排序信息，不能由此推出概率分布已可信或可以用于实际仓位。', '',
        '下一步转向量价交互和日内价格路径的历史特征，与已有换手率/成交额均值作匹配对照。只读探查确认原共同人群涉及的1,242只历史股票都有raw/qfq日线；三只样例含OHLC、成交量、成交额、换手率且单位关系一致。这只证明数据可用，不是新预测成绩，也不证明全部文件已完成质量核验。见[next_feature_probe.json](outputs/r22_probability_recalibration/next_feature_probe.json)。', '',
        '完整核验冻结源与缓存哈希、同样本、逐个校准时点的成熟历史、历史不足时原预测逐值不变、全部事件概率可由参数或组合权重重建。此为反复使用同一历史区间的探索，尚不是独立验证；技术通过不代表达到目标。本轮未验证12个月双20%。', '',
        '明细：[目标评分](outputs/r22_probability_recalibration/target_scoreboard.csv)、[配对比较](outputs/r22_probability_recalibration/paired_comparisons.csv)、[分阶段](outputs/r22_probability_recalibration/phase_scores.csv)、[方向诊断](outputs/r22_probability_recalibration/direction_diagnostics.csv)、[校准参数](outputs/r22_probability_recalibration/calibration_parameters.csv)、[组合权重](outputs/r22_probability_recalibration/mixture_weights.csv)、[技术核验](outputs/r22_probability_recalibration/research_integrity_audit.json)。', '']
    (EP/'probability_recalibration_report.md').write_text('\n'.join(lines))
    print(json.dumps({k: v for k, v in audit.items() if k != 'receipts'}, indent=2))


if __name__ == '__main__':
    run()
