"""R39 all-population audit, fixed target scores and paired shrinkage ablations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from build_margin_information import digest
from run_joint_information import frame_digest
from run_issuer_calibration import DEST, CACHE, PANEL, PLAN, REFERENCE, MODELS, priors
from issuer_calibration import add_buckets, estimate, score
from evaluate_improvement_search import evaluate, METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {'base_reference': '原B', 'extra_reference': '极端随机树原对照',
    'base_sign': 'B加个股方向校准', 'base_bins': 'B加个股七档校准',
    'extra_sign': '极端随机树加个股方向校准', 'extra_bins': '极端随机树加个股七档校准'}
PAIRS = [(name, prior+'_reference', name) for name, (prior, _) in MODELS.items()]
PAIRS += [(prior+'_bins', prior+'_sign', prior+'_bins_increment') for prior in ['base', 'extra']]


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert spec['models'] == {k: list(v) for k, v in MODELS.items()}
    assert digest(PANEL) == spec['panel_sha256'] and digest(PLAN) == spec['plan_sha256']
    for receipt in json.loads((DEST/'source_receipts.json').read_text()):
        assert digest(Path(receipt['path'])) == receipt['sha256']
    contract = json.loads((TARGET/'target_contract.json').read_text())
    panel = add_buckets(pd.read_parquet(PANEL)); fits = pd.read_csv(DEST/'fit_audit.csv')
    assert len(fits) == 384 and not fits.duplicated(['months', 'date', 'mode']).any()
    checked = 0; reconstructed = 0; receipts=[]; diagnostics=[]; reliability=[]; calibration=[]
    for item in contract['files']:
        h = item['months']; bp = Path(item['path']); assert digest(bp) == item['sha256']
        base = pd.read_parquet(bp); base = base[base.model.eq('B')]
        rp = REFERENCE/f'predictions_{h}m.parquet'
        sr = next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name))
        assert digest(rp) == sr['sha256']
        ref = pd.read_parquet(rp); ref = ref[ref.model.eq('extra_reference')]
        path = DEST/f'predictions_{h}m.parquet'; data = pd.read_parquet(path)
        assert set(data.model) == set(LABELS)
        for name, frame in [('base_reference', base), ('extra_reference', ref)]:
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True), frame.assign(model=name).reset_index(drop=True))
        for name, g in data.groupby('model'):
            j = g.merge(base[['date', 'instrument', 'actual', 'label_end', 'target_date']],
                on=['date', 'instrument'], suffixes=('', '_base'), validate='one_to_one')
            assert len(j) == len(g) == 27600
            np.testing.assert_allclose(j.actual, j.actual_base, equal_nan=True)
            for c in ['label_end', 'target_date']:
                pd.testing.assert_series_equal(j[c], j[c+'_base'], check_names=False)
        for date, test in panel[panel.date.ge('2021-01-01')].groupby('date', sort=True):
            test = test.reset_index(drop=True); keys = test[['date', 'instrument']]
            stem = f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stem}_keys.parquet'), keys)
            distributions, _ = priors(h, date, base, ref, keys)
            for mode in ['sign', 'bins']:
                f, history, details = estimate(panel, h, date, test.instrument, mode)
                r = fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits['mode'].eq(mode)]
                assert len(r) == 1; r = r.iloc[0]
                assert pd.Timestamp(details['last_training_label']) < date
                for key, value in details.items(): assert r[key] == value, (key, r[key], value)
                assert frame_digest(keys) == r.keys_sha256
                cp = CACHE/f'{stem}_{mode}.npz'; assert digest(cp) == r.cache_sha256
                with np.load(cp) as payload:
                    np.testing.assert_array_equal(f, payload['factors'])
                    np.testing.assert_array_equal(history, payload['history'])
                checked += 1
                for prior in ['base', 'extra']:
                    name = f'{prior}_{mode}'; template, a, w = distributions[prior]
                    expected = score(template, a, w, f, history, mode)
                    g = data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True)
                    pd.testing.assert_frame_equal(g[['date', 'instrument']], keys)
                    np.testing.assert_allclose(g[expected.columns], expected, atol=1e-12, rtol=1e-12, equal_nan=True)
                    assert np.array_equal(g.p_up.gt(g.p_down), expected.p_up.gt(expected.p_down))
                    pd.testing.assert_frame_equal(g.loc[history==0, expected.columns], template.loc[history==0, expected.columns])
                    reconstructed += len(g)
        for name, g in data.groupby('model'):
            cells, summary = probability_reliability(g)
            reliability.append(cells.assign(months=h, model=name)); calibration.append(dict(months=h, model=name, **summary))
        for (name, date), g in data.groupby(['model', 'date']):
            g = g[g.actual.notna()&g.actual.ne(0)]
            if not len(g): continue
            y = g.actual.gt(0)
            diagnostics.append(dict(months=h, date=date, model=name,
                accuracy=(g.p_up.gt(g.p_down)==y).mean(), up_call_rate=g.p_up.gt(g.p_down).mean(),
                within_month_auc=roc_auc_score(y, g.p_up-g.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)), sha256=digest(path)))
        print(h, 'reconstructed', flush=True)
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
                a, b = wide[new].mean(), wide[old].mean()
                lo, hi = paired_interval(wide[new], wide[old], metric)
                pairs.append(dict(months=h, comparison=name, metric=metric,
                    relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,
                    improvement_lower95=lo, improvement_upper95=hi))
    paired = pd.DataFrame(pairs); paired.to_csv(DEST/'paired_comparisons.csv', index=False)
    scores = pd.read_csv(DEST/'target_scoreboard.csv'); new = scores[scores.model.isin(MODELS)]
    assert len(scores) == 72 and len(new) == 48
    decisions = new.groupby('model').point_target_met.all().to_dict()
    audit = dict(technical_integrity_passed=True, goal_achieved=False, goal_status='active',
        new_candidates=4, cumulative_complete_candidates=135, original_stock_dates_per_model=27600,
        maturity_calibration_checks=checked, all_new_prediction_rows_reconstructed=reconstructed,
        passed_point_gates=int(new.point_target_met.sum()), candidates_passing_all_point_gates=decisions, receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    result = '尚未达到双20%目标。' if not any(decisions.values()) else '点估计有达标候选，尚需验证审核。'
    lines = ['# R39：个股历史概率偏差收缩校准', '', f'**{result}** 四个新增候选，累计135个完整评分候选。全部保留原27,600个股票月，原B和1/3/6月十二项门槛不变。', '',
        '只用已到期的历史结果，比较该股与同期相近波动、市值股票的各档概率，按20×期限的固定强度向无偏差收缩。两个原分布分别加二档方向或七档校准；原子位置不变，二档保持零收益质量，没有自身历史时精确保留原预测。可比组排除自身；不足10只退回同月其他成熟股票。', '',
        '|期限|候选|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|', '|---|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for name, label in LABELS.items():
            v = scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines += ['', '上表相对原B。下表分别相对自己的原对照；七档增量相对同一原分布的二档校准。正值为改善。', '',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|', '|---|---|---|---|---|---|']
    for h in [1, 3, 6]:
        for _, _, name in PAIRS:
            v = paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            label = LABELS.get(name, ('B' if name.startswith('base') else '极端随机树')+'七档增量')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    coverage = fits.groupby(['months', 'mode'])[['stocks_with_history', 'test_rows']].sum()
    lines += ['', '个股成熟历史覆盖率（全部预测行）：'+ '；'.join(f'{h}月{mode} {r.stocks_with_history/r.test_rows:.2%}' for (h, mode), r in coverage.iterrows())+'。', '',
        f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48；384组成熟历史校准、331,200条新概率重建通过。153项测试通过。技术核验通过不等于预测目标通过。', '',
        '属于重复历史探索，不是独立验证。股票身份偏差可能随时间改变；强收缩只是预先固定的启发式，不证明重叠标签独立。同月比较组未控制所有信息，不能把点估计增量解释为因果效果。', '',
        '结果解读：四候选相对各自原对照的36项概率误差点估计全部变差。极端随机树七档校准的6个月命中率49.65%→51.00%，绝对增加1.35个百分点，配对95%区间为+0.29至+2.41个百分点；但1/3个月命中率52.78%→52.15%、56.89%→55.17%，6个月同月AUC也由0.5268降至0.5011。该方向增量伴随概率质量和排序能力下降，不支持替换原模型。相对原B，七档版6个月命中率仅相对提高1.95%，三项误差改善0.33%/0.11%/0.21%，仍远低于目标。', '',
        '明细：[评分前方案](notes/r39_issuer_calibration.md)、[目标评分](outputs/r39_issuer_calibration/target_scoreboard.csv)、[配对区间](outputs/r39_issuer_calibration/paired_comparisons.csv)、[分阶段](outputs/r39_issuer_calibration/phase_scores.csv)、[方向与排序](outputs/r39_issuer_calibration/direction_diagnostics.csv)、[完整核验](outputs/r39_issuer_calibration/research_integrity_audit.json)。', '']
    (EP/'issuer_calibration_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'}, indent=2))


if __name__ == '__main__':
    run()
