"""R36 shareholder-count availability, matched ablation and probability reconstruction."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_holder_counts import DEST,PANEL,SOURCE,FEATURES,GROUPS,BOUNDARIES,read_sources,feature_frame
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from run_holder_count_models import CACHE,CONTROL,MODELS,REFERENCES
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
    LABELS.update({f'{family}_level':label+'加户数水平',f'{family}_change':label+'加户数变化',f'{family}_both':label+'加两组'})
PAIRS=[(name,f'{family}_reference',name) for name,(family,_) in MODELS.items()]


def run():
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert spec['models']=={name:[family,added] for name,(family,added) in MODELS.items()}
    assert spec['control_features']==CONTROL and spec['extra']==FOREST_PARAMS
    assert spec['catboost']==dict(depth=2,iterations=100,learning_rate=.03,l2_leaf_reg=20,random_seed=24)
    assert digest(PANEL)==fa['feature_sha256']==spec['feature_sha256']
    assert digest(SOURCE)==fa['source_sha256']
    assert digest(EP/'notes/r36_holder_counts.md')==fa['plan_sha256']==spec['plan_sha256']
    assert digest(DEST/'source_manifest.json')==fa['source_manifest_sha256']
    assert digest(DEST/'availability_audit.json')==fa['availability_audit_sha256']
    assert digest(DEST/'filing_crosschecks.json')==fa['filing_checks_sha256']
    assert digest(BOUNDARIES)==fa['price_boundaries_sha256']
    filings=json.loads((DEST/'filing_crosschecks.json').read_text());assert filings['all_four_counts_match']
    for r in filings['checks']:assert digest(Path(r['pdf_path']))==r['pdf_sha256']
    raw=read_sources();panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE)
    pd.testing.assert_frame_equal(panel[original.columns],original)
    pd.testing.assert_frame_equal(feature_frame(original,raw),panel)
    for prefix in ['current','previous','year']:
        assert (panel[f'hc_{prefix}_notice'].isna()|panel[f'hc_{prefix}_notice'].lt(panel.date)).all()
    for stamp in fa['prefix_checks']:
        date=pd.Timestamp(stamp);cut=raw[raw.HOLD_NOTICE_DATE.lt(date)]
        rebuilt=feature_frame(original[original.date.eq(date)].reset_index(drop=True),cut)
        pd.testing.assert_frame_equal(rebuilt,panel[panel.date.eq(date)].reset_index(drop=True))
    fit=pd.read_csv(DEST/'fit_audit.csv')
    assert len(fit)==1152 and not fit.duplicated(['months','date','model']).any() and set(fit.model)==set(MODELS)
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
    score=pd.read_csv(DEST/'target_scoreboard.csv');assert len(score)==96
    new=score[score.model.isin(MODELS)];assert len(new)==72
    decisions=new.groupby('model').point_target_met.all().to_dict()
    assert reconstructed==496800
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=6,
        original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        all_source_hashes_and_prefix_features_checked=True,all_training_maturity_and_imputation_checked=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=pred_receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '有点估计达标候选，仍需完整验证审核。'
    lines=['# R36：股东户数水平与变化','',f'**{result}** 本轮6个新增候选和2个原样对照，累计123个完整评分候选。原B、27,600股票月与1/3/6个月全部12项标准不变。','',
        '新增户数水平、最近两期与约一年变化及时间信息，共7项。两种固定算法各做水平/变化/合并三组消融；原38项控制逐值保留，月份等权成熟训练、32个全局分位点/类、与精确B各半混合。无户数因素的两种同算法参考逐值复用R31。','',
        '数据按公告日期严格早于预测日对齐，当前统计期超过180天则特征缺失；每个比较值也取自当时独立已公布记录，未直接采用供应商附带的前期值。原预测样本全部保留，未将来源无记录解释成户数为零。户数不等于持仓集中度或机构资金流。','',
        '原1242只股票中1216只股票有历史记录，26只来源明确无记录；公告早于统计日的记录保守排除。两份官方年报四个户数数值匹配，部分供应商日期比年报实际出现该数字更晚；保留较晚日期，不凭零散抽核倒填，历史版本仍未完整认证。','',
        f'输入检查发现年度比较包含上市前少量股东基数，初始未完成运行已中断隔离，没有计为候选。正式版本要求所有统计日均不早于现有原始行情首个正收盘价日，排除{fa["before_price_history_excluded"]}条更早记录。这是保守行情覆盖边界，并非精确上市日认证。修正后户数水平覆盖{fa["test_feature_coverage"]["hc_log_count"]:.2%}、年度变化覆盖{fa["test_feature_coverage"]["hc_year_change"]:.2%}。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    lines[4:4]=['本轮较好的方向候选为极端随机树加户数变化：1/3/6个月命中率53.68%/57.18%/49.84%，原B为51.98%/53.23%/50.02%。3个月相对B的上涨Brier、五档Brier和CRPS改善2.21%/0.44%/1.11%，方向相对提高7.42%，仍远低于20%要求；6个月方向低于B。','','与不加户数的同算法参考相比，3个月命中率56.89%→57.18%，约+0.29个百分点，按预测月分块重采样95%区间约−0.76至+1.78个百分点；1月和6月的命中率增量区间也跨零。1月增益主要来自2024年以后，早段反而略差。因此这里只观察到小幅点估计变化，尚未证明稳定的信息增量。127项测试通过，输入修正未改变任何原股票月或标签。','']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','相对同算法原对照的信息增量：','','|期限|新增组合|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name in MODELS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[name]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['','正值改善，负值变差。主表相对原B，增量表相对同算法参考；不得互换或拼接最好指标。技术核验和输入覆盖均不能代替预测有效性。仍为反复历史探索，继承源版本、股票池和行情限制；12个月双20%未获证明。','',
        f'六候选20%单项门槛通过{audit["passed_point_gates"]}/72；1152次拟合时点、原始输入矩阵与训练内缺失填补核验完成，全部496800条新预测重建通过。','',
        '明细：[评分前方案](notes/r36_holder_counts.md)、[来源与覆盖](holder_count_data_probe.md)、[特征覆盖](outputs/r36_holder_counts/feature_coverage.csv)、[目标评分](outputs/r36_holder_counts/target_scoreboard.csv)、[配对消融](outputs/r36_holder_counts/paired_comparisons.csv)、[分阶段](outputs/r36_holder_counts/phase_scores.csv)、[方向诊断](outputs/r36_holder_counts/direction_diagnostics.csv)、[完整核验](outputs/r36_holder_counts/research_integrity_audit.json)。','']
    (EP/'holder_count_models_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
