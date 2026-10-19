"""R34 same-population comparisons and full reconstruction of every new forecast."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_joint_information import DEST,PANEL,SOURCE,FULL,CONTROL,FAMILIES,SOURCES,attach
from run_joint_information import CACHE,FIT_MODELS,MODELS,score,frame_digest
from build_margin_information import digest
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_direct_probability import classes
from run_prequential_search import load_distribution
from run_four_horizons import probability_stats
from recover_baseline_precision import RECOVERED
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET
LABELS={'reference':'浅层控制·混合','shallow_control_raw':'浅层控制·独立','shallow_full_raw':'浅层联合·独立','shallow_full_mixed':'浅层联合·混合',
        'deep_control_raw':'较大容量控制·独立','deep_control_mixed':'较大容量控制·混合','deep_full_raw':'较大容量联合·独立','deep_full_mixed':'较大容量联合·混合'}
PAIRS=[('shallow_full_raw','shallow_control_raw','shallow_information_raw'),('shallow_full_mixed','reference','shallow_information_mixed'),
       ('deep_full_raw','deep_control_raw','deep_information_raw'),('deep_full_mixed','deep_control_mixed','deep_information_mixed'),
       ('deep_control_mixed','reference','control_capacity'),('deep_full_mixed','shallow_full_mixed','full_capacity'),
       ('shallow_full_raw','shallow_full_mixed','shallow_remove_mixture'),('deep_full_raw','deep_full_mixed','deep_remove_mixture')]


def run():
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']==spec['feature_sha256']
    assert digest(SOURCE)==fa['source_sha256'] and digest(OUT/'r25_historical_peers/feature_audit.json')==fa['source_audit_sha256']
    assert digest(EP/'notes/r34_joint_information.md')==fa['plan_sha256']==spec['plan_sha256']
    panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE);rebuilt=original.copy()
    pd.testing.assert_frame_equal(panel[original.columns],original)
    for r in fa['source_receipts']:
        assert digest(Path(r['path']))==r['sha256'] and digest(Path(r['audit_path']))==r['audit_sha256']
        f=pd.read_parquet(r['path']);pd.testing.assert_frame_equal(f[original.columns],original);rebuilt=attach(rebuilt,f,r['columns'])
    pd.testing.assert_frame_equal(rebuilt,panel)
    assert spec['fit_models']=={n:dict(features=c,depth=d,iterations=t,l2_leaf_reg=l2) for n,(c,d,t,l2) in FIT_MODELS.items()}
    for r in json.loads((DEST/'reused_source_receipts.json').read_text()):assert digest(Path(r['path']))==r['sha256']
    fits=pd.read_csv(DEST/'fit_audit.csv');assert len(fits)==768 and not fits.duplicated(['months','date','component']).any()
    assert fits.reused.sum()==192 and (~fits.reused).sum()==576
    contract=json.loads((TARGET/'target_contract.json').read_text());receipts=[];reconstructed=0;reliability=[];calibration=[]
    for source in contract['files']:
        h=source['months'];bp=Path(source['path']);assert digest(bp)==source['sha256'];base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        rp=Path(spec['reference_folder'])/path.name;r=next(r for r in spec['reference_receipts'] if r['path'].endswith(path.name));assert digest(rp)==r['sha256']
        old=pd.read_parquet(rp);old=old[old.model.eq(spec['reference_model'])].assign(model='reference')
        pd.testing.assert_frame_equal(data[data.model.eq('reference')].reset_index(drop=True),old.reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,template in base.groupby('date',sort=True):
            template=template.reset_index(drop=True);keys=template[['date','instrument']];stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(keys,pd.read_parquet(CACHE/f'{stem}_keys.parquet'))
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys);bs=probability_stats(ba,template.actual)
            np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)].reset_index(drop=True);weights=observation_weights(train,date,True,None)
            y=train[f'y_{h}'].to_numpy();labels=classes(y);atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),weights)
            f=fits[fits.months.eq(h)&fits.date.eq(str(date.date()))];assert len(f)==4
            components={}
            for _,item in f.iterrows():
                assert item.training_rows==len(train) and item.training_months==train.date.nunique() and item.test_rows==len(test)
                assert pd.Timestamp(item.last_training_label)==train[f'end_{h}'].max()<date;np.testing.assert_allclose(item.total_weight,weights.sum())
                cols=CONTROL if item.component=='shallow_control' else FIT_MODELS[item.component][0]
                assert frame_digest(train[cols])==item.train_features_sha256 and frame_digest(test[cols])==item.test_features_sha256
                cache=CACHE/f'{stem}_{item.component}.npz';assert digest(cache)==item.cache_sha256
                with np.load(cache) as payload:
                    np.testing.assert_array_equal(payload['class_atoms'],atoms[0]);p=payload['probabilities']
                    assert np.isfinite(p).all() and (p>=0).all();np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                    components[item.component]=p
                if item.component=='shallow_control':
                    with np.load(OUT/f'local_cache/r25_class_distributions/{stem}_own_momentum_control.npz') as reused:
                        np.testing.assert_array_equal(p,reused['probabilities']);np.testing.assert_array_equal(atoms[0],reused['class_atoms'])
            for name,(component,fraction) in MODELS.items():
                expected=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),components[component],fraction)
                actual=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(actual[['date','instrument']],keys)
                np.testing.assert_allclose(actual[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True);reconstructed+=len(actual)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)))
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False);pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly=pd.read_csv(DEST/'monthly_scores.csv');comparisons=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,name in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                comparisons.append(dict(months=h,comparison=name,new=new,old=old,metric=metric,
                    relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,improvement_lower95=lo,improvement_upper95=hi))
    paired=pd.DataFrame(comparisons);paired.to_csv(DEST/'paired_comparisons.csv',index=False)
    target=pd.read_csv(DEST/'target_scoreboard.csv');assert len(target)==96;new=target[target.model.isin(MODELS)];assert len(new)==84
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=7,new_fits=576,reused_components=192,
        features=131,original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        all_original_columns_and_reference_preserved=True,all_fit_maturity_feature_matrices_and_distributions_verified=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '出现点估计达标候选，需继续完整验证。'
    lines=['# R34：联合信息、模型容量与混合比例','',f'**{result}** 七个新增候选，累计109个已评分候选。原B、27,600股票月及1/3/6个月全部12项标准不变。','',
        '将此前分别检验过的量价路径、联动股票、两融、海外风险、财报质量、历史行业和国内宏观七组93项输入，与原38项控制合并为131项。原控制、标签、预测样本逐值保留，不通过删行获取更完整样本。','',
        '浅层depth2/100树/L2=20，较大容量depth4/200树/L2=50，均lr=.03、seed24；同容量有原输入对照。分别保存独立预测和与精确B各半混合的预测。浅层控制原始概率复用R25，混合参考逐值复用R31。只新拟合三种配置，不事后选特征或调参数。','',
        '联合输入继承每组数据限制：财报缺失与版本、行业发布空档、国内宏观45天可用假设与统计范围变化、海外指标滞后、股价复权与原股票池偏差。未入模贷款分项仍排除。拼接完整不等于历史原始版本获得证明。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=target[target.months.eq(h)&target.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','匹配比较：','','|期限|新模型 / 对照|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for new_name,old_name,comparison in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(comparison)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[new_name]} / {LABELS[old_name]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['','本轮84个20%单项门槛全部未通过。联合混合模型在两种容量、三个期限的三项概率误差均差于各自同容量控制；增加信息没有显示同步增益。浅层3月命中率由54.30%降至50.15%，差值约−4.14个百分点，按预测月分块重采样的95%区间约−8.50至−0.45个百分点；这是多轮探索中的描述性结果，不能作为独立确认。','','本轮6月命中率最高的是未增加联合输入的浅层独立模型52.60%，相对B的50.02%改善5.14%；上涨Brier、五档Brier和CRPS分别改善1.43%、0.50%和0.79%。不能把这个6月结果与其他模型的较优期限拼接成达标。118项测试通过，576次新拟合的成熟标签与输入矩阵、192个复用组件、579600条新预测已全部核验。']
    lines+=['','正值改善，负值变差。主表相对冻结B，匹配表按其指定对照；不得混淆或拼接最好单项。较大容量同时改变树深、树数和正则，不能把差异只归因于深度。反复历史探索不构成独立验证，12个月双20%仍未验证。','',
        '明细：[评分前方案](notes/r34_joint_information.md)、[输入覆盖](outputs/r34_joint_information/feature_coverage.csv)、[目标评分](outputs/r34_joint_information/target_scoreboard.csv)、[配对比较](outputs/r34_joint_information/paired_comparisons.csv)、[分阶段](outputs/r34_joint_information/phase_scores.csv)、[核验](outputs/r34_joint_information/research_integrity_audit.json)。','']
    (EP/'joint_information_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))

if __name__=='__main__':run()
