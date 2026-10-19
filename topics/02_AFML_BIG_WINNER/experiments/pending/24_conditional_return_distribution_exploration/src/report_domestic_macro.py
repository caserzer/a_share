"""R33 domestic macro availability, matched ablation and probability reconstruction."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from prepare_panel import EP,OUT
from build_margin_information import digest
from build_domestic_macro import DEST,PANEL,SOURCE,MONTHLY,ACTIVITY,CREDIT,LAG_DAYS,read_sources,align,source_checks
from recover_baseline_precision import RECOVERED
from run_four_horizons import probability_stats
from bs4 import BeautifulSoup
from run_domestic_macro_models import CACHE,CONTROL,MODELS,REFERENCES
from conditional_forests import training_impute
from run_market_time_models import select_training,observation_weights,weighted_class_distribution
from run_prequential_search import load_distribution,combine_distributions
from run_direct_probability import classes,weighted_stats
from report_earnings_revisions import paired_interval,METRICS
from report_distribution_shape_models import probability_reliability
from diagnose_prediction_target import DEST as TARGET

LABELS={'catboost_reference':'提升树原对照','extra_reference':'极端随机树原对照'}
for family,label in [('catboost','提升树'),('extra','极端随机树')]:
    LABELS.update({f'{family}_activity':label+'加景气通胀',f'{family}_credit':label+'加融资',f'{family}_both':label+'加两组'})
PAIRS=[(name,f'{family}_reference',name) for name,(family,_) in MODELS.items()]


def run():
    fa=json.loads((DEST/'feature_audit.json').read_text());spec=json.loads((DEST/'spec.json').read_text())
    assert fa['technical_feature_integrity_passed']
    assert digest(PANEL)==fa['feature_sha256']==spec['feature_sha256']
    assert digest(SOURCE)==fa['source_sha256'] and digest(MONTHLY)==fa['monthly_sha256']
    assert digest(EP/'notes/r33_domestic_macro.md')==fa['plan_sha256']==spec['plan_sha256']
    assert digest(DEST/'source_manifest.json')==fa['source_manifest_sha256']
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    for r in manifest['official']:
        assert r['status']=='downloaded' and digest(Path(r['path']))==r['sha256']
    expected_text={'pmi2020':['51.9','55.7'],'pmi2025':['50.1','50.2'],'cpi2025':['0.8'],'ppi2025':['1.9'],
        'money2020':['10.1','19.63'],'money2025':['8.8'],'tsf2020':['34.86','20.03'],'tsf2021':['31.35','19.94']}
    for r in manifest['official']:
        text=BeautifulSoup(Path(r['path']).read_bytes(),'html.parser').get_text(' ',strip=True)
        assert all(token in text for token in expected_text[r['name']])
    raw,coverage=read_sources();assert coverage==fa['source_coverage']
    assert digest(DEST/'official_crosschecks.json')==fa['crosschecks_sha256']
    assert source_checks(raw)==json.loads((DEST/'official_crosschecks.json').read_text())
    panel=pd.read_parquet(PANEL);original=pd.read_parquet(SOURCE)
    pd.testing.assert_frame_equal(panel[original.columns],original)
    monthly=align(raw,sorted(original.date.unique()))
    pd.testing.assert_frame_equal(monthly,pd.read_parquet(MONTHLY))
    pd.testing.assert_frame_equal(original.join(monthly,on='date',validate='many_to_one'),panel)
    assert panel.macro_assumed_available_date.lt(panel.date).all()
    for stamp in fa['prefix_checks']:
        date=pd.Timestamp(stamp);cut=raw[(raw.index.to_timestamp(how='end').normalize()+pd.Timedelta(days=LAG_DAYS))<date]
        pd.testing.assert_frame_equal(align(cut,[date]),monthly.loc[[date]],check_freq=False)
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
                    a=np.tile(payload['class_atoms'],(len(g),1));w=np.repeat(payload['probabilities']/32,32,axis=1)
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
        original_stock_dates_per_model=27600,all_new_prediction_rows_reconstructed=reconstructed,
        all_source_hashes_and_prefix_features_checked=True,all_training_maturity_and_imputation_checked=True,
        passed_point_gates=int(new.point_target_met.sum()),candidates_passing_all_point_gates=decisions,receipts=pred_receipts)
    (DEST/'research_integrity_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    result='尚未达到双20%目标。' if not any(decisions.values()) else '有点估计达标候选，仍需完整验证审核。'
    lines=['# R33：国内景气、通胀与融资信息','',f'**{result}** 本轮6个新增候选和2个原样对照，累计102个已评分候选。原B、27,600股票月与1/3/6个月全部12项标准不变。','',
        '以极端随机树融资组为例，1/3/6月命中率为53.42%/55.18%/48.81%，同算法对照为52.78%/56.89%/49.65%。1月小幅增益主要来自2024年以后，2021—2023年方向略差；3月和6月没有延续。6月所有新增模型的方向与三项概率误差都差于同算法对照，六候选72个20%单项门槛全部未通过。在本轮数据滞后和算法设定下，没有稳定的宏观信息增量。','',
        '新增景气通胀组9项（制造业/非制造业PMI及变化、CPI/PPI同比及变化、PPI减CPI），融资组5项（M2同比及变化、过去12月社融/M2及变化、按下载序列计算的社融年度变化）。分别追加到相同38项原输入上，在原浅层提升树和极端随机树算法上做六组消融，参数固定。所有模型月份等权训练，与精确B各半。两个无新增因素对照逐值复用R31。','',
        f'全部88个历史月份输入完整，未减少原股票样本。统一按统计月末45个日历日后可用，并严格早于预测日；实际观测年龄{fa["min_observation_age"]}—{fa["max_observation_age"]}天。四个真实历史前缀重建通过，12条数值/年度汇总抽查与8份官方原文一致（金额按公布精度）。','',
        'PMI、CPI/PPI和M2为东方财富转发历史表，社融为商务部公开序列。45天滞后是保守假设，不是完整发布日期认证，更不能证明历史原始版本未修订。M1统计口径变更所以未加入；贷款分项扩大核验发现135/136个月在亿元取整精度内一致，2022年6月明显不一致，整体口径尚未完全确认；两个贷款分项都未入模。实际使用的2022—2025年社融年度总量另行核验通过。社融总量包含政府债券，M2不代表股票入市资金。社融年度变化按同一下载序列相除，未重建统计扩围的可比口径，不能称官方可比同比；见口径澄清。','',
        '|期限|模型|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|实际命中率|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name,label in LABELS.items():
            v=score[score.months.eq(h)&score.model.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{label}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+f'|{v.loc["accuracy","value"]:.2%}|')
    lines+=['','相对同算法原对照的信息增量：','','|期限|新增组合|上涨Brier改善|五档Brier改善|CRPS改善|命中率相对改善|','|---|---|---|---|---|---|']
    for h in [1,3,6]:
        for name in MODELS:
            v=paired[paired.months.eq(h)&paired.comparison.eq(name)].set_index('metric')
            lines.append(f'|{h}个月|{LABELS[name]}|'+ '|'.join(f'{v.loc[m,"relative_improvement"]:+.2%}' for m in METRICS)+'|')
    lines+=['','正值改善，负值变差。主表相对原B，增量表相对同算法对照；不能互换或拼接最好指标。技术测试与全量概率重建不证明有效。仍为反复历史探索，保留源数据修订、股票池与行情版本限制，12个月双20%尚未验证。','',
        '来源与时点：[事前方案](notes/r33_domestic_macro.md)、[口径澄清](notes/r33_data_semantics.md)、[来源与官方原文](outputs/r33_domestic_macro/source_manifest.json)。明细：[目标评分](outputs/r33_domestic_macro/target_scoreboard.csv)、[配对消融](outputs/r33_domestic_macro/paired_comparisons.csv)、[分阶段](outputs/r33_domestic_macro/phase_scores.csv)、[概率校准](outputs/r33_domestic_macro/calibration_summary.csv)、[方向诊断](outputs/r33_domestic_macro/direction_diagnostics.csv)、[特征核验](outputs/r33_domestic_macro/feature_audit.json)、[预测核验](outputs/r33_domestic_macro/research_integrity_audit.json)。','']
    (EP/'domestic_macro_report.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in audit.items() if k!='receipts'},indent=2))


if __name__=='__main__':run()
