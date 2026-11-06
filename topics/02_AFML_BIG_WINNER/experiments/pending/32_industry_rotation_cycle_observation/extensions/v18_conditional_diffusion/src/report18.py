from pathlib import Path
import sys,json,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';E=ROOT.parent
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js

def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'
def table(d):
 d=d[['model','policy','precision','point_recall','event_recall','active_date_fraction']].copy()
 for c in ['precision','point_recall','event_recall','active_date_fraction']:d[c]=d[c].map(lambda x:f'{x:.2%}')
 return md(d)

def run():
 s=pd.read_csv(OUT/'summary.csv');freq=pd.read_csv(OUT/'frequency_summary.csv');years=pd.read_csv(OUT/'annual_summary.csv')
 new=['capacity_tree','diffusion_tree','diffusion_blend'];best=s[s.event_recall.ge(.4125)&s.tasks.eq(s.precision_defined_tasks)].sort_values('precision',ascending=False).head(8)
 hits=s[s.diagnostic_target_hit];selected=s[s.model.isin(new)&s.policy.isin(['top_0.1','all_p0.15'])]
 strata=pd.read_csv(OUT/'missingness_strata.csv').groupby(['model','diffusion_complete']).brier.mean().reset_index();strata.to_csv(OUT/'missingness_summary.csv',index=False)
 txt='# EP32 V18：早期状态条件下的扩散信息\n\n'
 txt+=f'目标为precision≥23.50%、周期recall≥41.25%。本轮新候选在17项政策中命中目标的组合数：{int(hits.model.isin(new).sum())}。全部结果为已重复使用历史上的探索，不是独立验证。\n\n'
 txt+='两个同容量树分别使用原27项风险/阶段特征，以及加11项龙头/同业扩散特征；第三个模型为扩散树与原risk_blend各50%。参数在生成预测前冻结，没有按本轮指标调参。缺失扩散数据保留NaN，未删除行业。\n\n预定主要观察政策如下：\n\n'+table(selected)
 txt+='\n保留周期召回下限的最高precision网格点（只是诊断候选，未按历史最优部署）：\n\n'+table(best)
 txt+='\n原主要候选及同容量模型的Brier对照（越低越好）：\n\n'+md(s[s.policy.eq('top_0.1')&s.model.isin(['risk_blend','risk_tree']+new)][['model','brier']])
 txt+='\n扩散完整/缺失样本的Brier分别核对，见[分层结果](../outputs/missingness_summary.csv)。缺失程度随年份变化，模型预测增量不能直接解释为经济机制成立。\n\n'
 if len(best):
  r=best.iloc[0];mask=years.model.eq(r.model)&years.policy.eq(r.policy);fmask=freq.model.eq(r.model)&freq.policy.eq(r.policy)
  txt+='最佳保召回网格点的年度与频率结果：\n\n'+md(years[mask][['year','precision','point_recall','event_recall','active_date_fraction']])+'\n'+md(freq[fmask][['frequency','precision','point_recall','event_recall','active_date_fraction']])
 txt+='''
precision是已知报警的日期平均命中率；无报警日期无定义，活跃日期比例独立展示。周期召回始终使用原全部可评价周期作分母，不能随新筛选政策缩小；任务缺失precision不能靠跳过而通过门槛。前10%名单在删除未知标签之前确定，未知不记负例。时点recall另外报告。

主评价仍为2021年至2024年9月统一24个月随访，全二三级行业、周/双周/月度、三阈值、双基准。最新未成熟历史不强行计负。2021分类断点、历史反复探索、严格PIT BLOCKED_DATA及独立前瞻FORWARD_PENDING边界不变。

本轮沿用RD-Agent环境训练固定候选，没有新增LLM搜索。全部旧预测逐任务复核；训练标签成熟日严格早于季度起点；预测文件与训练方案哈希冻结后才开始评分。

[全部政策结果](../outputs/summary.csv) · [逐年](../outputs/annual_summary.csv) · [逐频率](../outputs/frequency_summary.csv) · [数据完整率](../outputs/feature_coverage.csv) · [冻结模型](../outputs/frozen_candidates.json) · [原始验证](../outputs/validation.json)

![Precision与周期Recall](precision_recall.png)
'''
 (ROOT/'reports/conditional_diffusion.md').write_text(txt)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(8,6))
 for model,g in s.groupby('model'):
  ax.scatter(g.precision*100,g.event_recall*100,label=model,s=24,alpha=.75)
 ax.axvline(23.5,color='black',linestyle='--',linewidth=1);ax.axhline(41.25,color='black',linestyle='--',linewidth=1)
 ax.set(xlabel='Precision (%)',ylabel='Event recall (%)',title='EP32: frozen model / selection policy diagnostics',xlim=(0,max(30,s.precision.max()*105)),ylim=(0,100))
 ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.15);fig.tight_layout();fig.savefig(ROOT/'reports/precision_recall.png',dpi=160);plt.close(fig)
 checks=[]
 def ck(name,ok):
  assert bool(ok),name
  checks.append(name)
 prev=json.loads((OUT/'predecessors.json').read_text());ck('all frozen predecessors unchanged',all(sha(p)==h for p,h in prev.items()))
 receipt=json.loads((OUT/'prediction_receipt.json').read_text());ck('all new predictions unchanged',all(sha(t['path'])==t['sha256'] for t in receipt['tasks']))
 original=json.loads((E/'v15_rank_separation/outputs/prediction_receipt.json').read_text())
 source={t['task']:t for t in original['tasks']}
 for t in receipt['tasks']:
  pred=pd.read_parquet(t['path']);ck('finite probability '+t['task'],pred.prob.notna().all() and pred.prob.between(0,1).all())
  ck('ineligible new probability zero '+t['task'],pred.loc[pred.model.isin(new)&pred.state_eligible.eq(0),'prob'].eq(0).all())
  old=pd.read_parquet(source[t['task']]['path'],filters=[('model','in',['rd_selected','rd_gate','risk_tree','risk_blend','rank_hedged'])])
  control=pred[pred.model.isin(old.model.unique())]
  cols=list(old.columns)
  ck('old predictions identical '+t['task'],old[cols].reset_index(drop=True).equals(control[cols].reset_index(drop=True)))
 ck('all quarter training label cutoffs',all(pd.Timestamp(f['latest_training_label'])<pd.Timestamp(f['quarter']) for f in receipt['folds']))
 ck('all 8 models and 17 policies',len(s)==136 and s.model.nunique()==8 and s.policy.nunique()==17)
 ck('original scoring audits pass',json.loads((OUT/'validation.json').read_text())['status']=='PASS')
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):ck('link '+link,(p.parent/link).exists())
 js(OUT/'report_validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),diagnostic_hits=hits[['model','policy']].to_dict('records'),goal_complete=False))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
 print('V18 report PASS',len(checks),'checks',len(files),'files')
 print(best[['model','policy','precision','event_recall']].to_string(index=False))

if __name__=='__main__':run()
