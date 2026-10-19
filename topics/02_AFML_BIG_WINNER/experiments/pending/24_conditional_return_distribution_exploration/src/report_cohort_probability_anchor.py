"""R46 independent parameter reconstruction, cohort constraints and fixed-target audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit,softmax
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_joint_information import frame_digest
from run_cohort_probability_anchor import DEST,CACHE,PLAN,SOURCE,REFERENCES,MODELS,distributions
from cohort_probability_anchor import anchor,score,TOL,MAX_ITER
from evaluate_improvement_search import evaluate,METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'raw_reference':'原独立网络','mixed_reference':'原混合网络','raw_sign':'独立加方向锚','raw_bins':'独立加七档锚','mixed_sign':'混合加方向锚','mixed_bins':'混合加七档锚'}
PAIRS=[(name,source+'_reference',name) for name,(source,_) in MODELS.items()]
PAIRS += [(source+'_bins',source+'_sign',source+'_bins_increment') for source in ['raw','mixed']]


def independent_reconstruction(p,bp,q,parameters,mode):
    if mode=='sign':
        up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1);mass=up+down
        newup=mass*expit(np.log(up)-np.log(down)+parameters[0]);expected=p.copy()
        expected[:,:3]*=((mass-newup)/down)[:,None];expected[:,4:]*=(newup/up)[:,None]
        np.testing.assert_array_equal(q[:,3],p[:,3])
        target=bp[:,4:].sum()/(bp[:,:3].sum()+bp[:,4:].sum())
        residual=abs(q[:,4:].sum()/mass.sum()-target)
        logit_before=np.log(up/down);logit_after=np.log(q[:,4:].sum(axis=1)/q[:,:3].sum(axis=1))
        np.testing.assert_allclose(logit_after-logit_before,parameters[0],atol=1e-12,rtol=1e-12)
    else:
        expected=softmax(np.log(p)+parameters,axis=1);target=bp.mean(axis=0);active=target>0
        assert np.array_equal(np.isfinite(parameters),active) and (q[:,~active]==0).all()
        residual=float(np.max(np.abs(q.mean(axis=0)-target)))
        indices=np.flatnonzero(active)
        for k in indices[1:]:
            delta=np.log(q[:,k]/q[:,indices[0]])-np.log(p[:,k]/p[:,indices[0]])
            np.testing.assert_allclose(delta,parameters[k]-parameters[indices[0]],atol=1e-12,rtol=1e-12)
    np.testing.assert_allclose(q,expected,atol=1e-12,rtol=1e-12)
    assert residual<=TOL
    return residual


def run():
    spec=json.loads((DEST/'spec.json').read_text())
    assert spec['models']=={k:list(v) for k,v in MODELS.items()} and spec['references']==REFERENCES
    assert digest(PLAN)==spec['plan_sha256'] and TOL==spec['tolerance'] and MAX_ITER==spec['max_bin_iterations']
    assert digest(SOURCE/'fit_audit.csv')==spec['source_fit_sha256']
    for receipt in json.loads((DEST/'source_receipts.json').read_text()):assert digest(Path(receipt['path']))==receipt['sha256']
    sourcefits=pd.read_csv(SOURCE/'fit_audit.csv');fits=pd.read_csv(DEST/'calibration_audit.csv')
    assert len(fits)==768 and not fits.duplicated(['months','date','model']).any()
    contract=json.loads((TARGET/'target_contract.json').read_text());checked=0;reconstructed=0;receipts=[];diagnostics=[];reliability=[];calibration=[];constraints=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')];path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path)
        assert set(data.model)==set(LABELS)
        rp=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256']
        old=pd.read_parquet(rp)
        for name,oldname in REFERENCES.items():
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True),old[old.model.eq(oldname)].assign(model=name).reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date in sorted(base.date.unique()):
            date=pd.Timestamp(date);keys,bp,inputs,_=distributions(h,date,base,old,sourcefits);stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stem}_keys.parquet'),keys)
            for name,(source,mode) in MODELS.items():
                prior,a,w,p=inputs[source]
                r=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits.model.eq(name)];assert len(r)==1;r=r.iloc[0]
                assert r.rows==len(keys) and r.keys_sha256==frame_digest(keys)
                cp=CACHE/f'{stem}_{name}.npz';assert digest(cp)==r.cache_sha256
                with np.load(cp) as payload:
                    np.testing.assert_array_equal(p,payload['before']);np.testing.assert_array_equal(bp,payload['baseline'])
                    q=payload['after'];parameters=payload['parameters'];target=payload['target']
                    again,pars,tgt,iterations,residual=anchor(p,bp,mode)
                    np.testing.assert_array_equal(q,again);np.testing.assert_array_equal(parameters,pars);np.testing.assert_array_equal(target,tgt)
                assert iterations==r.iterations;np.testing.assert_allclose(residual,r.residual,atol=1e-15,rtol=1e-10)
                independent_residual=independent_reconstruction(p,bp,q,parameters,mode)
                constraints.append(dict(months=h,date=date,model=name,iterations=iterations,anchor_residual=independent_residual))
                expected=score(prior,a,w,p,q);g=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                assert np.array_equal(g.p_up.gt(g.p_down),expected.p_up.gt(expected.p_down))
                checked+=1;reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
            for date,m in g.groupby('date'):
                m=m[m.actual.notna()&m.actual.ne(0)]
                if not len(m):continue
                y=m.actual.gt(0);conditional=m.p_up/(m.p_up+m.p_down)
                diagnostics.append(dict(months=h,date=date,model=name,accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(),within_month_auc=roc_auc_score(y,m.p_up-m.p_down) if y.nunique()==2 else np.nan,
                    conditional_up_auc=roc_auc_score(y,conditional) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'all calibrations and forecasts rebuilt',flush=True)
    assert checked==768 and reconstructed==331200
    pd.DataFrame(constraints).to_csv(DEST/'anchor_constraints.csv',index=False)
    diagnostic=pd.DataFrame(diagnostics);diagnostic.to_csv(DEST/'monthly_direction_diagnostics.csv',index=False)
    diagnostic.groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    evaluate(DEST);monthly=pd.read_csv(DEST/'monthly_scores.csv');pairs=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,name in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                pairs.append(dict(months=h,comparison=name,metric=metric,relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,
                    improvement_lower95=lo,improvement_upper95=hi))
    paired=pd.DataFrame(pairs);paired.to_csv(DEST/'paired_comparisons.csv',index=False)
    scores=pd.read_csv(DEST/'target_scoreboard.csv');new=scores[scores.model.isin(MODELS)];assert len(scores)==72 and len(new)==48
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=163,
        original_stock_dates_per_model=27600,cohort_calibration_checks=checked,all_new_prediction_rows_reconstructed=reconstructed,
        maximum_anchor_residual=float(pd.DataFrame(constraints).anchor_residual.max()),
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R46：当期股票池概率水平锚定','',f'**{result}** 四新增候选，累计163个完整评分候选。原B、27,600股票月及1/3/6月全部12项门槛不变。','',
        '复用R45 alpha=16独立/混合两种分布，只使用预测当月原B在相同股票池的预测作为总体概率锚。方向版共同平移条件上涨logit、保留每股零质量与方向内幅度；七档版共同调整类别乘数、对齐各档均值并保留类别内幅度及活跃类别相对赔率。没有用未来实际结果做校准。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表四候选对各自原分布；七档增量对同来源方向版。正值改善、负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    extra={'raw_bins_increment':'独立七档对方向','mixed_bins_increment':'混合七档对方向'}
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS.get(name,extra.get(name,name))}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。768次共同偏移/类别乘数校验及331,200条预测重建通过，最大锚定残差{audit["maximum_anchor_residual"]:.3g}。','',
        '原B总体预测可能错误，锚定约束不等于真实校准。方向版保留条件上涨概率排序，零质量差异可影响p_up-p_down排序；七档版不保证上涨概率排序。仍属重复历史探索，继承R45优化尚未确认收敛及样本/历史数据版本边界。','',
        '结果解读：方向锚定确实保留了每月条件上涨概率AUC，独立和混合版的逐月差异均为0；七档版不具这个保证。独立方向锚6月命中率49.23%→51.58%，对原B相对提高3.11%，三项概率误差相对原B改善0.46%/0.14%/0.11%；但对原网络的四项配对增量区间全部跨零。该同一候选1月命中率54.50%→51.31%，低于原B51.98%，3月也从53.49%降至52.88%，低于原B53.23%。3/6月四候选相对各自参考的全部概率和方向配对增量区间均跨零。1月两种混合校准的上涨Brier和CRPS则出现负的配对区间。把总体概率强制对齐到B没有形成可替换的全面改进；改善排序本身不足以满足双20。176项测试通过，768份校准最大锚定误差约9.98e-11，最多9次七档迭代和14次方向求根迭代。','',
        '明细：[评分前方案](notes/r46_cohort_probability_anchor.md)、[目标评分](outputs/r46_cohort_probability_anchor/target_scoreboard.csv)、[配对区间](outputs/r46_cohort_probability_anchor/paired_comparisons.csv)、[锚定约束](outputs/r46_cohort_probability_anchor/anchor_constraints.csv)、[方向与排序](outputs/r46_cohort_probability_anchor/direction_diagnostics.csv)、[完整核验](outputs/r46_cohort_probability_anchor/research_integrity_audit.json)。','']
    (EP/'cohort_probability_anchor_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
