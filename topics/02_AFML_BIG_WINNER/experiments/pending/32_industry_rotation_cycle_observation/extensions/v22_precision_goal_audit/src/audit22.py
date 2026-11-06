from pathlib import Path
import sys,json,re
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js
VERSIONS=['v17_precision_recall_frontier','v18_conditional_diffusion','v19_remaining_model_frontier','v20_persistent_confirmation','v21_long_context']

def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'
def show(d):
 d=d[['model','policy','precision','point_recall','event_recall','active_date_fraction','median_delay_days']].copy()
 for c in ['precision','point_recall','event_recall','active_date_fraction']:d[c]=d[c].map(lambda x:f'{x:.2%}')
 d.median_delay_days=d.median_delay_days.map(lambda x:f'{x:.2f}')
 return md(d)

def run():
 previous={};frames=[];years=[];freq=[];checks=[]
 def ck(name,ok):
  assert bool(ok),name
  checks.append(name)
 for version in VERSIONS:
  r=E/version;m=json.loads((r/'outputs/manifest.json').read_text())
  previous.update(json.loads((r/'outputs/predecessors.json').read_text()))
  previous.update({str(r/f['path']):f['sha256'] for f in m['files']});previous[str(r/'outputs/manifest.json')]=sha(r/'outputs/manifest.json')
  ck('source validation '+version,json.loads((r/'outputs/validation.json').read_text())['status']=='PASS')
  for filename,dest in [('summary.csv',frames),('annual_summary.csv',years),('frequency_summary.csv',freq)]:
   d=pd.read_csv(r/'outputs'/filename);d['source_version']=version;dest.append(d)
 ck('all predecessors and sibling results frozen',all(sha(p)==h for p,h in previous.items()));js(OUT/'predecessors.json',previous)
 columns=['precision','point_recall','event_recall','active_date_fraction','median_delay_days','alerts','known_alerts']
 f=pd.concat(frames,ignore_index=True)
 for key,g in f.groupby(['model','policy']):
  if len(g)>1:ck('identical duplicate '+str(key),all(np.allclose(g[c],g.iloc[0][c],equal_nan=True) for c in columns))
 f=f.drop_duplicates(['model','policy']);ck('37 models and 629 policies',f.model.nunique()==37 and len(f)==629)
 f.to_csv(OUT/'all_candidates.csv',index=False)
 y=pd.concat(years,ignore_index=True).drop_duplicates(['model','policy','year']);y.to_csv(OUT/'annual_summary.csv',index=False)
 q=pd.concat(freq,ignore_index=True).drop_duplicates(['model','policy','frequency']);q.to_csv(OUT/'frequency_summary.csv',index=False)
 feasible=f[f.event_recall.ge(.4125)&f.tasks.eq(f.precision_defined_tasks)].sort_values('precision',ascending=False)
 best=feasible.head(10);best.to_csv(OUT/'recall_preserving_frontier.csv',index=False)
 hits=f[f.precision.ge(.235)&f.event_recall.ge(.4125)&f.tasks.eq(f.precision_defined_tasks)]
 ck('reported targets agree',np.array_equal(f.diagnostic_target_hit.to_numpy(),(f.precision.ge(.235)&f.event_recall.ge(.4125)&f.tasks.eq(f.precision_defined_tasks)).to_numpy()))
 b=f[f.model.eq('risk_blend')&f.policy.eq('top_0.1')].iloc[0]
 ck('baseline precision reproduced',abs(b.precision-.117500)<1e-6);ck('baseline event recall reproduced',abs(b.event_recall-.458319)<1e-6)
 decision=dict(status='DIAGNOSTIC_CANDIDATE_REQUIRES_REVIEW' if len(hits) else 'TARGET_NOT_MET',precision_target=.235,event_recall_floor=.4125,candidate_count=629,model_count=37,diagnostic_hits=hits[['model','policy','precision','event_recall']].to_dict('records'),best_recall_preserving=best.iloc[0][['model','policy','precision','event_recall','point_recall','median_delay_days','source_version']].to_dict(),goal_complete=False,strict_PIT='BLOCKED_DATA',forward_validation='FORWARD_PENDING')
 js(OUT/'decision.json',decision)
 r=best.iloc[0]
 txt='# EP32：precision翻倍目标的阶段汇总\n\n'
 txt+=f'目标保持precision≥23.50%、周期recall≥41.25%。本轮累计37个冻结模型、629项不同模型/选择政策，符合两项数值目标的组合数为{len(hits)}；目标尚未完成。选择网格已反复查看历史，不能视为629次独立验证。\n\n'
 txt+='原主要候选和当前保召回网格最优对照：\n\n'+show(pd.DataFrame([b,r]))
 txt+='\n保留召回下限的前十项：\n\n'+show(best)
 txt+='\n上述最佳网格点的逐年表现：\n\n'+md(y[y.model.eq(r.model)&y.policy.eq(r.policy)][['year','precision','point_recall','event_recall','active_date_fraction']])
 txt+='\n逐频率表现：\n\n'+md(q[q.model.eq(r.model)&q.policy.eq(r.policy)][['frequency','precision','point_recall','event_recall','active_date_fraction']])
 txt+='''
五步探索分别是：V17调整五个主要模型的选择预算；V18增加条件扩散信息并设同容量对照；V19补齐其余20个旧模型；V20检验持续确认和模型一致性；V21补回6—12个月趋势及市场状态。每步原失败结果、预定网格和数据边界都保留。

precision维持原有日期等权口径，没有已知报警的日期不纳入该均值，因此活跃日期比例必须一起看。周期recall的分母始终为原全部可评价周期，没有随筛选政策缩小。时点recall另外报告。延迟列是各任务中位延迟的平均，基于首次命中的自然日距阶段低点，仅对检出周期计算。

所有结果保留原全二三级行业、周/双周/月、三阈值、双基准，主评价2021年至2024年9月统一24个月随访。未知结果不记负例，2021分类断点覆盖较低；严格PIT仍BLOCKED_DATA，独立前瞻FORWARD_PENDING。更高precision的网格最优尚未替代原主要候选，更未部署。

下一步有待检验的方向是让训练目标更贴近“每个周期至少发现一次”：当前逐时点损失会重复计入同一容易识别的周期。可固定比较按成熟正例周期等权的模型与原逐日期权重模型，并保持正例总权重和同样标签成熟隔离；在完成实验前不声称它能提高precision或recall。本轮没有把这项未执行方案算作完成。

[所有629项组合](../outputs/all_candidates.csv) · [逐年](../outputs/annual_summary.csv) · [逐频率](../outputs/frequency_summary.csv) · [机器可读状态](../outputs/decision.json) · [V17](../../v17_precision_recall_frontier/reports/frontier_observation.md) · [V18](../../v18_conditional_diffusion/reports/conditional_diffusion.md) · [V19](../../v19_remaining_model_frontier/reports/remaining_frontier.md) · [V20](../../v20_persistent_confirmation/reports/observation.md) · [V21](../../v21_long_context/reports/observation.md)
'''
 (ROOT/'reports/precision_goal_progress.md').write_text(txt)
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):ck('link '+link,(p.parent/link).exists())
 js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks,goal_complete=False))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)));print(json.dumps(decision,ensure_ascii=False,indent=2));print('PASS',len(checks),'checks;',len(files),'files')

if __name__=='__main__':run()
