"""R32 matched population, published inputs, mature labels and distribution reconstruction."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_historical_industry import DEST,PANEL,SOURCE,POOL,IDENTITY,STATE,identity,peer_state
from download_historical_industry import CACHE as RAW
from run_historical_industry_models import CACHE,MODELS,conditional_atoms,score
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_direct_probability import classes
from run_four_horizons import probability_stats
from run_prequential_search import load_distribution
from recover_baseline_precision import RECOVERED
from build_margin_information import digest
from report_earnings_revisions import METRICS,paired_interval
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET
LABELS={'reference':'无行业对照','industry_identity':'行业身份','industry_state':'再加行业状态','industry_conditional':'再调行业幅度分布'}
PAIRS=[('industry_identity','reference'),('industry_state','industry_identity'),('industry_conditional','industry_state'),('industry_conditional','reference')]

def run():
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed'] and digest(PANEL)==fa['feature_sha256']==spec['feature_sha256']
    assert digest(SOURCE)==fa['source_sha256'] and digest(POOL)==fa['pool_sha256']
    assert digest(EP/'notes/r32_historical_industry.md')==fa['plan_sha256']==spec['plan_sha256']
    assert digest(RAW/'download_manifest.json')==fa['download_manifest_sha256']
    assert digest(DEST/'source_manifest.json')==fa['download_manifest_sha256']
    discovery=json.loads((DEST/'discovery_receipt.json').read_text());assert digest(Path(discovery['script_path']))==discovery['script_sha256']
    download=json.loads((RAW/'download_manifest.json').read_text())
    for r in download:
        assert digest(Path(r['article_path']))==r['article_sha256'] and digest(Path(r['pdf_path']))==r['pdf_sha256']
    for r in fa['release_receipts']:assert digest(Path(r['table_path']))==r['table_sha256']
    panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE);pd.testing.assert_frame_equal(panel[original.columns],original)
    pool=pd.read_parquet(POOL)
    for stamp in fa['prefix_checks']:
        date=pd.Timestamp(stamp);g=pool[pool.date.eq(date)][['date','instrument','mom21','mom63','mom126']]
        cut=[r for r in fa['release_receipts'] if pd.Timestamp(r['published'])<date]
        current=peer_state(identity(g,date,cut));expected=panel[panel.date.eq(date)]
        got=expected[['date','instrument']].merge(current,on=['date','instrument'],validate='one_to_one')
        pd.testing.assert_frame_equal(got[IDENTITY+STATE].reset_index(drop=True),expected[IDENTITY+STATE].reset_index(drop=True),check_dtype=False)
    fit=pd.read_csv(DEST/'fit_audit.csv');assert len(fit)==576 and not fit.duplicated(['months','date','model']).any()
    receipts=[];reconstructed=0;local_rows=0;local_class_cells=0;reliability=[];calibration=[]
    contract=json.loads((TARGET/'target_contract.json').read_text())
    for source in contract['files']:
        h=source['months'];path=Path(source['path']);assert digest(path)==source['sha256']
        base=pd.read_parquet(path);base=base[base.model.eq('B')]
        path=DEST/f'predictions_{h}m.parquet';data=pd.read_parquet(path);assert set(data.model)==set(LABELS)
        refpath=Path(spec['reference_folder'])/path.name;r=next(x for x in spec['reference_receipts'] if x['path'].endswith(path.name));assert digest(refpath)==r['sha256']
        ref=pd.read_parquet(refpath);ref=ref[ref.model.eq('catboost_reference')].assign(model='reference')
        pd.testing.assert_frame_equal(data[data.model.eq('reference')].reset_index(drop=True),ref.reset_index(drop=True))
        for name,g in data.groupby('model'):
            j=g.merge(base[['date','instrument','actual','label_end','target_date']],on=['date','instrument'],suffixes=('','_base'),validate='one_to_one')
            assert len(j)==len(g)==27600;np.testing.assert_allclose(j.actual,j.actual_base,equal_nan=True)
            for c in ['label_end','target_date']:pd.testing.assert_series_equal(j[c],j[c+'_base'],check_names=False)
        for date,template in base.groupby('date',sort=True):
            template=template.reset_index(drop=True);keys=template[['date','instrument']];stem=f'{h}_{date.date()}'
            pd.testing.assert_frame_equal(keys,pd.read_parquet(CACHE/f'{stem}_keys.parquet'))
            ba,bw=load_distribution(RECOVERED,h,date,'B',keys);bs=probability_stats(ba,template.actual)
            np.testing.assert_allclose(bs,template[bs.columns],atol=1e-12,rtol=1e-12,equal_nan=True)
            train=select_training(panel,h,date,None);test=panel[panel.date.eq(date)];weights=observation_weights(train,date,True,None)
            assert train[f'end_{h}'].max()<date;y=train[f'y_{h}'].to_numpy();labels=classes(y)
            global_atoms,_=weighted_class_distribution(y,labels,np.full((1,7),1/7),weights)
            gfit=fit[fit.months.eq(h)&fit.date.eq(str(date.date()))];assert len(gfit)==3
            for _,item in gfit.iterrows():
                assert item.training_rows==len(train) and item.training_months==train.date.nunique() and pd.Timestamp(item.last_training_label)==train[f'end_{h}'].max()
                assert item.test_rows==len(test);np.testing.assert_allclose(item.total_weight,weights.sum())
                cache=CACHE/f'{stem}_{item.model}.npz';assert digest(cache)==item.cache_sha256
                with np.load(cache) as payload:
                    p=payload['probabilities'];assert np.isfinite(p).all() and (p>=0).all();np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
                    if item.model=='industry_conditional':
                        a,counts,used=conditional_atoms(y,labels,weights,train.industry_id,test.industry_id,global_atoms[0])
                        np.testing.assert_array_equal(a,payload['atoms']);np.testing.assert_array_equal(counts,payload['counts']);np.testing.assert_array_equal(used,payload['used'])
                        with np.load(CACHE/f'{stem}_industry_state.npz') as state:np.testing.assert_array_equal(p,state['probabilities'])
                        local_rows+=int(used.any(axis=1).sum());local_class_cells+=int(used.sum())
                    else:
                        np.testing.assert_array_equal(payload['class_atoms'],global_atoms[0]);a=np.tile(global_atoms[0],(len(test),1))
                expected=score(template,ba,bw,a,p);actual=data[data.date.eq(date)&data.model.eq(item.model)].reset_index(drop=True)
                pd.testing.assert_frame_equal(actual[['date','instrument']],keys)
                np.testing.assert_allclose(actual[expected.columns],expected,atol=1e-12,rtol=1e-12,equal_nan=True);reconstructed+=len(actual)
        st=data[data.model.eq('industry_state')].reset_index(drop=True);lo=data[data.model.eq('industry_conditional')].reset_index(drop=True)
        np.testing.assert_array_equal(st[['p_up','p_down','brier']],lo[['p_up','p_down','brier']])
        np.testing.assert_allclose(st.multiclass_brier,lo.multiclass_brier,atol=1e-12,rtol=1e-12,equal_nan=True)
        for name,g in pd.concat([data,base]).groupby('model'):
            cells,summary=probability_reliability(g);reliability.append(cells.assign(months=h,model=name));calibration.append(dict(months=h,model=name,**summary))
        receipts.append(dict(path=str(path.relative_to(EP)),sha256=digest(path)))
    pd.concat(reliability,ignore_index=True).to_csv(DEST/'probability_reliability.csv',index=False);pd.DataFrame(calibration).to_csv(DEST/'calibration_summary.csv',index=False)
    monthly=pd.read_csv(DEST/'monthly_scores.csv');pairs=[]
    for h,g in monthly.groupby('months'):
        for metric in METRICS:
            wide=g.pivot(index='date',columns='model',values=metric)
            for new,old in PAIRS:
                a,b=wide[new].mean(),wide[old].mean();low,high=paired_interval(wide[new],wide[old],metric)
                pairs.append(dict(months=h,new=new,old=old,metric=metric,relative_improvement=a/b-1 if metric=='accuracy' else 1-a/b,improvement_lower95=low,improvement_upper95=high))
    paired=pd.DataFrame(pairs);paired.to_csv(DEST/'paired_comparisons.csv',index=False)
    scores=pd.read_csv(DEST/'target_scoreboard.csv');assert len(scores)==48;new=scores[scores.model.isin(MODELS)];assert len(new)==36
    decisions=new.groupby('model').point_target_met.all().to_dict()
    audit=dict(technical_integrity_passed=True,goal_achieved=False,goal_status='active',new_candidates=3,
        all_new_prediction_rows_reconstructed=reconstructed,all_reference_rows_unchanged=True,all_source_and_prefix_checks_passed=True,
        mature_training_and_local_fallback_verified=True,global_local_direction_identical=True,local_rows=local_rows,local_class_cells=local_class_cells,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '出现点估计达标候选，需继续完整验证。'
    lines=['# R32：历史行业身份、状态与幅度分布','',f'**{result}** 三个新增候选，累计96个已评分候选；原B、原27,600股票月、1/3/6个月全部12项标准不变。','',
        '加入行业身份后，1/3/6月命中率为50.58%/53.61%/50.00%，同算法无行业对照为51.59%/54.30%/49.32%。6月方向略好于同算法对照，但仍未超过原B50.02%；1月和3月下降。追加同行状态未带来同步优势，行业内幅度分布只在1月和3月小幅改善CRPS、6月略差。三候选的36个20%单项门槛全部未通过。','',
        f'19期协会正式发布分类表已解析，逐股代码与独立PDF文本集合一致。测试股票月行业身份覆盖{fa["evaluation_known_fraction"]:.2%}，至少5只同行的63日状态覆盖{fa["evaluation_state_fraction"]:.2%}。超过365天未更新分类的股票月占{fa["evaluation_stale_fraction"]:.2%}，最旧{fa["max_publication_age_days"]}天；所有股票仍参与预测。','',
        '按文章发布日期严格早于预测日使用，分类所属期末不是可用日。2021—2023目录存在空档，明确沿用最后已知分类及年龄；旧/新分类制度分开建身份。旧PDF一处门类代码原图已截断，保留可读大类与股票、门类记未知。迁移网站保存的历史发布材料未独立证明原始时点字节。','',
        '行业身份和行业状态分别检验信息增量；行业幅度版本只替换同业成熟样本的类别内32分位点，类别不足30条回退全局。幅度版本与行业状态版方向概率、Brier和命中判断严格相同，五档Brier仅允许浮点差；因此它只能改变CRPS等档内分布指标。全部仍与精确B各半，模型参数固定。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=scores[scores.months.eq(h)&scores.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','逐层配对消融：','','|期限|新模型 / 对照|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for new,old in PAIRS:
            v=paired[paired.months.eq(h)&paired.new.eq(new)&paired.old.eq(old)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[new]} / {LABELS[old]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['','正值改善，负值变差。仍是同一历史段的反复探索，配对区间不能消除多次尝试的选择偏差。12个月双20%未验证，技术核验不代表预测有效。','',
        '明细：[评分前方案](notes/r32_historical_industry.md)、[数据覆盖](outputs/r32_historical_industry/coverage_by_month.csv)、[目标评分](outputs/r32_historical_industry/target_scoreboard.csv)、[配对比较](outputs/r32_historical_industry/paired_comparisons.csv)、[分阶段](outputs/r32_historical_industry/phase_scores.csv)、[完整核验](outputs/r32_historical_industry/research_integrity_audit.json)。','']
    (EP/'historical_industry_report.md').write_text('\n'.join(lines));print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))

if __name__=='__main__':run()
