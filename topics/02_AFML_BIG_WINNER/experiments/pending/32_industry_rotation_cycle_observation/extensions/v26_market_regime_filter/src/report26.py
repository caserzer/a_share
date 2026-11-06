from pathlib import Path
import sys,json,re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js

def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'

def run():
 s=pd.read_csv(OUT/'summary.csv');best=s[s.event_recall.ge(.4125)&s.tasks.eq(s.precision_defined_tasks)].sort_values('precision',ascending=False).head(10)
 y=pd.read_csv(OUT/'annual_summary.csv');q=pd.read_csv(OUT/'frequency_summary.csv');r=best.iloc[0]
 yy=y[y.model.eq(r.model)&y.policy.eq(r.policy)];base=pd.read_csv(E/'v23_event_weighting/outputs/annual_summary.csv').query("model=='risk_blend' and policy=='top_0.1'")
 matched=yy[['year','precision','event_recall','brier','active_date_fraction']].merge(base[['year','precision','event_recall','brier']],on='year',suffixes=('_new','_base'));matched.to_csv(OUT/'best_year_baseline_comparison.csv',index=False)
 txt='''# EP32 V26：市场状态过滤接近目标，但存在年度召回回退

原目标仍为precision≥23.50%、周期recall≥41.25%。50项冻结组合中无同时达标者。保留召回下限的最好点为risk_diffusion_min，仅在中证全指过去126日收益>0时发出分数≥0.10的信号：precision23.12%、周期recall49.99%。

有信号日期占28.61%，时点recall16.42%，各任务中位延迟平均45.57天。2023年周期recall从原risk_blend约47.00%降至19.90%，不能用总体改善掩盖该年度退步。信号选择后的未知标签占比也需继续审计。

所有日期和行业仍进入评价；市场条件只控制是否发信号，未发信号的周期仍计漏检，Brier也按完整已知标签样本计算。precision继续采用原有活跃日期平均口径，无已知信号的日期无定义，因此必须同时看覆盖、recall和逐年分解。

保留召回下限的前十项：

'''+md(best[['model','policy','precision','point_recall','event_recall','active_date_fraction','median_delay_days']])+ '\n逐年对照：\n\n'+md(matched)+'\n逐频率：\n\n'+md(q[q.model.eq(r.model)&q.policy.eq(r.policy)][['frequency','precision','point_recall','event_recall','active_date_fraction']])+'''

冻结四种市场过滤条件、两个已冻结基底和五个全池门槛；不改模型，不逐年选择规则。中证全指统一作为背景，沪深300/中证全指最终超额标签仍分别评价。价格前缀和同行广度去重一致性均验证。

主评价2021—2024年9月，24个月统一跟踪；所有二三级行业及三频率/三阈值/双基准保留。历史探索不是独立确认，严格PIT和前瞻缺口不变。

[完整组合](../outputs/summary.csv) · [年度对照](../outputs/best_year_baseline_comparison.csv) · [频率](../outputs/frequency_summary.csv) · [市场条件覆盖](../outputs/gate_coverage.csv) · [评分验证](../outputs/validation.json)
'''
 (ROOT/'reports/market_regime_observation.md').write_text(txt)
 checks=[]
 def ck(name,ok):
  assert bool(ok),name
  checks.append(name)
 cfg=json.loads((OUT/'frozen_candidates.json').read_text());receipt=json.loads((OUT/'prediction_receipt.json').read_text());prev=json.loads((OUT/'predecessors.json').read_text())
 ck('all predecessors unchanged',all(sha(p)==h for p,h in prev.items()))
 ck('50 candidate policies',len(s)==50)
 ck('target not yet met',not s.diagnostic_target_hit.any())
 ck('original scoring checks pass',json.loads((OUT/'validation.json').read_text())['status']=='PASS')
 ck('market prefix and unchanged universe',receipt['market_prefix_pass'] and receipt['all_original_observations_retained'])
 sources={base:{a['task']:a for a in json.loads((E/version/'outputs/prediction_receipt.json').read_text())['tasks']} for base,version in cfg['source_versions'].items()}
 for a in receipt['tasks']:
  ck('prediction hash '+a['task'],sha(a['path'])==a['sha256']);p=pd.read_parquet(a['path'])
  ck('finite scores '+a['task'],p.prob.notna().all() and p.prob.between(0,1).all())
  for base in cfg['controls']:
   old=pd.read_parquet(sources[base][a['task']]['path'],filters=[('model','==',base)]);copy=p[p.model.eq(base)]
   ck('old controls identical '+base+' '+a['task'],old.reset_index(drop=True).equals(copy[old.columns].reset_index(drop=True)))
   for gate in cfg['gates']:
    variant=p[p.model.eq(base+'__'+gate)]
    ck('same rows and pure score suppression '+base+gate+a['task'],np.array_equal(old.row_id,variant.row_id) and ((variant.prob.to_numpy()==0)|(variant.prob.to_numpy()==old.prob.to_numpy())).all())
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):ck('link '+link,(p.parent/link).exists())
 js(OUT/'report_validation.json',dict(status='PASS',checks_count=len(checks),checks=checks,goal_complete=False))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)));print('V26 PASS',len(checks),'checks',len(files),'files')

if __name__=='__main__':run()
