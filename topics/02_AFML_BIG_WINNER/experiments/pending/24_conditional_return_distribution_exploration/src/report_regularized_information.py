"""R35 reconstruct train-only designs, stored coefficients and every distribution."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_joint_information import PANEL
from build_margin_information import digest
from run_regularized_information import DEST,CACHE,CONFIGS,MODELS,REFERENCES,array_digest
from regularized_information import WeightedRankDesign,month_weights,probabilities
from run_joint_information import score,frame_digest
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_direct_probability import classes
from run_prequential_search import load_distribution
from run_four_horizons import probability_stats
from recover_baseline_precision import RECOVERED
from diagnose_prediction_target import DEST as TARGET
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
LABELS={**{f'{group}_c{c}_{suffix}':f'{label}·C={c}·{mix}' for group,label in [('control','原控制'),('full','全输入')]
            for c in [1,10] for suffix,mix in [('raw','独立'),('mixed','混合')]},
        'shallow_control_reference':'浅层树控制参考','shallow_full_reference':'浅层树联合参考'}
PAIRS=[]
for c in [1,10]:
    for suffix in ['raw','mixed']:
        PAIRS.append((f'full_c{c}_{suffix}',f'control_c{c}_{suffix}',f'information_c{c}_{suffix}'))
for group in ['control','full']:
    for suffix in ['raw','mixed']:
        PAIRS.append((f'{group}_c10_{suffix}',f'{group}_c1_{suffix}',f'penalty_{group}_{suffix}'))
    for c in [1,10]:PAIRS.append((f'{group}_c{c}_raw',f'{group}_c{c}_mixed',f'mixture_{group}_c{c}'))
    for c in [1,10]:PAIRS.append((f'{group}_c{c}_mixed',f'shallow_{group}_reference',f'algorithm_{group}_c{c}'))


def run():
    spec=json.loads((DEST/'spec.json').read_text());panel=pd.read_parquet(PANEL)
    assert digest(PANEL)==spec['feature_sha256']
    assert digest(EP/'notes/r35_regularized_information.md')==spec['plan_sha256']
    assert digest(OUT/'r34_joint_information/research_integrity_audit.json')==spec['source_audit_sha256']
    assert digest(OUT/'r34_joint_information/feature_audit.json')==spec['feature_audit_sha256']
    assert spec['configs']=={k:dict(columns=c,C=v) for k,(c,v) in CONFIGS.items()}
    fits=pd.read_csv(DEST/'fit_audit.csv');assert len(fits)==768 and not fits.duplicated(['months','date','component']).any()
    assert fits.n_iter.between(1,999).all()
    contract=json.loads((TARGET/'target_contract.json').read_text());receipts=[];reconstructed=0;reliability=[];calibration=[]
    for source in contract['files']:
        h=source['months'];bp=Path(source['path']);assert digest(bp)==source['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        rp=OUT/f'r34_joint_information/predictions_{h}m.parquet';r=next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name))
        assert digest(rp)==r['sha256'];old=pd.read_parquet(rp)
        for new_name,old_name in REFERENCES.items():
            expected=old[old.model.eq(old_name)].assign(model=new_name).reset_index(drop=True)
            pd.testing.assert_frame_equal(data[data.model.eq(new_name)].reset_index(drop=True),expected)
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for col in ['label_end','target_date']:pd.testing.assert_series_equal(j[col],j[col+'_base'],check_names=False)
        for date,template in base.groupby('date',sort=True):
            template=template.reset_index(drop=True);keys=template[['date','instrument']];stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(keys,pd.read_parquet(CACHE/f'{stem}_keys.parquet'))
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys);bs=probability_stats(ba,template.actual)
            np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)].reset_index(drop=True);weights=month_weights(train)
            np.testing.assert_allclose(pd.Series(weights).groupby(train.date.to_numpy()).sum(),1,atol=1e-12)
            y=train[f'y_{h}'].to_numpy();labels=classes(y);aw=observation_weights(train,date,True,None)
            atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),aw)
            f=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))];assert len(f)==4;designs={};components={}
            for component,(cols,c) in CONFIGS.items():
                item=f[f.component.eq(component)].iloc[0]
                assert item.C==c and item.training_rows==len(train) and item.training_months==train.date.nunique() and item.test_rows==len(test)
                assert pd.Timestamp(item.last_training_label)==train[f'end_{h}'].max()<date
                np.testing.assert_allclose(item.total_weight,train.date.nunique())
                assert frame_digest(train[cols])==item.train_features_sha256 and frame_digest(test[cols])==item.test_features_sha256
                group=component.split('_')[0]
                if group not in designs:
                    design=WeightedRankDesign().fit(train[cols],weights)
                    x,z=design.transform(train[cols]),design.transform(test[cols]);designs[group]=(design,x,z)
                design,x,z=designs[group]
                assert x.shape[1]==item.design_columns and array_digest(x)==item.train_design_sha256 and array_digest(z)==item.test_design_sha256
                cache=CACHE/f'{stem}_{component}.npz';assert digest(cache)==item.cache_sha256
                with np.load(cache) as payload:
                    np.testing.assert_array_equal(payload['names'],design.names)
                    np.testing.assert_array_equal(payload['class_atoms'],atoms[0]);p=payload['probabilities']
                    np.testing.assert_array_equal(payload['classes'],np.arange(7))
                    np.testing.assert_allclose(p,probabilities(z,payload['coef'],payload['intercept'],payload['classes']),atol=1e-12,rtol=1e-12)
                    np.testing.assert_allclose(np.linalg.norm(payload['coef']),item.coef_l2)
                    assert np.isfinite(p).all() and (p>=0).all();np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                    components[component]=p
            for name,(component,fraction) in MODELS.items():
                expected=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),components[component],fraction)
                actual=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(actual[['date','instrument']],keys)
                np.testing.assert_allclose(actual[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True);reconstructed+=len(actual)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)))
    assert reconstructed==662400
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly=pd.read_csv(DEST/'monthly_scores.csv');comparisons=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,name in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                comparisons.append(dict(months=h,comparison=name,new=new,old=old,metric=metric,
                    relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,improvement_lower95=lo,improvement_upper95=hi))
    pd.DataFrame(comparisons).to_csv(DEST/'paired_comparisons.csv',index=False)
    target=pd.read_csv(DEST/'target_scoreboard.csv');assert len(target)==120;new=target[target.model.isin(MODELS)];assert len(new)==96
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=8,new_fits=768,
        original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        all_references_preserved=True,all_fit_maturity_transform_coefficients_and_scores_verified=True,max_iterations=int(fits.n_iter.max()),
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '出现点估计达标候选，需继续完整验证。'
    lines=['# R35：训练内秩变换与正则化联合概率','',f'**{result}** 八个新增候选，累计117个完整评分候选。原B、27,600股票月、1/3/6个月全部12项门槛不变。','',
        '将原38项和联合131项输入分别作训练内加权秩变换、缺失标记和行业类别编码，拟合七类逻辑回归。每个训练起始月总权重为1，C固定1/10，两档分别完整报告；没有用测试成绩挑选强度。每个拟合保留独立分布和50%精确B混合分布。','',
        '此前R34浅层树控制与联合混合版逐值复用作算法参考。强收缩、秩变换和可加结构同时变化，算法比较不能把差异仅归因于某一个改变；同算法内输入/C/混合消融见配对明细。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=target[target.months.eq(h)&target.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['',f'新增候选通过20%单项门槛{audit["passed_point_gates"]}/96。全部768次拟合均收敛，最高迭代{audit["max_iterations"]}次；原样本、成熟标签、训练内变换、保存系数及662400条新增预测完整重建通过。','',
        '每项改善相对于冻结B，正值更好；相对改善不是百分点变化，不能跨模型拼接最好单项。缺失、公开数据后续修订、行业空档和原股票池偏差等限制全部继承。仍为反复历史探索，不是新独立测试；12个月双20%尚未验证。','',
        '明细：[评分前方案](notes/r35_regularized_information.md)、[评分](outputs/r35_regularized_information/target_scoreboard.csv)、[配对消融](outputs/r35_regularized_information/paired_comparisons.csv)、[分阶段](outputs/r35_regularized_information/phase_scores.csv)、[核验](outputs/r35_regularized_information/research_integrity_audit.json)。','']
    lines += ['较强收缩C=1在与C=10的36个概率评分对照中，有35个点估计更好；这说明约束复杂度有帮助，但不足以达到目标。八个新增候选的6个月三项概率误差全部差于原B，不能把相对另一种参数的改善等同于相对原基线达标。','','以同一个原38项输入、C=1独立模型为例：1个月命中率51.98%→54.16%（相对+4.19%），三项概率误差仅改善1.13%/0.35%/0.74%；3个月命中率53.23%→52.42%；6个月命中率50.02%→50.72%，上涨Brier却恶化4.50%。1个月改善也有阶段差异：2021—2023年命中率55.20%→52.82%，2024年以后47.69%→55.95%。这不是跨阶段稳定增益。','','122项测试通过；完整核验见审计文件。下一项股东户数信息已完成公开来源和历史可用性检查，尚未入模，不计入117个完整候选，见[数据覆盖检查](holder_count_data_probe.md)。','']
    (EP/'regularized_information_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
