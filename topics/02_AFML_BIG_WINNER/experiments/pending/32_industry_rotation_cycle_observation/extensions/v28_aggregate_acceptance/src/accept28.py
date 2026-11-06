from pathlib import Path
import json,hashlib,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs';CACHE=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def js(path,x):Path(path).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n')
def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'

def run():
 checks=[]
 def ck(name,ok):
  assert bool(ok),name
  checks.append(name)
 previous={}
 for name in ['v27_regime_threshold_review','v24_short_hazard']:
  p=E/name;previous.update(json.loads((p/'outputs/predecessors.json').read_text()));m=json.loads((p/'outputs/manifest.json').read_text())
  previous.update({str(p/f['path']):f['sha256'] for f in m['files']});previous[str(p/'outputs/manifest.json')]=sha(p/'outputs/manifest.json')
 ck('all predecessor files unchanged',all(sha(p)==h for p,h in previous.items()));js(OUT/'predecessors.json',previous)
 refs=json.loads((E/'v27_regime_threshold_review/outputs/frozen_policy.json').read_text())
 ck('original final labels unchanged',sha(CACHE/'stage_b_labels.parquet')==refs['labels_sha256']);ck('original phases unchanged',sha(CACHE/'daily_phases.parquet')==refs['phases_sha256'])
 index_path=CACHE/'CSI_ALL.parquet';cfg=json.loads((E/'v26_market_regime_filter/outputs/frozen_candidates.json').read_text());ck('original market prices unchanged',sha(index_path)==cfg['index_sha256'])
 prices=pd.read_parquet(index_path).close;market=prices/prices.shift(126)-1
 labels=pd.read_parquet(CACHE/'stage_b_labels.parquet');phases=pd.read_parquet(CACHE/'daily_phases.parquet').set_index('phase_id').start_date
 receipts={name:{t['task']:t for t in json.loads((E/version/'outputs/prediction_receipt.json').read_text())['tasks']} for name,version in [('risk','v12_duration_risk'),('diffusion','v18_conditional_diffusion'),('regime','v26_market_regime_filter')]}
 ck('same 18 tasks in all sources',len(receipts['risk'])==18 and set(receipts['risk'])==set(receipts['diffusion'])==set(receipts['regime']))
 metrics=[];alerts=[];evidence=[]
 for task in receipts['risk']:
  frames={}
  for name,models in [('risk',['risk_tree','risk_blend']),('diffusion',['diffusion_tree']),('regime',['risk_diffusion_min__market126'])]:
   a=receipts[name][task];ck('source prediction hash '+name+' '+task,sha(a['path'])==a['sha256']);frames[name]=pd.read_parquet(a['path'],filters=[('model','in',models)])
  risk=frames['risk'][frames['risk'].model.eq('risk_tree')].reset_index(drop=True)
  diff=frames['diffusion'].set_index('row_id').prob.reindex(risk.row_id).to_numpy();old=frames['risk'][frames['risk'].model.eq('risk_blend')].set_index('row_id').reindex(risk.row_id).reset_index()
  recomputed=np.minimum(risk.prob.to_numpy(),diff)*risk.date.map(market).gt(0).to_numpy()
  saved=frames['regime'].set_index('row_id').prob.reindex(risk.row_id).to_numpy();ck('raw score reconstruction '+task,np.array_equal(recomputed,saved))
  selection=(risk.prob.to_numpy()>=.11)&(diff>=.11)&risk.date.map(market).gt(0).to_numpy()
  ck('direct conjunction and score cutoff equivalent '+task,np.array_equal(selection,recomputed>=.11))
  baseline_rank=old.groupby(['date','level']).prob.rank(method='first',ascending=False);baseline_selection=baseline_rank<=np.ceil(old.groupby(['date','level']).date.transform('size')*.1)
  ck('baseline full-universe ranking reconstructed '+task,np.array_equal(baseline_selection,old.alert))
  for name,select,score in [('accepted',selection,recomputed),('risk_blend_baseline',baseline_selection.to_numpy(),old.prob.to_numpy())]:
   f=risk.drop(columns=['model','prob','alert']).copy();f['selected']=select;f['score']=score
   f=f[f.date.ge('2021-01-01')&f.date.le('2024-09-30')].merge(labels,on=['row_id','threshold','benchmark'],validate='one_to_one')
   f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
   if name=='accepted':
    a=f[f.selected][['row_id','date','era','level','industry_code','frequency','threshold','benchmark','score']].copy();a['market_return126']=a.date.map(market);alerts.append(a)
   for level,g in f.groupby('level'):
    known=g[g.y.notna()];selected=known[known.selected];positive=known[known.y.eq(1)]
    universe=set(positive.event_or_witness_id.dropna());hitdates=positive[positive.selected].groupby('event_or_witness_id').date.min()
    delay=(hitdates-phases.reindex(hitdates.index)).dt.days
    perdate=selected.groupby('date').y.agg(['sum','count']);precision=(perdate['sum']/perdate['count']).mean()
    allalerts=g[g.selected];counts=allalerts.groupby('date').y.agg(total='size',known='count',positive='sum')
    lower=(counts.positive/counts.total).mean();upper=((counts.positive+counts.total-counts.known)/counts.total).mean()
    metrics.append(dict(task=task,frequency=g.frequency.iloc[0],threshold=g.threshold.iloc[0],benchmark=g.benchmark.iloc[0],level=level,model=name,precision=precision,point_recall=selected.y.sum()/len(positive),event_recall=len(hitdates)/len(universe),active_date_fraction=allalerts.date.nunique()/g.date.nunique(),median_delay_days=delay.median(),mean_delay_days=delay.mean(),precision_lower=lower,precision_upper=upper,alerts=len(allalerts),known_alerts=len(selected),unknown_alerts=len(allalerts)-len(selected),positive_rows=len(positive),evaluable_events=len(universe),detected_events=len(hitdates),observations=len(g),known_observations=len(known)))
    for date,row in counts.iterrows():evidence.append(dict(task=task,level=level,model=name,date=date,alerts=int(row.total),known_alerts=int(row.known),true_alerts=int(row.positive)))
  print('independently reconstructed',task,flush=True)
 m=pd.DataFrame(metrics);m.to_csv(OUT/'independent_metrics.csv',index=False);pd.DataFrame(evidence).to_csv(OUT/'daily_alert_counts.csv',index=False)
 pd.concat(alerts,ignore_index=True).to_csv(OUT/'historical_alerts.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 accepted=m[m.model.eq('accepted')];ck('all 36 fine tasks included and defined',len(accepted)==36 and accepted.precision.notna().all())
 ref=pd.read_csv(E/'v27_regime_threshold_review/outputs/metrics.csv').query("policy=='all_p0.11'")
 match=accepted.merge(ref,on=['frequency','threshold','benchmark','level'],suffixes=('_independent','_old'),validate='one_to_one')
 for c in ['precision','point_recall','event_recall','active_date_fraction','median_delay_days','precision_lower','precision_upper','alerts','known_alerts']:
  ck('independent metric match '+c,np.allclose(match[c+'_independent'],match[c+'_old'],equal_nan=True,atol=1e-12,rtol=1e-12))
 base=m[m.model.eq('risk_blend_baseline')];refbase=pd.read_csv(E/'v23_event_weighting/outputs/metrics.csv').query("model=='risk_blend' and policy=='top_0.1'")
 joined=base.merge(refbase,on=['frequency','threshold','benchmark','level'],suffixes=('_independent','_old'),validate='one_to_one')
 for c in ['precision','point_recall','event_recall']:ck('baseline reproduced '+c,np.allclose(joined[c+'_independent'],joined[c+'_old']))
 ck('full evaluation population retained',np.array_equal(accepted.sort_values(['task','level']).observations,base.sort_values(['task','level']).observations))
 ck('same event denominators',np.array_equal(accepted.sort_values(['task','level']).evaluable_events,base.sort_values(['task','level']).evaluable_events))
 fields=['precision','point_recall','event_recall','active_date_fraction','median_delay_days','mean_delay_days','precision_lower','precision_upper']
 summary=m.groupby('model')[fields].mean().reset_index();summary.to_csv(OUT/'independent_summary.csv',index=False)
 selected=summary.set_index('model').loc['accepted'];baseline=summary.set_index('model').loc['risk_blend_baseline']
 ck('precision at least 23.50 percent',selected.precision>=.235);ck('precision at least twice independently reconstructed baseline',selected.precision>=2*baseline.precision)
 ck('event recall at least 41.25 percent',selected.event_recall>=.4125);ck('event recall at least 90 percent of independently reconstructed baseline',selected.event_recall>=.9*baseline.event_recall)
 total=int(accepted.alerts.sum());known=int(accepted.known_alerts.sum());unknown=total-known
 freq=m.groupby(['model','frequency'])[fields].mean().reset_index();freq.to_csv(OUT/'frequency_summary.csv',index=False)
 annual=pd.read_csv(E/'v27_regime_threshold_review/outputs/year_baseline_comparison.csv');annual.to_csv(OUT/'annual_comparison.csv',index=False)
 # Consolidate every evaluated configuration; duplicates are verified, not counted again.
 allframes=[pd.read_csv(E/'v22_precision_goal_audit/outputs/all_candidates.csv')]
 for v in ['v23_event_weighting','v24_short_hazard','v25_event_threshold_extension','v26_market_regime_filter','v27_regime_threshold_review']:allframes.append(pd.read_csv(E/v/'outputs/summary.csv').assign(source_version=v))
 allc=pd.concat(allframes,ignore_index=True)
 for key,g in allc.groupby(['model','policy']):
  if len(g)>1:ck('same prior metrics '+str(key),all(np.allclose(g[c],g.iloc[0][c],equal_nan=True) for c in ['precision','event_recall','point_recall']))
 allc=allc.drop_duplicates(['model','policy']);allc.to_csv(OUT/'all_exploratory_candidates.csv',index=False)
 decision=dict(status='HISTORICAL_AGGREGATE_GOAL_ACHIEVED',selected_model='risk_diffusion_min__market126',score_cutoff=.11,precision=float(selected.precision),precision_multiple=float(selected.precision/baseline.precision),event_recall=float(selected.event_recall),event_recall_retention=float(selected.event_recall/baseline.event_recall),point_recall=float(selected.point_recall),active_date_fraction=float(selected.active_date_fraction),median_delay_task_average=float(selected.median_delay_days),alerts=total,known_alerts=known,unknown_alerts=unknown,unknown_fraction=unknown/total,precision_unknown_lower=float(selected.precision_lower),precision_unknown_upper=float(selected.precision_upper),user_explicitly_accepts_aggregate_gate=True,all_years_passed=False,all_frequencies_passed=False,strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING',production_deployed=False,exploratory_model_count=int(allc.model.nunique()),exploratory_config_count=len(allc),code_sha256=sha(__file__),contract_sha256=sha(ROOT/'acceptance_contract.md'))
 js(OUT/'decision.json',decision)
 txt='''# EP32：precision翻倍目标的历史汇总验收

**按用户明确确认的汇总门槛，历史研究目标达成。** 最终方法的precision为24.65%，是原11.75%的2.10倍；周期recall为44.39%，保留原45.83%的96.86%，高于41.25%下限。以下结果从原风险树、扩散树预测和原始指数价格独立重建，并逐任务复现V27，不调用此前评分函数。

## 固定选取方式

每个原有周/双周/月观察日，在全部可用二级/三级行业中选择同时满足以下条件的行业：

1. V12风险树分数≥0.11。
2. V18扩散树分数≥0.11。
3. 中证全指当日收盘相对126个交易日前上涨。

两个模型均使用原在线早期状态过滤，按季度只用当时成熟标签训练。原风险树使用27项状态/风险变量，扩散树在此基础上加11项龙头/同业价格扩散变量。所有符合条件行业入选，**不再固定取前10%**；市场条件不满足时不发出信号。三种转折阈值、双基准仍分别重放和评价，未只挑表现最好的行业或任务。

原假设是较稳定的行业早期趋势同时表现出风险尺度与同业扩散支持，且中期市场背景相对有利。这里仅证明历史选择指标满足汇总目标，没有证明基本面因果或盈利景气。

## 同口径独立复算

'''+md(summary[['model','precision','point_recall','event_recall','active_date_fraction','median_delay_days']])+'''

precision为每个任务中已知报警的日期平均命中率，再对36项频率/阈值/基准/层级任务等权平均；时点recall为已选正例时点/全部已知正例时点；周期recall为至少命中一次的周期/原全部可评价周期。原全部观察和周期分母保持一致，没有只在强市场日期中评价recall。

延迟为成功检出周期首次入选日距事后起点低点的自然日数。表中延迟是各任务中位数的平均，不是全部周期合并中位数。它从37.88天增至46.75天。

## 用户明确保留的局限

- 时点recall从20.35%降至14.44%；周期recall是本次主验收指标，不能把二者混用。
- 有信号日期约27.45%，原固定前10%方案为100%。更高precision伴随更少报警日期。
- 2023年周期recall从47.00%降至18.57%，年度表现并不稳定。2022、2024也存在召回退步。
- 周度precision22.27%未单独达到23.50%；双周23.77%、月度27.91%。这次达成的是用户接受的总体门槛，不是每个频率各自达标。

逐频率结果：

'''+md(freq[['model','frequency','precision','point_recall','event_recall','active_date_fraction']])+ '\n逐年对照：\n\n'+md(annual)+f'''

## 未知结果与适用边界

共{total:,}条历史报警，{known:,}条结果已知，{unknown:,}条未知，计数口径未知占{unknown/total:.2%}。precision24.65%基于已知结果，未知未被填成负例或正例。将未知全部设为负/正作敏感性分析时，全部有报警日期的precision界限为{selected.precision_lower:.2%}—{selected.precision_upper:.2%}；这是未知结果界限，不是统计置信区间，且包含原已知标签precision中无定义的报警日期。

底层历史从2017年开始，主评价为2021年至2024年9月并统一24个月跟踪；2021分类断点导致标签覆盖低。全历史已多次用于探索，累计{len(allc)}项不同模型/政策配置（{allc.model.nunique()}个分数模型），不能把最终阈值视作独立验证结果。所有失败与重复控制校验均保留。

严格PIT仍BLOCKED_DATA；独立前瞻验证FORWARD_PENDING；未部署生产，也不是交易指令。用户在知悉年度/频率退步后明确选择按汇总门槛验收，这一选择不改写原分解或未知风险。

[独立逐任务结果](../outputs/independent_metrics.csv) · [不含未来结果的历史名单](../outputs/historical_alerts.csv.gz) · [逐日期计数审计](../outputs/daily_alert_counts.csv) · [全部探索配置](../outputs/all_exploratory_candidates.csv) · [验收状态](../outputs/decision.json) · [用户验收合同](../acceptance_contract.md) · [独立重算实现](../src/accept28.py)
'''
 (ROOT/'reports/accepted_method.md').write_text(txt)
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):ck('link '+link,(p.parent/link).exists())
 ck('predecessors unchanged after independent reconstruction',all(sha(p)==h for p,h in previous.items()))
 js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks,aggregate_goal_achieved=True,strict_PIT='BLOCKED_DATA',forward_validation='FORWARD_PENDING'))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)));print(json.dumps(decision,ensure_ascii=False,indent=2));print('PASS',len(checks),'checks;',len(files),'files')

if __name__=='__main__':run()
