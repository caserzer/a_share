"""R30 chronological refit and full-distribution scoring audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from prepare_diverse_sources import DEST,CACHE,NAMES,load_components
from run_diverse_ensemble import MODELS,ALL_MODELS,MIN_MONTHS
from diverse_ensemble import fit_joint_mixture,fit_sign_stack,sign_transform,replace_sign_mass,mixed_crps,cdf_distance
from probability_recalibration import calibration_history
from run_prequential_search import combine_distributions
from run_direct_probability import weighted_stats
from hierarchical_probabilities import stable_sign_scores
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'uniform_diverse':'七源等权','joint_expanding':'联合误差/扩展','joint_recent24':'联合误差/近期24月',
        'sign_expanding':'方向校准/扩展','sign_recent24':'方向校准/近期24月'}
PAIRS=[(n,'uniform_diverse',n) for n in MODELS]+[('joint_recent24','joint_expanding','joint_window'),('sign_recent24','sign_expanding','sign_window')]


def run():
    source=json.loads((DEST/'source_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert source['technical_source_integrity_passed'] and source['max_recovered_baseline_score_error']==0
    assert digest(DEST/'source_audit.json')==spec['source_audit_sha256']
    assert digest(EP/'notes/r30_diverse_ensemble.md')==spec['plan_sha256']==source['plan_sha256']
    assert digest(DEST/'baseline_precision_audit.json')==source['baseline_recovery_audit_sha256']
    recovery=json.loads((DEST/'baseline_precision_audit.json').read_text());assert recovery['recovery_matches_all_frozen_baseline_scores']
    assert digest(DEST/'input_cache_receipts.csv')==source['input_cache_receipts_sha256']
    cache_receipts=pd.read_csv(DEST/'input_cache_receipts.csv').to_dict('records')
    for r in source['prediction_receipts']+source['prepared_receipts']+recovery['receipts']+cache_receipts:
        assert digest(Path(r['path']))==r['sha256']
    fit=pd.read_csv(DEST/'fit_audit.csv');params=json.loads((DEST/'parameters.json').read_text())
    assert len(fit)==len(params)==768 and not fit.duplicated(['months','date','model']).any() and set(fit.model)==set(MODELS)
    lookup={(p['months'],p['date'],p['model']):p for p in params};assert len(lookup)==768
    contract=json.loads((TARGET/'target_contract.json').read_text());receipts=[];reconstructed=0;active_refits=0;warmup_rows=0;distance_pairs=0
    diagnostic=[];reliability=[];calibration=[]
    for item in contract['files']:
        h=item['months'];path=Path(item['path']);assert digest(path)==item['sha256']
        b=pd.read_parquet(path);b=b[b.model.eq('B')]
        meta=pd.read_parquet(CACHE/f'keys_{h}m.parquet');uniform=pd.read_parquet(CACHE/f'uniform_{h}m.parquet')
        with np.load(CACHE/f'sources_{h}m.npz') as x:data={k:x[k] for k in x.files}
        predpath=DEST/f'predictions_{h}m.parquet';pred=pd.read_parquet(predpath);assert set(pred.model)==set(ALL_MODELS)
        for name,g in pred.groupby('model'):
            j=g.merge(b[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,template in meta.groupby('date',sort=True):
            current=template.index.to_numpy();template=template.reset_index(drop=True);keys=template[['date','instrument']]
            components,_=load_components(h,date,keys);prior=np.full(len(NAMES),1/len(NAMES));ua,uw=combine_distributions(components,prior)
            expected_uniform=weighted_stats(ua,uw,template.actual);fallback=uniform[uniform.date.eq(date)].reset_index(drop=True)
            np.testing.assert_allclose(fallback[expected_uniform.columns],expected_uniform,atol=1e-12,rtol=1e-12,equal_nan=True)
            ug=pred[pred.date.eq(date)&pred.model.eq('uniform_diverse')].reset_index(drop=True)
            pd.testing.assert_frame_equal(ug,fallback);reconstructed+=len(ug)
            np.testing.assert_allclose(expected_uniform.crps,mixed_crps(data['crps'][current],data['distance'][current],prior),atol=1e-12,rtol=1e-12,equal_nan=True)
            if str(date.date()) in ['2021-01-29','2023-12-29','2026-04-30']:
                for i in range(len(NAMES)):
                    for j in range(i):
                        np.testing.assert_allclose(cdf_distance(*components[i],*components[j]),data['distance'][current,i,j],atol=1e-14)
                        distance_pairs+=1
            for name,(kind,window) in MODELS.items():
                history=calibration_history(meta,date,window);ix=history.index.to_numpy();active=history.date.nunique()>=MIN_MONTHS
                r=fit[fit.months.eq(h)&fit.date.eq(str(date.date()))&fit.model.eq(name)].iloc[0]
                p=lookup[(h,str(date.date()),name)];coeff=np.asarray(p['coefficients']);pars=np.asarray(p['sign_parameters'])
                assert r.active==active==p['active'] and r.history_rows==len(history) and r.history_months==history.date.nunique()
                assert r.test_rows==len(template)
                if len(history):
                    assert history.date.max()<date and history.label_end.max()<date
                    assert pd.Timestamp(r.latest_history_label)==history.label_end.max()
                    assert pd.Timestamp(r.first_origin)==history.date.min() and pd.Timestamp(r.last_origin)==history.date.max()
                g=pred[pred.date.eq(date)&pred.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                if not active:
                    pd.testing.assert_frame_equal(g,fallback.assign(model=name));np.testing.assert_array_equal(coeff,prior)
                    np.testing.assert_array_equal(pars,np.zeros(24));warmup_rows+=len(g)
                else:
                    y=history.actual.to_numpy()
                    if kind=='joint':
                        expected_coef,info=fit_joint_mixture(data['sign'][ix],data['five_bin'][ix],data['crps'][ix],data['distance'][ix],y,history.date,
                            history[['brier','multiclass_brier','crps']].to_numpy())
                        np.testing.assert_allclose(coeff,expected_coef,atol=1e-9,rtol=1e-9)
                        a,w=combine_distributions(components,coeff);target=np.einsum('nsc,s->nc',data['sign'][current],coeff)
                    else:
                        expected_pars,info=fit_sign_stack(data['sign'][ix],y,history.date)
                        np.testing.assert_allclose(pars,expected_pars,atol=1e-9,rtol=1e-9)
                        target=sign_transform(data['sign'][current],pars);a,w=replace_sign_mass(ua,uw,target)
                    for k,v in info.items():np.testing.assert_allclose(p[k],v,atol=1e-9,rtol=1e-9)
                    expected=stable_sign_scores(weighted_stats(a,w,template.actual),target,target,1.,template.actual)
                    np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True);active_refits+=1
                reconstructed+=len(g)
        for name,g in pd.concat([pred,b]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
        for (name,date),g in pd.concat([pred,b]).groupby(['model','date']):
            g=g[g.actual.notna()&g.actual.ne(0)]
            if not len(g):continue
            y=g.actual.gt(0);diagnostic.append(dict(months=h,date=date,model=name,accuracy=((g.p_up>g.p_down)==y).mean(),
                up_call_rate=(g.p_up>g.p_down).mean(),always_down=(~y).mean(),
                within_month_auc=roc_auc_score(y,g.p_up-g.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(predpath.relative_to(EP)),sha256=digest(predpath)))
    pd.DataFrame(diagnostic).groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly=pd.read_csv(DEST/'monthly_scores.csv');pairs=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,comparison in PAIRS:
                a,bvalue=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                pairs.append(dict(months=h,comparison=comparison,metric=metric,relative_improvement=a/bvalue-1 if metric=='accuracy' else 1-a/bvalue,
                                  improvement_lower95=lo,improvement_upper95=hi))
    pd.DataFrame(pairs).to_csv(DEST/'paired_comparisons.csv',index=False)
    weight_rows=[]
    for p in params:
        if p['kind']=='joint':weight_rows.append(dict(months=p['months'],date=p['date'],model=p['model'],active=p['active'],**dict(zip(NAMES,p['coefficients']))))
    pd.DataFrame(weight_rows).to_csv(DEST/'mixture_weights.csv',index=False)
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==60 and set(score.model)==set(ALL_MODELS)
    decisions=score.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=5,
        all_new_prediction_rows_reconstructed=reconstructed,active_parameter_refits=active_refits,exact_uniform_warmup_rows=warmup_rows,
        pairwise_cdf_integrals_independently_recomputed=distance_pairs,all_history_maturity_checked=True,
        frozen_baseline_unchanged=True,recovered_baseline_matches_original_exactly=True,
        passed_point_gates=int(score.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '存在点估计达标候选，需要完整验证审核。'
    lines=['# R30：多来源分布组合与方向校准','',f'**{result}** 五个正式候选，累计87个候选。固定原B、27,600股票月与1/3/6个月全部12项门槛。','',
        '七个组件覆盖原B、提升树、随机森林、极端随机树、方向专用模型、两融因素和海外因素。除B外均用原始未混合分布，避免重复加入B。测试固定等权、三项概率误差联合优化的扩展/近期权重，以及独立的扩展/近期方向校准。','',
        f'学习仅使用旧预测中当时已经到期的结果，至少12个起点月，月份等权。历史不足时逐值保留等权分布，未删除早期股票月。所有{active_refits}次有效拟合已按成熟历史重跑核验，全部{reconstructed}条新预测重建通过。','',
        '精度核验发现旧B的float32缓存影响1条预测的分档概率，没有方向判断变化，1个月月等权五档误差变化约2.94e-7。已按原算法恢复float64原子，全部评分与原报告逐项完全一致，原报告和旧缓存未改。新B组件使用恢复版；验收与训练尺度仍使用冻结B原评分。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','正值表示改善，负值表示变差。三项概率误差的训练目标没有替代最终方向命中率门槛；不得跨模型或跨阶段拼接最好指标。技术核验不代表有效性。仍为多轮历史探索，保留原数据版本与股票池限制，12个月双20%尚未验证。','',
        '明细：[事前方案](notes/r30_diverse_ensemble.md)、[目标评分](outputs/r30_diverse_ensemble/target_scoreboard.csv)、[配对增量](outputs/r30_diverse_ensemble/paired_comparisons.csv)、[权重](outputs/r30_diverse_ensemble/mixture_weights.csv)、[分阶段](outputs/r30_diverse_ensemble/phase_scores.csv)、[概率校准](outputs/r30_diverse_ensemble/calibration_summary.csv)、[方向诊断](outputs/r30_diverse_ensemble/direction_diagnostics.csv)、[基线精度核验](outputs/r30_diverse_ensemble/baseline_precision_audit.json)、[完整核验](outputs/r30_diverse_ensemble/research_integrity_audit.json)。','']
    (EP/'diverse_ensemble_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
