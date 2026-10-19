"""R47 mature-history audit, independent parameter reconstruction and target scores."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit,softmax
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_joint_information import frame_digest
from run_mature_neural_calibration import DEST,CACHE,PLAN,SOURCE,REFERENCES,COHORT_REFERENCES,ANCHOR_SOURCE,MODELS,distributions,history_digest
from cohort_probability_anchor import score
from mature_neural_calibration import history_for,fit_history,apply,WINDOW,MIN_MONTHS,BOUND,PENALTY
from probability_recalibration import class_probabilities
from evaluate_improvement_search import evaluate,METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'raw_reference':'原独立网络','mixed_reference':'原混合网络','raw_sign':'独立历史方向校准','raw_bins':'独立历史七档校准','mixed_sign':'混合历史方向校准','mixed_bins':'混合历史七档校准'}
LABELS.update({'cohort_'+k:label for k,label in [('raw_sign','独立固定方向锚'),('raw_bins','独立固定七档锚'),('mixed_sign','混合固定方向锚'),('mixed_bins','混合固定七档锚')]})
PAIRS=[(name,source+'_reference',name) for name,(source,_) in MODELS.items()]
PAIRS += [(name,'cohort_'+name,name+'_vs_fixed_anchor') for name in MODELS]
PAIRS += [(source+'_bins',source+'_sign',source+'_bins_increment') for source in ['raw','mixed']]


def independent_reconstruction(p,q,parameters,mode):
    if mode=='sign':
        assert parameters.shape==(1,) and abs(parameters[0])<=BOUND
        up=p[:,4:].sum(axis=1);down=p[:,:3].sum(axis=1);mass=up+down
        newup=mass*expit(np.log(up)-np.log(down)+parameters[0]);expected=p.copy()
        expected[:,:3]*=((mass-newup)/down)[:,None];expected[:,4:]*=(newup/up)[:,None]
        np.testing.assert_array_equal(q[:,3],p[:,3])
        delta=np.log(q[:,4:].sum(axis=1)/q[:,:3].sum(axis=1))-np.log(up/down)
        np.testing.assert_allclose(delta,parameters[0],atol=1e-12,rtol=1e-12)
    else:
        assert parameters.shape==(8,) and .25<=parameters[0]<=4 and (np.abs(parameters[1:])<=2).all()
        expected=softmax(parameters[0]*np.log(np.clip(p,1e-6,1.))+parameters[1:],axis=1)
    np.testing.assert_allclose(q,expected,atol=1e-12,rtol=1e-12)


def run():
    spec=json.loads((DEST/'spec.json').read_text())
    assert spec['models']=={k:list(v) for k,v in MODELS.items()} and spec['references']==REFERENCES
    assert digest(PLAN)==spec['plan_sha256'] and WINDOW==spec['window'] and MIN_MONTHS==spec['minimum_mature_months']
    assert spec['cohort_references']==COHORT_REFERENCES and spec['penalty']==PENALTY and spec['sign_intercept_bound']==BOUND
    assert digest(SOURCE/'fit_audit.csv')==spec['source_fit_sha256']
    for receipt in json.loads((DEST/'source_receipts.json').read_text()):assert digest(Path(receipt['path']))==receipt['sha256']
    sourcefits=pd.read_csv(SOURCE/'fit_audit.csv');fits=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fits)==768 and not fits.duplicated(['months','date','model']).any()
    contract=json.loads((TARGET/'target_contract.json').read_text());checked=0;reconstructed=0;receipts=[];diagnostics=[];reliability=[];calibration=[];parameters_log=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')];path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path)
        assert set(data.model)==set(LABELS)
        rp=SOURCE/f'predictions_{h}m.parquet';r=next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256']
        old=pd.read_parquet(rp)
        ap=ANCHOR_SOURCE/f'predictions_{h}m.parquet';r=next(r for r in spec['cohort_receipts'] if r['path'].endswith(ap.name));assert digest(ap)==r['sha256']
        cohort=pd.read_parquet(ap)
        for name,oldname in COHORT_REFERENCES.items():
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True),cohort[cohort.model.eq(oldname)].assign(model=name).reset_index(drop=True))
        originals={source:old[old.model.eq('alpha16_'+source)] for source in ['raw','mixed']}
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
                prior,a,w,p=inputs[source];np.testing.assert_allclose(class_probabilities(prior),p,atol=1e-12,rtol=1e-12)
                r=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits.model.eq(name)];assert len(r)==1;r=r.iloc[0]
                assert r.test_rows==len(keys) and r.keys_sha256==frame_digest(keys)
                history=history_for(originals[source],date,mode)
                assert history.date.nunique()<=WINDOW and len(history)==r.history_rows and history.date.nunique()==r.history_months
                assert (history.date<date).all() and (history.label_end<date).all() and history.actual.notna().all()
                if mode=='sign':assert history.actual.ne(0).all()
                for col,expected_time in [('first_origin',history.date.min()),('last_origin',history.date.max()),('last_history_label',history.label_end.max())]:
                    recorded=pd.to_datetime(r[col]);assert (pd.isna(recorded) and pd.isna(expected_time)) or recorded==expected_time
                for key,value in history_digest(history,mode).items():assert r[key]==value
                pars,active,info=fit_history(history,mode);assert bool(r.active)==active
                for key,value in info.items():
                    if np.isnan(value):assert pd.isna(r[key])
                    else:np.testing.assert_allclose(r[key],value,atol=1e-12,rtol=1e-10)
                cp=CACHE/f'{stem}_{name}.npz';assert digest(cp)==r.cache_sha256
                with np.load(cp) as payload:
                    np.testing.assert_array_equal(p,payload['before']);q=payload['after'];parameters=payload['parameters']
                    np.testing.assert_allclose(parameters,pars,atol=1e-12,rtol=1e-12)
                parameters_log.append(dict(months=h,date=date,model=name,active=active,history_months=len(history.date.unique()),
                    scale=parameters[0] if mode=='bins' else 1.,**{f'intercept_{k}':float(v) for k,v in enumerate(parameters[1:] if mode=='bins' else parameters)}))
                g=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                if active:
                    independent_reconstruction(p,q,parameters,mode)
                    expected=score(prior,a,w,p,q)
                    np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                    assert np.array_equal(g.p_up.gt(g.p_down),expected.p_up.gt(expected.p_down))
                else:
                    np.testing.assert_array_equal(q,p)
                    pd.testing.assert_frame_equal(g,prior.assign(model=name))
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
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'all mature histories and forecasts rebuilt',flush=True)
    assert checked==768 and reconstructed==331200
    pd.DataFrame(parameters_log).to_csv(DEST/'calibration_parameters.csv',index=False)
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
    scores=pd.read_csv(DEST/'target_scoreboard.csv');new=scores[scores.model.isin(MODELS)];assert len(scores)==120 and len(new)==48
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=167,
        original_stock_dates_per_model=27600,mature_history_calibration_checks=checked,all_new_prediction_rows_reconstructed=reconstructed,
        active_calibration_fits=int(fits.active.sum()),unchanged_burn_in_cases=int((~fits.active).sum()),
        unchanged_burn_in_rows=int(fits.loc[~fits.active,'test_rows'].sum()),
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R47：成熟历史学习的神经网络概率校准','',f'**{result}** 四新增候选，累计167个完整评分候选。原B、27,600股票月及1/3/6月全部12项门槛不变。','',
        '复用R45 alpha=16独立/混合分布，只用起点和标签结束日均严格早于当前预测日的成熟历史学习校准。固定最近36起点月、至少12起点月、月份等权、向恒等变换的L2惩罚0.01。方向版学习一个有界截距；七档版复用R22的正斜率加类别截距。历史不足时逐值保留原预测，预热月全部参与验收。对照含未校准源及R46固定锚定版本。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表四候选对各自原分布、对R46同来源同模式固定锚定，以及七档对同来源方向版。正值改善、负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    extra={'raw_bins_increment':'独立七档对方向','mixed_bins_increment':'混合七档对方向'}
    extra.update({name+'_vs_fixed_anchor':LABELS[name]+'对固定锚' for name in MODELS})
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS.get(name,extra.get(name,name))}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。768次成熟历史校验及331,200条预测重建通过；其中有效校准拟合{audit["active_calibration_fits"]}次，{audit["unchanged_burn_in_cases"]}份预热预测逐值不变（{audit["unchanged_burn_in_rows"]:,}行）。','',
        '历史校准假设偏差可迁移到随后月份，不能保证市场状态改变后仍有效。方向版保留条件上涨概率排序；七档版不保证上涨排序。依旧属于重复历史探索，继承基础网络有限轮数未确认收敛及样本/历史数据版本边界。','',
        '结果解读：独立方向校准1月命中率54.50%→56.60%，对原B相对提高8.89%；对原网络绝对增量2.10个百分点，配对95%区间[-0.15,+4.38]个百分点，尚不能确认稳定增益。其上涨Brier/CRPS相对原B改善1.24%/0.57%，五档Brier变差0.35%，未满足概率目标。同一候选3月命中率53.60%，三项误差对B变差5.28%/1.92%/2.72%；6月49.44%，三项误差变差14.71%/3.86%/6.10%。6月四个历史校准候选相对各自未校准源的上涨及五档Brier增量区间全部为负，两种七档校准的CRPS增量区间也为负。方向校准逐月条件上涨AUC确实完全不变，故这轮变化来自概率水平而非新增排序信息。历史校准偏差在本轮长周期上没有有效迁移；不宜据1月命中率点估计替换全期限模型。180项测试通过；584次有效拟合均完成，184份预热预测共76,188行逐值保留，全部月份仍进入验收。','',
        '明细：[评分前方案](notes/r47_mature_neural_calibration.md)、[目标评分](outputs/r47_mature_neural_calibration/target_scoreboard.csv)、[配对区间](outputs/r47_mature_neural_calibration/paired_comparisons.csv)、[成熟历史](outputs/r47_mature_neural_calibration/fit_audit.csv)、[校准参数](outputs/r47_mature_neural_calibration/calibration_parameters.csv)、[方向与排序](outputs/r47_mature_neural_calibration/direction_diagnostics.csv)、[完整核验](outputs/r47_mature_neural_calibration/research_integrity_audit.json)。','']
    (EP/'mature_neural_calibration_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
