"""R45 reconstruct stronger regularization and matched-alpha ablations."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from run_neural_regularization import DEST,CACHE,PLAN,PANEL,SOURCE,GROUPS,MODELS,REFERENCES,PARAMETERS,array_digest
from neural_probability_models import PARAMS,forward
from regularized_information import WeightedRankDesign,month_weights
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_direct_probability import classes
from run_joint_information import score,frame_digest
from run_prequential_search import load_distribution
from run_four_horizons import probability_stats
from recover_baseline_precision import RECOVERED
from evaluate_improvement_search import evaluate,METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={f'alpha1_{mode}':'alpha=1'+suffix for mode,suffix in [('raw','独立'),('mixed','混合')]}
LABELS.update({f'{group}_{mode}':group.replace('alpha','alpha=')+suffix for group in GROUPS for mode,suffix in [('raw','独立'),('mixed','混合')]})
PAIRS=[(name,'alpha1_'+name.rsplit('_',1)[1],name) for name in MODELS]
PAIRS += [(f'alpha64_{mode}',f'alpha16_{mode}',f'stronger_{mode}') for mode in ['raw','mixed']]
PAIRS += [(f'{group}_raw',f'{group}_mixed',f'{group}_raw_increment') for group in GROUPS]


def run():
    spec=json.loads((DEST/'spec.json').read_text())
    assert spec['models']=={k:list(v) for k,v in MODELS.items()} and spec['groups']==GROUPS and spec['references']==REFERENCES
    assert spec['parameters']==json.loads(json.dumps(PARAMETERS))
    assert digest(PANEL)==spec['feature_sha256'] and digest(PLAN)==spec['plan_sha256']
    assert digest(Path(spec['mlp_source_path']))==spec['mlp_source_sha256']
    original_spec=json.loads((SOURCE/'spec.json').read_text())
    assert original_spec['parameters']==json.loads(json.dumps(PARAMS))
    assert original_spec['feature_sha256']==spec['feature_sha256']
    original_fits=pd.read_csv(SOURCE/'fit_audit.csv')
    panel=pd.read_parquet(PANEL);fits=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fits)==384 and not fits.duplicated(['months','date','group']).any()
    assert fits.n_iter.eq(60).all() and fits.iteration_limit_warnings.isin([0,1]).all()
    contract=json.loads((TARGET/'target_contract.json').read_text());checked=0;reconstructed=0;receipts=[];diagnostics=[];reliability=[];calibration=[];shrinkage=[]
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
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']];stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stem}_keys.parquet'),keys)
            template=base[base.date.eq(date)].reset_index(drop=True);ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            bs=probability_stats(ba,template.actual);np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            train=select_training(panel,h,date,None);w=observation_weights(train,date,True,None);dw=month_weights(train)
            np.testing.assert_allclose(pd.Series(w,index=train.date).groupby(level=0).sum(),len(train)/train.date.nunique())
            np.testing.assert_allclose(pd.Series(dw,index=train.date).groupby(level=0).sum(),1)
            y=train[f'y_{h}'].to_numpy();labels=classes(y);atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),w)
            assert len(train)>=1000 and train.date.nunique()>=18 and set(labels)==set(range(7))
            for group,cols in GROUPS.items():
                r=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))&fits['group'].eq(group)];assert len(r)==1;r=r.iloc[0]
                assert r.alpha==PARAMETERS[group]['alpha']
                assert r.training_rows==len(train) and r.training_months==train.date.nunique() and r.test_rows==len(test)
                assert pd.Timestamp(r.last_training_label)==train[f'end_{h}'].max()<date
                np.testing.assert_allclose(r.total_weight,len(train));assert array_digest(w)==r.weights_sha256
                assert frame_digest(train[cols])==r.train_features_sha256 and frame_digest(test[cols])==r.test_features_sha256
                design=WeightedRankDesign().fit(train[cols],dw);x,z=design.transform(train[cols]),design.transform(test[cols])
                assert x.shape[1]==r.design_columns and array_digest(x)==r.train_design_sha256 and array_digest(z)==r.test_design_sha256
                oldfit=original_fits[original_fits.months.eq(h)&original_fits.date.eq(str(date.date()))&original_fits['group'].eq('control')]
                assert len(oldfit)==1;oldfit=oldfit.iloc[0]
                for key in ['weights_sha256','train_features_sha256','test_features_sha256','train_design_sha256','test_design_sha256']:
                    assert r[key]==oldfit[key]
                oldcache=OUT/'local_cache/r44_neural_probability_models'/f'{stem}_control.npz'
                assert digest(oldcache)==oldfit.cache_sha256
                cp=CACHE/f'{stem}_{group}.npz';assert digest(cp)==r.cache_sha256
                with np.load(cp) as payload:
                    np.testing.assert_array_equal(payload['names'],design.names);np.testing.assert_array_equal(payload['class_atoms'],atoms[0])
                    coefs=[payload[f'w{j}'] for j in range(3)];bias=[payload[f'b{j}'] for j in range(3)]
                    norm=float(sum(np.sum(v*v) for v in coefs));np.testing.assert_allclose(norm,r.weight_squared_norm)
                    with np.load(OUT/'local_cache/r44_neural_probability_models'/f'{stem}_control.npz') as original:
                        original_norm=float(sum(np.sum(original[f'w{j}']**2) for j in range(3)))
                    shrinkage.append(dict(months=h,date=date,group=group,weight_squared_norm=norm,reference_squared_norm=original_norm,ratio=norm/original_norm))
                    assert [a.shape for a in coefs]==[(x.shape[1],32),(32,16),(16,7)]
                    assert [a.shape for a in bias]==[(32,),(16,),(7,)]
                    np.testing.assert_array_equal(payload['classes'],np.arange(7))
                    curve=payload['loss_curve'];assert curve.shape==(60,) and np.isfinite(curve).all()
                    np.testing.assert_allclose([curve[0],curve[-1]],[r.loss_initial,r.loss_final])
                    p=forward(z,coefs,bias,payload['classes'])
                    np.testing.assert_allclose(p,payload['probabilities'],atol=1e-12,rtol=1e-12)
                checked+=1
                for mode,fraction in [('raw',1.),('mixed',.5)]:
                    expected=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),p,fraction)
                    g=data[data.date.eq(date)&data.model.eq(f'{group}_{mode}')].reset_index(drop=True)
                    pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                    np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                    assert np.array_equal(g.p_up.gt(g.p_down),expected.p_up.gt(expected.p_down));reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
            for date,m in g.groupby('date'):
                m=m[m.actual.notna()&m.actual.ne(0)]
                if not len(m):continue
                y=m.actual.gt(0);diagnostics.append(dict(months=h,date=date,model=name,accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(),within_month_auc=roc_auc_score(y,m.p_up-m.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'networks and forecasts rebuilt',flush=True)
    assert checked==384 and reconstructed==331200
    pd.DataFrame(shrinkage).to_csv(DEST/'parameter_shrinkage.csv',index=False)
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
    scores=pd.read_csv(DEST/'target_scoreboard.csv');new=scores[scores.model.isin(MODELS)];assert len(scores)==72 and len(new)==48
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=159,
        original_stock_dates_per_model=27600,network_fit_and_forward_checks=checked,all_new_prediction_rows_reconstructed=reconstructed,
        fixed_budget_iteration_limit_warnings=int(fits.iteration_limit_warnings.sum()),optimization_convergence_claimed=False,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R45：神经网络强正则化','',f'**{result}** 四新增候选，累计159个完整评分候选。原B、27,600股票月及1/3/6月全部12项门槛不变。','',
        '只把原38项输入网络的L2参数alpha从1提高到16、64；其余输入、权重、初始化种子、批设置、结构和60轮预算不变。每种强度保留独立与50%B混合；对照R44相同输入的alpha=1。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表新候选对同混合方式alpha=1；增强正则比较64对16；独立增量比较独立对同alpha混合。正值改善、负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    extra={'stronger_raw':'独立版64对16','stronger_mixed':'混合版64对16','alpha16_raw_increment':'16独立对混合','alpha64_raw_increment':'64独立对混合'}
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS.get(name,extra.get(name,name))}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。384次成熟训练/秩设计/网络前向核验及331,200条新预测重建通过。','',
        f'固定60轮，记录{audit["fixed_budget_iteration_limit_warnings"]}条达到上限的优化警告；没有声称收敛，没有用测试期早停。参数范数另列，不能跨alpha比较含不同惩罚的训练损失。仍是重复历史探索，未建立独立样本外确认。','',
        '结果解读：提高正则后，参数平方范数相对同月R44网络的中位比例分别为11.77%（alpha=16）和0.62%（alpha=64），收缩确实发生。alpha=16独立版3月三项概率误差对R44均改善且配对增量区间下界为正，但对原B仍变差2.73%/1.29%/1.94%；不能把修复较差参考误当成达到目标。该候选1月命中率54.50%（对B相对+4.85%），五档Brier仍变差0.28%。6月四个新增候选命中率均低于50%，alpha=16混合版48.17%，比匹配R44低3.84个百分点，配对区间为[-7.91,-0.49]个百分点。中等正则独立版的月内AUC在3/6月由0.5191/0.5097升至0.5421/0.5425，但这是排序点估计，尚未核验其增量区间，且方向及全分布验收仍失败。更强正则接近消除个体差异，独立版3/6月月内AUC为0.4728/0.4704，不宜据小幅总体命中率波动采纳。171项测试通过。固定60轮优化仍未确认收敛，全部结果仍属重复历史探索。','',
        '明细：[评分前方案](notes/r45_neural_regularization.md)、[目标评分](outputs/r45_neural_regularization/target_scoreboard.csv)、[配对区间](outputs/r45_neural_regularization/paired_comparisons.csv)、[参数收缩](outputs/r45_neural_regularization/parameter_shrinkage.csv)、[分阶段](outputs/r45_neural_regularization/phase_scores.csv)、[训练记录](outputs/r45_neural_regularization/fit_audit.csv)、[完整核验](outputs/r45_neural_regularization/research_integrity_audit.json)。','']
    (EP/'neural_regularization_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
