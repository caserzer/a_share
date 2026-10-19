"""R43 same-population target evaluation and paired raw-versus-mixed evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP
from build_margin_information import digest
from run_scaled_unmixed import DEST,PLAN,MODELS,SOURCE
from evaluate_improvement_search import evaluate,METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={}
for component in MODELS.values():
    title=('提升树' if component.startswith('catboost') else '极端随机树')+('逐期限' if 'separate' in component else '共享')
    LABELS[component+'_mixed']=title+'混合版';LABELS[component+'_raw']=title+'独立版'
PAIRS=[(name,component+'_mixed',name) for name,component in MODELS.items()]


def run():
    spec=json.loads((DEST/'spec.json').read_text());assert spec['models']==MODELS and digest(PLAN)==spec['plan_sha256']
    assert digest(SOURCE/'research_integrity_audit.json')==spec['source_audit_sha256']
    build=json.loads((DEST/'reconstruction_audit.json').read_text());assert build['reconstruction_passed']
    assert build['source_fit_cache_hashes_checked']==512 and build['new_raw_rows_reconstructed']==build['frozen_mixed_rows_reconstructed']==331200
    for r in json.loads((DEST/'reused_source_receipts.json').read_text()):assert digest(Path(r['path']))==r['sha256']
    diagnostics=[];reliability=[];calibration=[]
    for item in json.loads((TARGET/'target_contract.json').read_text())['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')];path=DEST/f'predictions_{h}m.parquet'
        r=next(r for r in build['receipts'] if r['path'].endswith(path.name));assert digest(path)==r['sha256']
        data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        oldpath=SOURCE/f'predictions_{h}m.parquet';old=pd.read_parquet(oldpath)
        for component in MODELS.values():
            pd.testing.assert_frame_equal(data[data.model.eq(component+'_mixed')].reset_index(drop=True),
                old[old.model.eq(component)].assign(model=component+'_mixed').reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
            for date,m in g.groupby('date'):
                m=m[m.actual.notna()&m.actual.ne(0)]
                if not len(m):continue
                y=m.actual.gt(0);diagnostics.append(dict(months=h,date=date,model=name,accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(),within_month_auc=roc_auc_score(y,m.p_up-m.p_down) if y.nunique()==2 else np.nan))
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
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=151,
        original_stock_dates_per_model=27600,new_fits=0,reused_fit_cache_hashes_checked=512,frozen_mixed_rows_reconstructed=331200,
        all_new_prediction_rows_reconstructed=331200,mixture_probability_and_brier_identity_checks_passed=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=build['receipts'])
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R43：取消标准化分布的基线混合','',f'**{result}** 四个新增候选，累计151个完整评分候选。原B、27,600股票月及1/3/6月全部12项门槛保持不变。','',
        '直接复用R42全部概率组件，比较100%组件分布和原50%B混合分布。没有新拟合、参数搜索或新数据；标准化、风险反变换、类别概率和幅度支持均保持一致。四个混合参考逐值原样保留。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表为各独立版相对同一组件的原混合版，正值改善、负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,_,_ in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[name]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。8项相关测试通过，512份原拟合缓存哈希核对，331,200条旧混合预测和331,200条新独立预测均完成重建；方向/五档概率线性混合及两项Brier平方损失混合恒等式通过。','',
        '取消混合可能放大过度自信及尾部外推，仍按原完整指标验收。本轮沿用此前历史窗口，属于重复探索，不是独立确认；不能将单一期限或指标的最佳值拼接为成功。','',
        '结果解读：取消混合后，四组件×三个期限的五档Brier和CRPS全部24个点估计都差于各自混合版，不能认为原B混合只是拖累。极端随机树共享独立版的6月命中率49.56%→53.66%，提高4.10个百分点，配对95%区间为+1.11至+7.46个百分点；但其五档及CRPS分别变差0.07%/0.13%，同月AUC由0.5177降至0.5147，1/3月命中率也低于混合版。相对原B，该同一独立候选6月命中率仅相对提高7.26%，三项概率误差改善2.32%/0.87%/1.36%，仍远低于20%。局部方向增益不等于完整分布与所有期限共同达标，且这些区间仍属重复历史探索。','',
        '明细：[评分前方案](notes/r43_scaled_unmixed.md)、[目标评分](outputs/r43_scaled_unmixed/target_scoreboard.csv)、[配对区间](outputs/r43_scaled_unmixed/paired_comparisons.csv)、[分阶段](outputs/r43_scaled_unmixed/phase_scores.csv)、[分布重建与恒等式](outputs/r43_scaled_unmixed/reconstruction_audit.json)、[完整核验](outputs/r43_scaled_unmixed/research_integrity_audit.json)。','']
    (EP/'scaled_unmixed_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
