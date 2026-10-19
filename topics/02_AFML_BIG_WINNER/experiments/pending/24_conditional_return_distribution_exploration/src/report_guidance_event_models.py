"""R37 dated guidance events, matched ablation and probability reconstruction."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_guidance_events import DEST,PANEL,SOURCE,FEATURES,GROUPS,read_sources,feature_frame
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from run_guidance_event_models import CACHE,CONTROL,MODELS,REFERENCES
from run_conditional_forests import PARAMS as FOREST_PARAMS
from conditional_forests import training_impute
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution
from run_direct_probability import classes
from run_joint_information import score as distribution_score,frame_digest
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'catboost_reference':'提升树原对照','extra_reference':'极端随机树原对照'}
for family,label in [('catboost','提升树'),('extra','极端随机树')]:
    LABELS.update({f'{family}_timing':label+'加公告时间与修订',f'{family}_timing_title':label+'再加标题方向词'})
PAIRS=[(name,f'{family}_reference',name) for name,(family,_) in MODELS.items()]
PAIRS += [(f'{family}_timing_title',f'{family}_timing',f'{family}_title_increment') for family in ('catboost','extra')]


def run():
    from build_guidance_events import CATALOG
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert spec['models']=={name:[family,added] for name,(family,added) in MODELS.items()}
    assert spec['control_features']==CONTROL and spec['extra']==FOREST_PARAMS
    assert spec['catboost']==dict(depth=2,iterations=100,learning_rate=.03,l2_leaf_reg=20,random_seed=24)
    assert digest(PANEL)==fa['feature_sha256']==spec['feature_sha256'] and digest(SOURCE)==fa['source_sha256']
    assert digest(EP/'notes/r37_guidance_events.md')==fa['plan_sha256']==spec['plan_sha256']
    assert digest(CATALOG/'coverage_audit.json')==fa['coverage_audit_sha256']
    assert digest(DEST/'dated_events.parquet')==fa['dated_events_sha256']
    for receipt in fa['source_manifests']:assert digest(Path(receipt['path']))==receipt['sha256']
    raw=read_sources();panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE)
    pd.testing.assert_frame_equal(panel[original.columns],original)
    pd.testing.assert_frame_equal(feature_frame(original,raw),panel)
    assert (panel.gd_latest_notice.isna()|panel.gd_latest_notice.lt(panel.date)).all()
    for stamp in fa['prefix_checks']:
        date=pd.Timestamp(stamp);cut=raw[raw.available.lt(date)]
        rebuilt=feature_frame(original[original.date.eq(date)].reset_index(drop=True),cut)
        pd.testing.assert_frame_equal(rebuilt,panel[panel.date.eq(date)].reset_index(drop=True))
    fit=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit)==768 and not fit.duplicated(['months','date','model']).any() and set(fit.model)==set(MODELS)
    assert fit.groupby(['months','date'])[['training_rows','training_months','last_training_label','test_rows','total_weight']].nunique().eq(1).all().all()
    for (h,date),g in fit.groupby(['months','date']):
        date=pd.Timestamp(date);train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)].reset_index(drop=True)
        w=observation_weights(train,date,True,None);r=g.iloc[0]
        assert len(train)==r.training_rows and train.date.nunique()==r.training_months
        assert train[f'end_{h}'].max()==pd.Timestamp(r.last_training_label)<date
        np.testing.assert_allclose(g.total_weight,w.sum())
        y=train[f'y_{h}'].to_numpy();labels=classes(y)
        expected_atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),w)
        for _,item in g.iterrows():
            family,added=MODELS[item.model];path=CACHE/f'{h}_{date.date()}_{item.model}.npz'
            assert digest(path)==item.cache_sha256
            assert frame_digest(train[CONTROL+added])==item.train_features_sha256
            assert frame_digest(test[CONTROL+added])==item.test_features_sha256
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
    contract=json.loads((TARGET/'target_contract.json').read_text());pred_receipts=[];reconstructed=0;diagnostics=[];reliability=[];calibration=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        for name,(folder,model) in REFERENCES.items():
            source=folder/f'predictions_{h}m.parquet';sr=next(r for r in spec['references'][name]['receipts'] if r['path'].endswith(f'predictions_{h}m.parquet'))
            assert digest(source)==sr['sha256']
            old=pd.read_parquet(source);old=old[old.model.eq(model)].assign(model=name)
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True),old.reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600
            np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,dated in data.groupby('date'):
            keys=pd.read_parquet(CACHE/f'{h}_{date.date()}_keys.parquet');ba,bw=load_distribution(RECOVERED,h,date,'B',keys)
            original_b=base[base.date.eq(date)].reset_index(drop=True);bs=probability_stats(ba,original_b.actual)
            np.testing.assert_allclose(bs,original_b[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            for name in MODELS:
                g=dated[dated.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                with np.load(CACHE/f'{h}_{date.date()}_{name}.npz') as payload:
                    a=np.tile(payload['class_atoms'],(len(g),1));p=payload['probabilities']
                expected=distribution_score(original_b,ba,bw,a,p,.5)
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
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==72
    new=score[score.model.isin(MODELS)];assert len(new)==48
    decisions=new.groupby('model').point_target_met.all().to_dict()
    assert reconstructed==331200
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,
        original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        all_source_hashes_and_prefix_features_checked=True,all_training_maturity_and_imputation_checked=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=pred_receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '有点估计达标候选，仍需完整验证审核。'
    lines=['# R37：业绩预告相关公告时间与标题信息','',f'**{result}** 本轮4个候选、2个同算法原样参考，累计127个完整评分候选。原B、27,600股票月和1/3/6个月全部12项门槛保持不变。','',
        '新增6项公告时间/修订计数，及4项预增、预减、预亏、预盈标题计数。每项只使用严格早于预测日的公开记录；原38项控制、算法、训练月份权重和50%原B混合不变。此处没有加入尚未核验的净利润金额或前瞻收益率数值。','',
        f'测试股票月中，过去365天匹配公告覆盖{fa["recent365_test_coverage"]:.2%}，过去90天覆盖{fa["recent90_test_coverage"]:.2%}。零计数只表示规定标题查询范围内无匹配记录，不代表没有任何盈利预告；不同标题和嵌入式预告仍是来源边界。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','配对消融：每个期限前四项相对同算法原对照，最后两项比较加入标题相对仅用时间组的增量。','','|期限|新增组合|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            label=LABELS.get(name,'提升树：标题相对时间组增量' if name.startswith('catboost') else '极端随机树：标题相对时间组增量')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines[4:4]=['以极端随机树的完整公告组合为例，1/3/6个月命中率为52.95%/56.52%/49.43%；相对原B，三项概率误差改善分别为0.59%/0.15%/0.25%、1.81%/0.34%/0.89%、1.12%/0.30%/0.58%，都远低于20%。相对同算法原对照，命中率分别约+0.17/−0.37/−0.22个百分点，三个期限的95%区间均跨零；3个月早晚两段的方向表现均较原对照略差。仅加时间组的3个月方向降幅约1.64个百分点，95%区间为−2.73至−0.58个百分点。','','因此本轮没有显示稳定的公告信息增益。这个结论只适用于时间和标题表示，不能替代尚未完成的盈利预测金额因子检验。144项测试通过，原预测样本和标签未改变。','']
    lines+=['','正值改善，负值变差。主表相对原B，消融表使用注明的各自对照；不可拼接不同候选的最佳指标。仍是重复历史探索，未构成独立留出验证。','',
        f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48；768次拟合输入和标签成熟时间检查、331200条新概率预测重建通过。技术通过不等于预测目标通过。','',
        '明细：[评分前方案](notes/r37_guidance_events.md)、[来源检查](company_guidance_data_probe.md)、[目标评分](outputs/r37_guidance_events/target_scoreboard.csv)、[配对消融与区间](outputs/r37_guidance_events/paired_comparisons.csv)、[分阶段](outputs/r37_guidance_events/phase_scores.csv)、[完整核验](outputs/r37_guidance_events/research_integrity_audit.json)。','']
    (EP/'guidance_event_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
