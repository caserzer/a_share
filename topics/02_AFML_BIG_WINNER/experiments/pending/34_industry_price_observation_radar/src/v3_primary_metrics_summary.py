from pathlib import Path
import pandas as pd, numpy as np, json, hashlib
P=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar')
O=P/'outputs/v3_primary_metrics_20261113'; S=P/'outputs/v3_candidate_evaluation_20261021'; C=P/'outputs/v3_m06_comparison'
inputs={}; sections=['# EP34 早期模型主池：全指标统计\n\n统计日2026-11-13；观察区间2020-01-03至2026-10-16；价格版本截至2026-10-21。主池solo_BALANCED_COMPETE，对照solo_BROAD20_COMPETE。只汇总冻结历史产物，不训练、不修改标签。']
def read(f):
 inputs[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 if f.suffix=='.csv': return pd.read_csv(f)
 if f.suffix=='.parquet': return pd.read_parquet(f)
 return json.loads(f.read_text())
def table(df):
 def val(v):
  if pd.isna(v): return '未知'
  if isinstance(v,(float,np.floating)): return f'{v:.4f}'
  return str(v)
 return '| '+' | '.join(map(str,df.columns))+' |\n|'+'|'.join(['---']*len(df.columns))+'|\n'+'\n'.join('| '+' | '.join(val(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))
def add(title,df,note='',file=None):
 sections.append('## '+title+'\n\n'+note+'\n\n'+table(df))
 if file: df.to_csv(O/file,index=False)
metrics=read(C/'all_grid_metrics.csv'); names=['solo_BALANCED_COMPETE','solo_BROAD20_COMPETE']; selected=metrics[metrics.run_id.isin(names)].copy(); selected.to_csv(O/'all_scalar_metrics.csv',index=False)
selected['timely_rate']=selected.parent_timely/selected.parent_total;selected['late_rate']=selected.parent_late/selected.parent_total;selected['miss_rate']=selected.parent_missed/selected.parent_total
add('覆盖、质量、负担全部标量（原字段）',selected.T.reset_index().rename(columns={'index':'metric',selected.index[0]:'early_model',selected.index[1]:'momentum'}),'所有rate/coverage及pre_gain字段为小数；new_all_lower/upper为把未知全部计错/计对的边界，不是置信区间。新增重复仍计入质量分母。父子不得相加。')
status=[]; timing=[]; work=[]; returns=[]; yearq=[]; sources=[]; interruption=[]
for candidate in ['early_model','momentum']:
 b=S/candidate;s=read(b/'summary.json');q=read(b/'event_quality.parquet');new=q[q.kind.eq('NEW')];w=read(b/'workload.csv');w=w[w.directory_state.eq('SUPPORTED_DIRECTORY')]
 for kind in ['new_status','update_status']:
  n=sum(s[kind].values())
  for k,v in s[kind].items():status.append(dict(candidate=candidate,kind=kind,status=k,count=v,denominator=n,fraction=v/n))
 for typ in ['parent','child']:
  d=read(b/(typ+'_coverage.parquet'));hit=d[d.covered]
  for source,n in hit.source.value_counts().items(): sources.append(dict(candidate=candidate,process=typ,source=source,covered=n,total=len(d)))
  for label,g in [('all_covered',hit),('TIMELY',hit[hit.timing.eq('TIMELY')]),('LATE',hit[hit.timing.eq('LATE')])]:
   for field in ['lag_days','pre_gain','confirmation_delay']:
    a=g[field].dropna();timing.append(dict(candidate=candidate,process=typ,group=label,metric=field,n=len(a),mean=a.mean(),p10=a.quantile(.1),p50=a.median(),p90=a.quantile(.9),p95=a.quantile(.95),maximum=a.max()))
  interruption.append(dict(candidate=candidate,process=typ,total=len(d),right_open=int(d.right_open.sum()),closed=int((~d.right_open).sum()),covered_right_open=int((d.covered&d.right_open).sum())))
 for field in ['NEW','UPDATE','EXIT','pool']:
  a=w[field];work.append(dict(candidate=candidate,metric=field,supported_weeks=len(a),sum=a.sum(),mean=a.mean(),median=a.median(),p90=a.quantile(.9),p95=a.quantile(.95),maximum=a.max(),zero_weeks=int(a.eq(0).sum())))
 for year,g in new.groupby(pd.to_datetime(new.date).dt.year):
  unknown=g.status.str.contains('UNKNOWN');known=g[~unknown];yearq.append(dict(candidate=candidate,alert_year=year,new=len(g),mature=len(known),unknown=int(unknown.sum()),effective=int(known.status.eq('COVERED').sum()),effective_rate=known.status.eq('COVERED').mean()))
 paths=read(b/'all_new_followup.parquet')
 for h,g in paths.groupby('horizon'):
  a=g[g.status.eq('MATURE')]; x=a.excess_return.dropna()
  assert len(g)==s['new_total']
  returns.append(dict(candidate=candidate,horizon=h,total=len(g),mature=len(a),immature=int(g.status.eq('IMMATURE').sum()),gap=int(g.status.eq('DATA_OR_CLASSIFICATION_GAP').sum()),excess_n=len(x),absolute_mean=a.absolute_return.mean(),absolute_median=a.absolute_return.median(),absolute_p10=a.absolute_return.quantile(.1),absolute_p90=a.absolute_return.quantile(.9),excess_mean=x.mean(),excess_median=x.median(),positive_fraction=a.absolute_return.gt(0).mean(),outperform_fraction=x.gt(0).mean(),positive_and_outperform=((a.absolute_return>0)&(a.excess_return>0))[a.excess_return.notna()].mean(),drawdown_mean=a.drawdown.mean(),drawdown_median=a.drawdown.median(),drawdown_p10=a.drawdown.quantile(.1)))
 assert s['parent_covered']+s['parent_missed']==s['parent_total']
 assert s['new_effective']+sum(v for k,v in s['new_status'].items() if k!='COVERED')==s['new_total']
 assert w.NEW.max()<=5 and w.pool.max()<=20
add('完整新增/更新分类',pd.DataFrame(status),'SHORT_OR_UNCONFIRMED_PROCESS是短过程或未确认的合并类别，不能都解释为短暂反弹；UNKNOWN不计失败。UPDATE不并入唯一新增质量分母。','status_counts.csv')
add('新增与更新的首次覆盖贡献',pd.DataFrame(sources),'每个父/子过程分别去重。一次提示可能覆盖父过程并属于其增强，故父子贡献之和不等于有效提示数。','coverage_sources.csv')
add('发现时机与尾部',pd.DataFrame(timing),'lag_days为相对事后参考起点的交易日差；pre_gain为提示前相对参考基准已有涨幅。confirmation_delay为提示后距过程确认的交易日数，max(0,确认日−提示日)，0包含当日或此前已确认。只统计有值的已覆盖过程，不给遗漏过程填零。','timing_distributions.csv')
add('工作负担分布',pd.DataFrame(work),'343个支持周；5个目录未知周排除分布但保留为未知。pool的sum为行业周占用，不是独立机会数量。','workload_distributions.csv')
add('入池后20/60/90/180交易日完整追踪',pd.DataFrame(returns),'每期限均从所有唯一NEW出发；未知/未成熟/价格链缺口不填零。收益等权按提示事件统计，允许同一行业不同入池轮次；不是可交易组合收益。超额=行业简单收益−同期CSI_ALL简单收益。回撤是提示至期限内的最大峰谷回撤，负号越大越差；不扣交易成本。','forward_returns.csv')
add('按提示年份的质量',pd.DataFrame(yearq),'按NEW日期分年，与按过程起点分年的覆盖表分母不同。2026为不完整年度，质量截至数据末日后验评价。','annual_alert_quality.csv')
strata=read(C/'all_grid_strata.csv');strata=strata[strata.run_id.isin(names)].copy();strata['coverage_rate']=strata.covered/strata.processes;strata['timely_rate']=strata.timely/strata.processes;strata['missed']=strata.processes-strata.covered
add('完整年度、此前状态及市场环境分层',strata,'year按过程起点年：2019的170个跨评价起点过程仍在分母中。PRIOR8_DOWN/UP是此前价格状态，不是基本面。市场分层为此前60日方向，不能据此证明行业独立alpha。','strata.csv')
add('过程右边界状态',pd.DataFrame(interruption),'right_open为数据右端过程未闭合，不等于无效；closed也不能直接等同于入池后失败。本汇总不新定义“中断率”。','boundary_states.csv')
paired=read(C/'main_metrics.csv');paired=paired[paired.run_id.isin(['q5_d0_BALANCED_COMPETE','q5_d0_BROAD20_COMPETE'])]
add('同实际新增1615次的主对照',paired,'与独立池1651/1648次的数字分开；主池独立路径不能使用这里的1360作为其覆盖数。','equal_burden.csv')
intervals=read(C/'paired_intervals.csv'); intervals=intervals[intervals.comparison.str.contains('q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE',regex=False)]
add('同新增比较的不确定性',intervals,'差值为模型减动量；rate单位为小数，乘100为百分点。沿用登记13周时间块、2000次重采样；反复研究的历史不是独立样本外。','equal_burden_intervals.csv')
quality=read(C/'actual_quality_coverage_points.csv');quality=quality[quality.run_id.str.contains('BALANCED_COMPETE|BROAD20_COMPETE')]
add('实际质量—覆盖取舍点',quality,'保留所有登记容量档实际点，不在曲线上插值声称精确同质量优势。','quality_coverage_points.csv')
sections.append('## 覆盖与解释边界\n\n目录含574个分类制度内行业身份（SW2014 227、SW2021 347），不能相加解释为574个永续独立行业；既有覆盖审计中99个身份无有效价格。每候选107141条行业日期记录，343个支持期，另5个分类衔接未知周。最新347行业中83数据不足、20在池。\n\n完整分母为4540父过程及458增强子过程，后者单列。现有口径衡量价格观察入口，不衡量订单/盈利改善。高匹配率不等于高覆盖率或提示后上涨率。父覆盖30.40%、及时覆盖17.71%、遗漏69.60%同时保留。\n\n模型强项是相对动量更及时；尚有大量遗漏，增强弱于动量。四期限超额中位数均为负，不应将选择主池解释为证明投资超额收益。\n\n持续性中断严格沿用既有短过程及阶段分类；目前没有一项独立冻结的“提示后中断率”总指标，不能临时挑选跌幅阈值计算后冒称原协议指标。任何进一步细分应单独登记口径。')
(O/'REPORT.md').write_text('\n\n'.join(sections)+'\n')
(O/'receipt.json').write_text(json.dumps({'status':'PASS_ACCOUNTING_AND_CAPACITY','inputs':inputs,'artifacts':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in O.iterdir() if f.is_file() and f.name!='receipt.json'}},ensure_ascii=False,indent=2)+'\n')
print(pd.DataFrame(returns).query('candidate=="early_model"').to_string(index=False));print(pd.DataFrame(work).query('candidate=="early_model"').to_string(index=False));print('report',O/'REPORT.md')
