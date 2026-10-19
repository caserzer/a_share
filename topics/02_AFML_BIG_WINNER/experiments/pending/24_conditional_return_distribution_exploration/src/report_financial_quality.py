"""R31 financial availability, matched ablation and probability reconstruction."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_financial_quality import DEST,PANEL,SOURCE,META,BASIC,QUALITY,CHANGES
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from run_financial_quality_models import CACHE,CONTROL,MODELS,REFERENCES,raw_reference
from conditional_forests import training_impute
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'catboost_reference':'提升树对照','extra_reference':'极端随机树对照'}
for family,label in [('catboost','提升树'),('extra','极端随机树')]:
    LABELS.update({f'{family}_basic':label+'加基础财报',f'{family}_levels':label+'加财报质量',f'{family}_changes':label+'再加年度变化'})
PAIRS=[]
for family in ['catboost','extra']:
    for new,old in [('basic','reference'),('levels','basic'),('changes','levels'),('changes','reference')]:
        PAIRS.append((f'{family}_{new}',f'{family}_{old}',f'{family}_{new}_vs_{old}'))


def run():
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert digest(PANEL)==fa['feature_sha256']==spec['feature_sha256']
    assert digest(SOURCE)==fa['source_sha256']
    assert digest(EP/'notes/r31_financial_quality.md')==fa['plan_sha256']==spec['plan_sha256']
    for r in fa['receipts']:assert digest(Path(r['path']))==r['sha256']
    for r in json.loads((DEST/'reference_raw_receipts.json').read_text()):assert digest(Path(r['path']))==r['sha256']
    panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE)
    pd.testing.assert_frame_equal(panel[original.columns],original)
    fresh=(panel.date-panel.financial_report_date).dt.days.le(456)
    assert panel.loc[fresh,'fq_available_date'].lt(panel.loc[fresh,'date']).all()
    assert panel.loc[~fresh,META+BASIC+QUALITY].isna().all().all()
    paired=panel.fq_prior_available.eq(1)
    assert panel.loc[paired,'fq_prior_available_date'].lt(panel.loc[paired,'date']).all()
    assert (panel.loc[paired,'fq_prior_report_date']+pd.DateOffset(years=1)).eq(panel.loc[paired,'fq_report_date']).all()
    fit=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit)==1152 and not fit.duplicated(['months','date','model']).any() and set(fit.model)==set(MODELS)
    assert fit.groupby(['months','date'])[['training_rows','training_months','last_training_label','test_rows','total_weight']].nunique().eq(1).all().all()
    for (h,date),g in fit.groupby(['months','date']):
        date=pd.Timestamp(date);train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)]
        w=observation_weights(train,date,True,None);r=g.iloc[0]
        assert len(train)==r.training_rows and train.date.nunique()==r.training_months
        assert train[f'end_{h}'].max()==pd.Timestamp(r.last_training_label)<date
        np.testing.assert_allclose(g.total_weight,w.sum())
        y=train[f'y_{h}'].to_numpy();labels=classes(y)
        expected_atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),w)
        for _,item in g.iterrows():
            family,added=MODELS[item.model];path=CACHE/f'{h}_{date.date()}_{item.model}.npz'
            assert digest(path)==item.cache_sha256
            with np.load(path) as payload:
                np.testing.assert_array_equal(payload['class_atoms'],expected_atoms[0])
                p=payload['probabilities'];assert np.isfinite(p).all() and (p>=0).all()
                np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                if family=='extra':
                    tx,qx,med=training_impute(train[CONTROL+added],test[CONTROL+added])
                    np.testing.assert_array_equal(payload['medians'],med)
                    assert hashlib.sha256(tx.tobytes()).hexdigest()==item.imputed_train_sha256
                    assert hashlib.sha256(qx.tobytes()).hexdigest()==item.imputed_test_sha256
                else:assert payload['medians'].size==0
    contract=json.loads((TARGET/'target_contract.json').read_text());pred_receipts=[];reconstructed=0;diagnostics=[];reliability=[];calibration=[];precision_details=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        for name,(folder,model) in REFERENCES.items():
            source=folder/f'predictions_{h}m.parquet';sr=next(r for r in spec['references'][name]['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
            assert digest(source)==sr['sha256']
            old=pd.read_parquet(source);old=old[old.model.eq(model)].reset_index(drop=True)
            current=data[data.model.eq(name)].reset_index(drop=True)
            pd.testing.assert_frame_equal(current[['date','instrument']],old[['date','instrument']])
            for column in ['p_up','p_down','brier','multiclass_brier','crps','q05','q50','q95']:
                if column in current:
                    precision_details.append(dict(months=h,model=name,field=column,
                        max_absolute_change=float((current[column]-old[column]).abs().max()),
                        monthly_mean_change=float((current[column]-old[column]).groupby(current.date).mean().mean())))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600
            np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,dated in data.groupby('date'):
            keys=pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet');ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            original_b=base[base.date.eq(date)].reset_index(drop=True)
            bs=probability_stats(ba,original_b.actual)
            np.testing.assert_allclose(bs,original_b[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            for name in LABELS:
                g=dated[dated.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                with np.load(CACHE/f'{h}_{date.date()}_{name}.npz') as payload:
                    a=np.tile(payload['class_atoms'],(len(g),1));w=np.repeat(payload['probabilities']/32,32,axis=1)
                if name in REFERENCES:
                    q,p,_=raw_reference(name,h,date,keys)
                    np.testing.assert_array_equal(a,np.tile(q,(len(g),1)))
                    np.testing.assert_array_equal(w,np.repeat(p/32,32,axis=1))
                aa,ww=combine_distributions([(ba,bw),(a,w)],[.5,.5]);expected=weighted_stats(aa,ww,g.actual)
                np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True);reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
        for (name,date),g in pd.concat([data,base]).groupby(['model','date']):
            g=g[g.actual.notna()&g.actual.ne(0)]
            if not len(g):continue
            y=g.actual.gt(0);diagnostics.append(dict(months=h,date=date,model=name,accuracy=((g.p_up>g.p_down)==y).mean(),
                up_call_rate=(g.p_up>g.p_down).mean(),always_down=(~y).mean(),
                within_month_auc=roc_auc_score(y,g.p_up-g.p_down) if y.nunique()==2 else np.nan))
        pred_receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)))
    pd.DataFrame(precision_details).to_csv(DEST/'reference_precision_details.csv',index=False)
    pd.DataFrame(diagnostics).groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly_scores=pd.read_csv(DEST/'monthly_scores.csv');pairs=[]
    for h,g in monthly_scores.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,comparison in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                pairs.append(dict(months=h,comparison=comparison,metric=metric,relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,
                    improvement_lower95=lo,improvement_upper95=hi))
    paired=pd.DataFrame(pairs);paired.to_csv(DEST/'paired_comparisons.csv',index=False)
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==96
    new=score[score.model.isin(MODELS)];assert len(new)==72
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=6,
        original_stock_dates_per_model=27600,all_candidate_and_reference_rows_reconstructed=reconstructed,
        all_source_hashes_and_prefix_features_checked=True,all_training_maturity_and_imputation_checked=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=pred_receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '有点估计达标候选，仍需完整验证审核。'
    coverage=pd.read_csv(DEST/'coverage.csv',index_col=0)
    lines=['# R31：财报质量与同季度变化消融','',f'**{result}** 本轮6个新增候选及2个匹配对照，累计93个候选。原B、27,600股票月与1/3/6个月全部12项门槛不变。','',
        '完整财报输入的极端随机树命中率，在1/3/6月分别为52.44%/56.94%/49.06%，对应同算法无财报对照为52.78%/56.89%/49.65%。3月仅增加约0.05个百分点，三项概率误差略差，且成对方向增益区间跨零；1月和6月方向表现下降。六候选中6月最高命中率49.92%，仍低于原B50.02%。因此本轮没有稳定的信息增量，不能据此认为已经接近双20%目标。','',
        '在相同38项原输入及两种固定算法上，先加基础财务指标，再加9项财报质量指标，最后加同季度年度变化。模型参数、月份等权、成熟训练行与50%B混合全部固定。本轮使用精确恢复的B，两原对照也统一采用该精度；未修改冻结基线。','',
        f'测试期最新财报在456天窗口内的覆盖为{coverage.loc["evaluation","fq_age_days"]:.2%}；扣非ROE覆盖仅{coverage.loc["evaluation","fq_core_roe"]:.2%}，其年度差值{coverage.loc["evaluation","fq_core_roe_annual_change"]:.2%}。有可用前一年同季度报告的股票月占{fa["evaluation_prior_report_coverage"]:.2%}。缺失保留，所有股票仍参与预测。','',
        '旧面板保留了超过456天的财报，本轮按事前规则把这部分新增输入置缺失；基础组不是对旧财报实验的逐位复刻。质量水平和年度变化的消融使用相同窗口。公告与更新日取较晚者且严格早于预测日，但供应商缓存不是历史原件；现金流/每股净资产等仅为代理，季度累计指标没有冒充年化。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','逐层加入信息的成对消融：','','|期限|比较|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for new_name,old_name,comparison in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(comparison)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[new_name]} 对 {LABELS[old_name]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['','正值改善，负值变差。主表相对原B，增量表相对同算法对照；不能互换或拼接最好指标。技术测试与全量概率重建不证明有效。仍为反复历史探索，保留源数据修订、股票池与行情版本限制，12个月双20%尚未验证。','',
        '来源与时点：[事前方案](notes/r31_financial_quality.md)。明细：[目标评分](outputs/r31_financial_quality/target_scoreboard.csv)、[配对消融](outputs/r31_financial_quality/paired_comparisons.csv)、[分阶段](outputs/r31_financial_quality/phase_scores.csv)、[概率校准](outputs/r31_financial_quality/calibration_summary.csv)、[方向诊断](outputs/r31_financial_quality/direction_diagnostics.csv)、[特征核验](outputs/r31_financial_quality/feature_audit.json)、[预测核验](outputs/r31_financial_quality/research_integrity_audit.json)。','']
    (EP/'financial_quality_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
