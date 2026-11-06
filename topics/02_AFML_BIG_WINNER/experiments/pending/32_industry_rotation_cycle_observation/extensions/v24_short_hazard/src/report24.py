from pathlib import Path
import sys,json,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js

def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'
def display(d):
 d=d[['model','policy','precision','point_recall','event_recall','active_date_fraction','median_delay_days']].copy()
 for c in ['precision','point_recall','event_recall','active_date_fraction']:d[c]=d[c].map(lambda x:f'{x:.2%}')
 d.median_delay_days=d.median_delay_days.map(lambda x:f'{x:.2f}')
 return md(d)

def run():
 cfg=json.loads((OUT/'frozen_candidates.json').read_text());new=cfg['models'];receipt=json.loads((OUT/'prediction_receipt.json').read_text())
 s=pd.read_csv(OUT/'summary.csv');year=pd.read_csv(OUT/'annual_summary.csv');freq=pd.read_csv(OUT/'frequency_summary.csv')
 hits=s[s.diagnostic_target_hit];best=s[s.event_recall.ge(.4125)&s.tasks.eq(s.precision_defined_tasks)].sort_values('precision',ascending=False).head(10)
 selected=s[s.model.isin(new)&s.policy.isin(['top_0.1','all_p0.15'])]
 if 'v20_' in ROOT.name:
  title='V20：持续确认与模型一致性';desc='固定过去14/28/42自然日分数中位数、在线已确认上行状态，以及风险树/扩散树一致性；不重新训练。多期确认只用截至当日的已保存预测，4110组前缀一致性检查通过。所得数值是选择分数，不保证已校准为真实概率。'
 elif 'v21_' in ROOT.name:
  title='V21：中长期趋势与市场状态';desc='固定补充17项中长期行业与市场特征，与原27项风险/阶段特征合用。树参数与V18容量对照相同；另与扩散树作50%融合。市场滚动特征通过两基准前缀一致性检查；同日同行汇总先去重复频率/阈值。两次训练前技术失败及修复完整保留在attempts，未依据结果修改参数。'
 else:
  title='V24：较快成熟的阶段失效风险';desc='最终景气标签保持不变；新增辅助模型预测候选低点在21/63个有效交易观察日内被替换或阶段结束的风险，正负例统一在窗口末成熟。以冻结risk_diffusion_min为基底作三种固定风险折减；所得为启发式选择分数，不是经独立校准的存活概率。'
 txt='# EP32 '+title+'\n\n目标为precision≥23.50%、周期recall≥41.25%。新候选命中两项目标的政策组合数：'+str(int(hits.model.isin(new).sum()))+'。这是重复使用历史的探索结果，不能作为独立确认。\n\n'+desc+'\n\n预定主要观察政策：\n\n'+display(selected)
 txt+='\n保留周期召回下限的最高precision网格点（诊断比较，不代表择优部署）：\n\n'+display(best)
 if len(best):
  r=best.iloc[0];yy=year[year.model.eq(r.model)&year.policy.eq(r.policy)];ff=freq[freq.model.eq(r.model)&freq.policy.eq(r.policy)]
  txt+='\n该网格点逐年结果：\n\n'+md(yy[['year','precision','point_recall','event_recall','active_date_fraction']])+'\n逐频率结果：\n\n'+md(ff[['frequency','precision','point_recall','event_recall','active_date_fraction']])
 txt+='''
延迟列为各任务首次命中延迟中位数的平均，单位自然日；起点为事后阶段低点，只对已检出周期计算。召回与延迟必须一起看，不能用漏掉难例换得更短延迟。

每种政策使用相同的全部可评价周期分母。名单在删除未知标签前确定，未知不计负例。precision沿用已知报警的日期等权口径，无可评价报警的日期不计算precision，活跃日期比例和信号数量单独列出；没有precision的任务不能被静默删除后宣称达标。时点召回同时报告。

主样本2021年至2024年9月，固定24个月随访；全部二三级行业、三频率三阈值双基准。2021分类断点、重复历史探索、严格PIT BLOCKED_DATA、独立前瞻FORWARD_PENDING仍存在。上述网格未通过独立验证，也未部署为实际筛选器。

[完整结果](../outputs/summary.csv) · [逐年](../outputs/annual_summary.csv) · [逐频率](../outputs/frequency_summary.csv) · [冻结候选](../outputs/frozen_candidates.json) · [指标复核](../outputs/validation.json) · [方案](../research_plan.md)
'''
 (ROOT/'reports/observation.md').write_text(txt)
 checks=[]
 def ck(name,ok):
  assert bool(ok),name
  checks.append(name)
 prev=json.loads((OUT/'predecessors.json').read_text());ck('all predecessor hashes unchanged',all(sha(p)==h for p,h in prev.items()))
 ck('all new prediction hashes verified',all(sha(t['path'])==t['sha256'] for t in receipt['tasks']))
 ck('frozen candidate identity',sha(OUT/'frozen_candidates.json')==receipt['frozen_sha256'])
 ck('all scoring checks passed',json.loads((OUT/'validation.json').read_text())['status']=='PASS')
 source={t['task']:t for t in json.loads((E/'v20_persistent_confirmation/outputs/prediction_receipt.json').read_text())['tasks']}
 for t in receipt['tasks']:
  pred=pd.read_parquet(t['path']);ck('finite scores '+t['task'],pred.prob.notna().all() and pred.prob.between(0,1).all())
  ck('new scores zero when ineligible '+t['task'],pred.loc[pred.model.isin(new)&pred.state_eligible.eq(0),'prob'].eq(0).all())
  old=pd.read_parquet(source[t['task']]['path'],filters=[('model','in',cfg['controls'])]);control=pred[pred.model.isin(old.model.unique())]
  ck('old prediction bytes values preserved '+t['task'],old.reset_index(drop=True).equals(control[old.columns].reset_index(drop=True)))
 if 'folds' in receipt:ck('all quarter label maturities precede fit',all(pd.Timestamp(f['latest_training_label'])<pd.Timestamp(f['quarter']) for f in receipt['folds']))
 if 'prefix_checks' in receipt:ck('4110 temporal prefix tests',receipt['prefix_checks']==4110)
 if 'v23_' in ROOT.name:
  w=pd.read_csv(OUT/'training_weight_audit.csv')
  ck('weight audit for all model quarter fits',len(w)==2*len(receipt['folds']))
  ck('positive class weight mass preserved',np.allclose(w.positive_weight,w.original_positive_weight))
  ck('all positive events equal weighted',np.allclose(w.min_event_weight,w.max_event_weight))
 audit=json.loads((OUT/'auxiliary_target_audit.json').read_text())
 ck('auxiliary target file unchanged',sha(audit['path'])==audit['sha256']==receipt['targets_sha256'])
 ck('auxiliary prefix and maturity audit',audit['prefix_checks']>0 and audit['positive_negative_same_maturity'])
 ck('17 policies for every model',s.groupby('model').size().eq(17).all())
 for p in ROOT.rglob('*.md'):
  if 'attempts' in p.parts:continue
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):ck('link '+link,(p.parent/link).exists())
 js(OUT/'report_validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),diagnostic_target_hits=hits[['model','policy']].to_dict('records'),goal_complete=False))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
 print('PASS',len(checks),'checks;',len(files),'files');print(best[['model','policy','precision','event_recall']].to_string(index=False))

if __name__=='__main__':run()
