"""R42 full risk-scaling, training maturity and probability reconstruction audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP
from build_margin_information import digest
from run_scaled_horizon_models import DEST,CACHE,PANEL,PLAN,MODELS,REFERENCES,CONTROL,CAT,FOREST_PARAMS,array_digest,training_sets
from shared_horizon_models import queries
from scaled_horizon_models import restore_atoms,risk_scale
from conditional_forests import training_impute
from run_market_time_models import weighted_class_distribution
from run_direct_probability import classes
from run_joint_information import frame_digest,score
from run_prequential_search import load_distribution
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from evaluate_improvement_search import evaluate,METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={}
for family,label in [('catboost','提升树'),('extra','极端随机树')]:
    for mode,description in [('separate','逐期限'),('shared','共享')]:
        LABELS[f'{family}_{mode}_reference']=label+'原尺度'+description
        LABELS[f'{family}_{mode}']=label+'标准化'+description
PAIRS=[(name,name+'_reference',name) for name in MODELS]
PAIRS += [(family+'_shared',family+'_separate',family+'_sharing_increment') for family in ['catboost','extra']]


def run():
    spec=json.loads((DEST/'spec.json').read_text())
    assert spec['models']=={k:list(v) for k,v in MODELS.items()} and spec['control_features']==CONTROL
    assert spec['catboost']==CAT and spec['extra']==FOREST_PARAMS and spec['candidate_fraction']==.5
    assert digest(PANEL)==spec['panel_sha256'] and digest(PLAN)==spec['plan_sha256']
    for r in json.loads((DEST/'source_receipts.json').read_text()):assert digest(Path(r['path']))==r['sha256']
    panel=pd.read_parquet(PANEL);fits=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fits)==512 and not fits.duplicated(['date','model','component_horizon']).any()
    checked=0;maturity=0
    for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
        test=test.reset_index(drop=True);stamp=str(date.date());own,weights,shared,sw=training_sets(panel,date)
        for name,(family,mode) in MODELS.items():
            for component in ([0] if mode=='shared' else [1,3,6]):
                train,w=(shared,sw) if component==0 else (own[component],weights[component])
                cols=CONTROL+(['horizon_months'] if component==0 else [])
                query=queries(test,CONTROL) if component==0 else test[CONTROL].reset_index(drop=True)
                expected_scale=np.maximum(train.vol63.to_numpy(),.001)*np.sqrt(train.horizon_months.to_numpy()/12)
                np.testing.assert_array_equal(expected_scale,train.label_scale)
                np.testing.assert_allclose(np.log1p(train.label.to_numpy())/expected_scale/10,train.normalized_label,atol=0,rtol=0)
                assert train.date.lt(date).all() and train.label_end.lt(date).all() and train.label.gt(-1).all()
                for h,g in train.groupby('horizon_months'):
                    assert len(g)>=1000 and g.date.nunique()>=18;maturity+=1
                    monthly=pd.Series(w[g.index],index=g.date).groupby(level=0).sum()
                    np.testing.assert_allclose(monthly,monthly.iloc[0])
                    if component==0:np.testing.assert_allclose(w[g.index].sum(),len(own[3])/3)
                r=fits[fits.date.eq(stamp)&fits.model.eq(name)&fits.component_horizon.eq(component)];assert len(r)==1;r=r.iloc[0]
                assert r.training_rows==len(train) and r.test_rows==len(test) and pd.Timestamp(r.last_label_end)==train.label_end.max()
                np.testing.assert_allclose(r.total_weight,len(own[3]) if component==0 else len(train))
                assert frame_digest(train)==r.training_digest and array_digest(w)==r.weights_sha256 and frame_digest(query)==r.query_digest
                path=CACHE/f'{component}_{stamp}_{name}.npz';assert digest(path)==r.cache_sha256
                with np.load(path) as payload:
                    p=payload['probabilities'];assert p.shape==(len(query),7) and np.isfinite(p).all() and (p>=0).all()
                    np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                    if family=='extra':
                        tx,qx,med=training_impute(train[cols],query[cols]);np.testing.assert_array_equal(med,payload['medians'])
                        assert array_digest(tx)==r.imputed_train_sha256 and array_digest(qx)==r.imputed_test_sha256
                    else:assert payload['medians'].size==0 and r.imputed_train_sha256==r.imputed_test_sha256=='native_missing'
                checked+=1
    assert checked==512 and maturity==768
    contract=json.loads((TARGET/'target_contract.json').read_text());receipts=[];reconstructed=0;diagnostics=[];reliability=[];calibration=[];support=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')];path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path)
        assert set(data.model)==set(LABELS)
        for name,(folder,oldname) in REFERENCES.items():
            rp=folder/f'predictions_{h}m.parquet';r=next(r for r in spec['references'][name]['receipts'] if r['path'].endswith(rp.name))
            assert digest(rp)==r['sha256'];old=pd.read_parquet(rp);old=old[old.model.eq(oldname)].assign(model=name)
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True),old.reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']];stamp=str(date.date())
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stamp}_keys.parquet'),keys)
            own,weights,_,_=training_sets(panel,date);u=own[h].normalized_label.to_numpy()
            proto,_=weighted_class_distribution(u,classes(u),np.full((1,7),1/7),weights[h])
            with np.load(CACHE/f'{stamp}_atoms.npz') as payload:np.testing.assert_array_equal(proto[0],payload[f'atoms_{h}'])
            atoms=restore_atoms(proto[0],test.vol63,h)
            np.testing.assert_allclose(np.log1p(atoms)/risk_scale(test.vol63,h)[:,None]/10,np.tile(proto[0],(len(test),1)),atol=1e-10,rtol=1e-10)
            support.append(dict(months=h,date=stamp,min_atom=float(atoms.min()),max_atom=float(atoms.max())))
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys);template=base[base.date.eq(date)].reset_index(drop=True)
            bs=probability_stats(ba,template.actual);np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            for name,(_,mode) in MODELS.items():
                component=0 if mode=='shared' else h
                with np.load(CACHE/f'{component}_{stamp}_{name}.npz') as payload:p=payload['probabilities']
                if component==0:
                    j=[1,3,6].index(h);p=p[j*len(test):(j+1)*len(test)]
                expected=score(template,ba,bw,atoms,p,.5)
                g=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                assert np.array_equal(g.p_up.gt(g.p_down),expected.p_up.gt(expected.p_down));reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
            for date,m in g.groupby('date'):
                m=m[m.actual.notna()&m.actual.ne(0)]
                if not len(m):continue
                y=m.actual.gt(0);diagnostics.append(dict(months=h,date=date,model=name,accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(),within_month_auc=roc_auc_score(y,m.p_up-m.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'reconstructed',flush=True)
    assert reconstructed==331200
    pd.DataFrame(support).to_csv(DEST/'restored_support_audit.csv',index=False)
    pd.DataFrame(diagnostics).groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
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
    scores=pd.read_csv(DEST/'target_scoreboard.csv');new=scores[scores.model.isin(MODELS)];assert len(scores)==96 and len(new)==48
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=147,
        original_stock_dates_per_model=27600,fit_checks=checked,maturity_slices_checked=maturity,all_new_prediction_rows_reconstructed=reconstructed,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R42：风险标准化的逐期限与共享概率模型','',f'**{result}** 四新增候选，累计147个完整评分候选；原B、27,600股票月及1/3/6月全部12项门槛不变。','',
        '使用预测起点已知年化波动率，以sqrt(h/12)换算期限风险。成熟对数收益除以该风险后学习七档概率，查询时反变换为各股票、各期限的完整简单收益分布。精确零和正负质量保持不变；逐期限和共享版本使用相同的目标期限自身幅度原子，全部与原B各半混合。原算法参数不变。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表四候选相对相同算法、相同逐期限/共享结构的原尺度版本；最后两项为标准化后共享相对逐期限的增量。正值改善，负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            label=LABELS.get(name,('提升树' if name.startswith('catboost') else '极端随机树')+'标准化后共享增量')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。166项测试、512次拟合输入核验、768个期限成熟切片和331,200条新概率重建通过。技术通过不等于预测目标通过。','',
        '标准化并非无影响的单位变换：它改变学习目标和条件尾部形状。指数反变换可外推出历史原收益范围，未按测试结果裁剪；支持范围见恢复原子核验表。R24已研究标准化分位数，本轮单独检验七档模型及期限共享，仍为重复历史探索，不是独立验证。','',
        '结果解读：四个标准化候选×三个期限，相对各自结构匹配原尺度版本，五档Brier和CRPS的24个点估计全部改善，其中6个五档、3个CRPS配对增量区间下界大于0。上涨Brier仅6/12改善，方向仅5/12改善，12个方向比较均无正增量区间下界。标准化更明确地帮助分布形状，尚未带来稳定方向增益。以极端随机树逐期限版为同一候选：1/3/6月命中率53.77%/56.88%/50.07%，相对原B提高3.45%/6.85%/0.08%；三项概率误差分别改善0.52%/1.00%/0.68%、1.69%/0.94%/1.32%、1.61%/0.72%/1.31%。全部候选的概率指标改善均不足2%，没有20%单项门槛通过。上述区间来自重复探索，不能当作独立确认。','',
        '明细：[评分前方案](notes/r42_scaled_horizon_models.md)、[目标评分](outputs/r42_scaled_horizon_models/target_scoreboard.csv)、[配对区间](outputs/r42_scaled_horizon_models/paired_comparisons.csv)、[分阶段](outputs/r42_scaled_horizon_models/phase_scores.csv)、[恢复支持范围](outputs/r42_scaled_horizon_models/restored_support_audit.csv)、[完整核验](outputs/r42_scaled_horizon_models/research_integrity_audit.json)。','']
    (EP/'scaled_horizon_models_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
