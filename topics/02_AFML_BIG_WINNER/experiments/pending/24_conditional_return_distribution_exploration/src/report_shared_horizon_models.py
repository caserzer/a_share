"""R41 horizon-specific maturity, weight conservation and forecast audit."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP
from build_margin_information import digest
from run_shared_horizon_models import DEST, CACHE, PANEL, PLAN, REFERENCE, MODELS, POOLS, CONTROL, FEATURES, CAT, FOREST_PARAMS, array_digest
from shared_horizon_models import stack_training, pooled_weights, queries
from run_market_time_models import select_training, observation_weights, weighted_class_distribution
from conditional_forests import training_impute
from run_direct_probability import classes
from run_joint_information import frame_digest, score
from run_prequential_search import load_distribution
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from evaluate_improvement_search import evaluate, METRICS
from report_earnings_revisions import paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS = {'catboost_reference':'提升树逐期限原对照', 'extra_reference':'极端随机树逐期限原对照',
    'catboost_h136':'提升树共享1/3/6月', 'catboost_h13612':'提升树再加入12月',
    'extra_h136':'极端随机树共享1/3/6月', 'extra_h13612':'极端随机树再加入12月'}
PAIRS = [(name, family+'_reference', name) for name, (family, _) in MODELS.items()]
PAIRS += [(family+'_h13612', family+'_h136', family+'_12m_increment') for family in ['catboost','extra']]


def run():
    spec=json.loads((DEST/'spec.json').read_text())
    assert spec['models'] == {k:list(v) for k,v in MODELS.items()} and spec['pools'] == POOLS
    assert spec['features'] == FEATURES and spec['catboost'] == CAT and spec['extra'] == FOREST_PARAMS
    assert digest(PANEL) == spec['panel_sha256'] and digest(PLAN) == spec['plan_sha256']
    for r in json.loads((DEST/'source_receipts.json').read_text()): assert digest(Path(r['path'])) == r['sha256']
    panel=pd.read_parquet(PANEL); fits=pd.read_csv(DEST/'fit_audit.csv'); slices=pd.read_csv(DEST/'training_slices.csv')
    assert len(fits)==256 and not fits.duplicated(['date','model']).any()
    assert len(slices)==448 and not slices.duplicated(['date','pool','horizon']).any()
    checked=0
    for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
        test=test.reset_index(drop=True); query=queries(test,CONTROL); stamp=str(date.date())
        mass=len(select_training(panel,3,date,None))
        for pool,horizons in POOLS.items():
            train=stack_training(panel,date,horizons,CONTROL); w=pooled_weights(train,mass)
            assert train.date.lt(date).all() and train.label_end.lt(date).all()
            for h,g in train.groupby('horizon_months'):
                rows=slices[slices.date.eq(stamp)&slices.pool.eq(pool)&slices.horizon.eq(h)]; assert len(rows)==1
                r=rows.iloc[0]
                assert len(g)==r.rows and g.date.nunique()==r.origin_months and g.label_end.max()==pd.Timestamp(r.last_label_end)<date
                assert g.date.nunique()>=(12 if h==12 else 18)
                np.testing.assert_allclose(w[g.index].sum(),r.total_weight)
                np.testing.assert_allclose(r.total_weight,mass/len(horizons))
                monthly=pd.Series(w[g.index],index=g.date).groupby(level=0).sum()
                np.testing.assert_allclose(monthly,monthly.iloc[0])
            for family in ['catboost','extra']:
                name=f'{family}_{pool}'; r=fits[fits.date.eq(stamp)&fits.model.eq(name)];assert len(r)==1;r=r.iloc[0]
                assert len(train)==r.training_rows and len(test)==r.test_rows
                np.testing.assert_allclose(r.total_weight,mass)
                assert frame_digest(train)==r.training_digest and array_digest(w)==r.weights_sha256 and frame_digest(query)==r.test_features_sha256
                path=CACHE/f'{stamp}_{name}.npz';assert digest(path)==r.cache_sha256
                with np.load(path) as payload:
                    p=payload['probabilities']; assert p.shape==(3,len(test),7) and np.isfinite(p).all() and (p>=0).all()
                    np.testing.assert_allclose(p.sum(axis=2),1,atol=1e-12)
                    if family=='extra':
                        tx,qx,med=training_impute(train[FEATURES],query[FEATURES]);np.testing.assert_array_equal(med,payload['medians'])
                        assert array_digest(tx)==r.imputed_train_sha256 and array_digest(qx)==r.imputed_test_sha256
                    else:
                        assert payload['medians'].size==0 and r.imputed_train_sha256==r.imputed_test_sha256=='native_missing'
                checked+=1
    assert checked==256
    contract=json.loads((TARGET/'target_contract.json').read_text()); receipts=[]; reconstructed=0; diagnostics=[]; reliability=[]; calibration=[]
    for item in contract['files']:
        h=item['months'];bp=Path(item['path']);assert digest(bp)==item['sha256']
        base=pd.read_parquet(bp);base=base[base.model.eq('B')]
        rp=REFERENCE/f'predictions_{h}m.parquet';r=next(r for r in spec['reference_receipts'] if r['path'].endswith(rp.name));assert digest(rp)==r['sha256']
        reference=pd.read_parquet(rp);path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        for name in ['catboost_reference','extra_reference']:
            pd.testing.assert_frame_equal(data[data.model.eq(name)].reset_index(drop=True),reference[reference.model.eq(name)].reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,test in panel[panel.date.ge('2021-01-01')].groupby('date',sort=True):
            test=test.reset_index(drop=True);keys=test[['date','instrument']];stamp=str(date.date())
            pd.testing.assert_frame_equal(pd.read_parquet(CACHE/f'{stamp}_keys.parquet'),keys)
            train=select_training(panel,h,date,None);w=observation_weights(train,date,True,None);y=train[f'y_{h}'].to_numpy()
            assert len(train)>=1000 and train.date.nunique()>=18
            atoms,_=weighted_class_distribution(y,classes(y),np.full((1,7),1/7),w)
            with np.load(CACHE/f'{stamp}_atoms.npz') as payload:np.testing.assert_array_equal(atoms[0],payload[f'atoms_{h}'])
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys);template=base[base.date.eq(date)].reset_index(drop=True)
            original=probability_stats(ba,template.actual);np.testing.assert_allclose(original,template[original.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            for name in MODELS:
                with np.load(CACHE/f'{stamp}_{name}.npz') as payload:p=payload['probabilities'][[1,3,6].index(h)]
                expected=score(template,ba,bw,np.tile(atoms[0],(len(test),1)),p,.5)
                g=data[data.date.eq(date)&data.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],keys)
                np.testing.assert_allclose(expected,g[expected.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
                assert np.array_equal(expected.p_up.gt(expected.p_down),g.p_up.gt(g.p_down));reconstructed+=len(g)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
            for date,m in g.groupby('date'):
                m=m[m.actual.notna()&m.actual.ne(0)]
                if not len(m):continue
                y=m.actual.gt(0);diagnostics.append(dict(months=h,date=date,model=name,accuracy=(m.p_up.gt(m.p_down)==y).mean(),
                    up_call_rate=m.p_up.gt(m.p_down).mean(),within_month_auc=roc_auc_score(y,m.p_up-m.p_down) if y.nunique()==2 else np.nan))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)));print(h,'reconstructed',flush=True)
    assert reconstructed==331200
    pd.DataFrame(diagnostics).groupby(['months','model']).mean(numeric_only=True).to_csv(DEST/'direction_diagnostics.csv')
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False)
    pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    evaluate(DEST); monthly=pd.read_csv(DEST/'monthly_scores.csv'); pairs=[]
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
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=4,cumulative_complete_candidates=143,
        original_stock_dates_per_model=27600,pooled_fit_checks=checked,maturity_slices_checked=len(slices),all_new_prediction_rows_reconstructed=reconstructed,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '点估计出现达标候选，尚需完整验证审核。'
    lines=['# R41：跨期限共享概率模型','',f'**{result}** 四个新增候选，累计143个完整评分候选。原B、27,600股票月及1/3/6月全部12项门槛不变。','',
        '两种原算法分别合并1/3/6月成熟标签，或再加入12月成熟标签。原38项控制加期限输入，每个期限内部月份等权，各期限权重相等；两个训练池总权重同为原3月成熟行数。每个标签单独检查到期时间，较短标签成熟不代表较长标签可用。原收益七档阈值及目标期限自身的档内幅度分布不变，四候选均与原B各半混合。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','上表相对原B。下表四候选分别对自身原算法逐期限训练；最后两项是加入12月标签相对只共享1/3/6月的增量。正值改善，负值变差。','',
        '|期限|消融|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for _,_,name in PAIRS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            label=LABELS.get(name,('提升树' if name.startswith('catboost') else '极端随机树')+'12月辅助增量')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['',f'四候选20%单项门槛通过{audit["passed_point_gates"]}/48。162项测试、256次共享拟合输入核验、448个期限成熟切片及331,200条新概率重建通过。技术通过不等于预测目标通过。','',
        '不同期限来自相同股票路径，不能把训练行数增加当成独立样本增加。总权重固定仍不消除标签组成和期限输入占用模型容量的差异。本轮为重复历史探索；12个月只用作辅助训练，不宣称完成12月预测验收。','',
        '结果解读：只共享1/3/6月的极端随机树，在6个月相对同算法逐期限对照，三项概率误差点估计改善0.58%/0.15%/0.30%，配对95%增量区间均为正，但命中率仍约49.65%，几乎没有方向增益。相对原B，其三项误差改善仅1.83%/0.48%/1.00%，方向反而相对下降0.75%。同一模型3个月命中率56.89%→54.88%，下降2.01个百分点，配对区间为−4.55至−0.19个百分点。加入12月标签也没有稳定辅助增益：提升树3月命中率54.65%→51.80%，增量区间为−4.99至−0.97个百分点；两算法6月命中率点估计均下降。跨期限共享存在局部概率增益与方向损失，尚不支持整体替换。','',
        '明细：[评分前方案](notes/r41_shared_horizon_models.md)、[目标评分](outputs/r41_shared_horizon_models/target_scoreboard.csv)、[配对区间](outputs/r41_shared_horizon_models/paired_comparisons.csv)、[分阶段](outputs/r41_shared_horizon_models/phase_scores.csv)、[完整核验](outputs/r41_shared_horizon_models/research_integrity_audit.json)。','']
    (EP/'shared_horizon_models_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
