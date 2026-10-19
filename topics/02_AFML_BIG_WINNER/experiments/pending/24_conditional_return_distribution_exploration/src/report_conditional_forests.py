"""R28 matched-distribution audit, scoring and report."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP, OUT
from build_margin_information import digest
from run_conditional_forests import DEST, CACHE, PANEL, SOURCE, REFERENCE, KINDS, MODELS, CONTROL
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from run_prequential_search import load_distribution, combine_distributions
from run_direct_probability import classes, weighted_stats
from conditional_forests import training_impute
from hierarchical_probabilities import stable_sign_scores
from report_earnings_revisions import paired_interval, METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {REFERENCE:'原浅层提升树对照'}
for kind, label in [('rf','随机森林'),('extra','极端随机树')]:
    LABELS.update({f'{kind}_global_mixed':label+'全局/混合', f'{kind}_local_mixed':label+'局部/混合',
                   f'{kind}_local_unmixed':label+'局部/独立'})
PAIRS = [(f'{k}_global_mixed', REFERENCE, f'{k}_vs_boosting') for k in KINDS]
PAIRS += [(f'{k}_local_mixed', f'{k}_global_mixed', f'{k}_local_vs_global') for k in KINDS]
PAIRS += [(f'{k}_local_unmixed', f'{k}_local_mixed', f'{k}_remove_baseline') for k in KINDS]


def run():
    spec = json.loads((DEST/'spec.json').read_text())
    assert digest(PANEL)==spec['panel_sha256']
    assert digest(EP/'notes/r28_conditional_forests.md')==spec['plan_sha256']
    assert digest(Path(spec['sklearn_forest_source']))==spec['sklearn_forest_source_sha256']
    panel=pd.read_parquet(PANEL);fit=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit)==384 and not fit.duplicated(['months','date','kind']).any()
    assert set(fit.kind)==set(KINDS) and fit.leaf_probability_max_error.lt(1e-12).all()
    assert fit.groupby(['months','date'])[['training_rows','training_months','last_training_label','test_rows','total_weight']].nunique().eq(1).all().all()
    for (h,date),group in fit.groupby(['months','date']):
        date=pd.Timestamp(date);train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)]
        weights=observation_weights(train,date,True,None);r=group.iloc[0]
        assert len(train)==r.training_rows and train.date.nunique()==r.training_months
        assert train[f'end_{h}'].max()==pd.Timestamp(r.last_training_label)<date
        np.testing.assert_allclose(group.total_weight,weights.sum())
        tx,qx,medians=training_impute(train[CONTROL],test[CONTROL])
        assert group.imputed_train_sha256.eq(hashlib.sha256(tx.tobytes()).hexdigest()).all()
        assert group.imputed_test_sha256.eq(hashlib.sha256(qx.tobytes()).hexdigest()).all()
        y=train[f'y_{h}'].to_numpy();labels=classes(y)
        expected_global,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),weights)
        for _,item in group.iterrows():
            path=CACHE/f'{h}_{date.date()}_{item.kind}.npz';assert digest(path)==item.cache_sha256
            with np.load(path) as payload:
                p=payload['probabilities'];local=payload['local_atoms']
                np.testing.assert_array_equal(payload['medians'],medians)
                np.testing.assert_array_equal(payload['global_atoms'],expected_global[0])
                np.testing.assert_array_equal(classes(local),np.tile(np.repeat(np.arange(7),32),(len(p),1)))
                assert np.isfinite(local).all() and np.isfinite(p).all() and (p>=0).all()
                np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                assert (payload['effective_n']>=1-1e-10).all() and (payload['effective_n']<=len(train)+1e-10).all()
                for k in range(7):
                    values=y[labels==k];a=local[p[:,k]>0,k*32:(k+1)*32]
                    if a.size:
                        assert len(values)>0 and a.min()>=values.min()-1e-14 and a.max()<=values.max()+1e-14
    contract=json.loads((TARGET/'target_contract.json').read_text())
    receipts=[];reconstructed=0;diagnostics=[];reliability=[];calibration=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path)
        source=SOURCE/f'predictions_{h}m.parquet'
        sr=next(r for r in spec['source_receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
        assert digest(source)==sr['sha256']
        old=pd.read_parquet(source);old=old[old.model.eq('own_momentum_control')].assign(model=REFERENCE)
        pd.testing.assert_frame_equal(data[data.model.eq(REFERENCE)].reset_index(drop=True),old.reset_index(drop=True))
        assert set(data.model)==set(LABELS)
        for name,g in data.groupby('model'):
            joined=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(joined)==len(g)==27600
            np.testing.assert_allclose(joined.actual,joined.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(joined[c],joined[c+'_base'],check_names=False)
        for date,dated in data.groupby('date'):
            keys=pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet')
            ba,bw=load_distribution(OUT/'local_cache/r15_distributions',h,date,'B',keys)
            baseline_sign=np.column_stack([(bw*(ba<0)).sum(axis=1),(bw*(ba==0)).sum(axis=1),(bw*(ba>0)).sum(axis=1)])
            for kind in KINDS:
                with np.load(CACHE/f'{h}_{date.date()}_{kind}.npz') as payload:
                    p=payload['probabilities'];local=payload['local_atoms'];ga=payload['global_atoms']
                sign=np.column_stack([p[:,:3].sum(axis=1),p[:,3],p[:,4:].sum(axis=1)])
                w=np.repeat(p/32,32,axis=1);shared=None
                for name,(k,shape,fraction) in MODELS.items():
                    if k!=kind:continue
                    g=dated[dated.model.eq(name)].reset_index(drop=True)
                    pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                    a=local if shape=='local' else np.tile(ga,(len(p),1))
                    aa,ww=combine_distributions([(ba,bw),(a,w)],[1-fraction,fraction]) if fraction<1 else (a,w)
                    expected=stable_sign_scores(weighted_stats(aa,ww,g.actual),sign,baseline_sign,fraction,g.actual)
                    np.testing.assert_allclose(g[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True)
                    if fraction==.5:
                        marginal=g[['p_up','p_down','p_zero','brier']].to_numpy()
                        if shared is not None:np.testing.assert_array_equal(marginal,shared)
                        shared=marginal
                    reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name))
            calibration.append(dict(months=h,model=name,**summary))
        for (name,date),g in pd.concat([data,base]).groupby(['model','date']):
            g=g[g.actual.notna() & g.actual.ne(0)]
            if not len(g):continue
            y=g.actual.gt(0)
            diagnostics.append(dict(months=h,date=date,model=name,accuracy=((g.p_up>g.p_down)==y).mean(),
                up_call_rate=(g.p_up>g.p_down).mean(),always_down=(~y).mean(),
                within_month_auc=roc_auc_score(y,g.p_up-g.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)))
    pd.DataFrame(diagnostics).groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly=pd.read_csv(DEST/'monthly_scores.csv');pairs=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old,comparison in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();lo,hi=paired_interval(wide[new],wide[old],metric)
                pairs.append(dict(months=h,comparison=comparison,metric=metric,relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,
                    improvement_lower95=lo,improvement_upper95=hi))
    pd.DataFrame(pairs).to_csv(DEST/'paired_comparisons.csv',index=False)
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==84
    new=score[score.model.isin(MODELS)];assert len(new)==72
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=6,
        original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,
        all_training_maturity_and_train_only_imputation_checked=True,shared_direction_marginals_exact=True,
        maximum_leaf_probability_error=float(fit.leaf_probability_max_error.max()),receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '存在点估计达标候选，需要完整验证审核。'
    lines=['# R28：条件分布森林', '',f'**{result}** 六个固定新候选，累计76个候选。固定原B、27,600股票月、1/3/6个月全部12项门槛；反复历史探索不是独立确认。','',
        '原38项输入、相同成熟训练标签和月份权重，测试随机森林与极端随机树。缺失值仅用训练数据填补并加缺失标志；与提升树的原生缺失处理不同。两种森林参数不调优。每种森林比较全局档内幅度/局部幅度与B各半，以及局部分布独立输出。','',
        '局部幅度来自预测股票所在叶节点的成熟样本加权分布，七类各32个分位近似。全局与局部的类别概率相同，因此其命中率和上涨Brier应相同；局部分布检验的是幅度、尾部与CRPS增量，不会凭空增加方向信息。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    phase=pd.read_csv(DEST/'phase_scores.csv')
    early=phase[phase.months.eq(3)&phase.phase.eq('2021_2023')].set_index('model')
    late=phase[phase.months.eq(3)&phase.phase.eq('2024_plus')].set_index('model')
    v=score[score.months.eq(3)&score.model.eq('extra_local_mixed')].set_index('metric')
    interpretation=(f'极端随机树局部混合版本3个月命中率{v.loc["accuracy","baseline"]:.2%}→{v.loc["accuracy","value"]:.2%}'
        f'（相对{v.loc["accuracy","relative_improvement"]:+.2%}），上涨Brier/五档/CRPS分别改善'
        +'/'.join(f'{v.loc[m,"relative_improvement"]:.2%}' for m in METRICS[:3])+'。'
        f'分阶段看，2021—2023年命中率{early.loc["extra_local_mixed","accuracy"]:.2%}，低于B的{early.loc["frozen_B","accuracy"]:.2%}；'
        f'2024年以后为{late.loc["extra_local_mixed","accuracy"]:.2%}，高于B的{late.loc["frozen_B","accuracy"]:.2%}。'
        '改善主要来自后段，不能认定各阶段均有效。局部幅度替换带来的CRPS变化很小，方向增量来自森林类别概率。')
    lines[-2:-2]=[interpretation,'']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','正数表示相对原B改善，负数变差。不能拼接不同模型、期限或市场阶段的最好指标。配对增量另存，全部目标必须由同一模型满足。','',
        '已核验训练内填补、bootstrap权重语义、叶内经验概率与模型输出一致、原样本/标签不变、所有概率与评分缓存重建。局部与全局的方向边际逐值一致。技术核验不代表预测有效；仍有原历史池、报价修订和多轮试验偏差。12个月双20%尚未检验。','',
        '明细：[事前方案](notes/r28_conditional_forests.md)、[目标评分](outputs/r28_conditional_forests/target_scoreboard.csv)、[配对消融](outputs/r28_conditional_forests/paired_comparisons.csv)、[分阶段](outputs/r28_conditional_forests/phase_scores.csv)、[概率校准](outputs/r28_conditional_forests/calibration_summary.csv)、[方向诊断](outputs/r28_conditional_forests/direction_diagnostics.csv)、[核验](outputs/r28_conditional_forests/research_integrity_audit.json)。','']
    (EP/'conditional_forests_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':
    run()
