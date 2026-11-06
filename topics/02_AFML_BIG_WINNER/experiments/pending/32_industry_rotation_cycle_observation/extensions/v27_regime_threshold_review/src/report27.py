from pathlib import Path
import sys,json,re
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];E=ROOT.parent;OUT=ROOT/'outputs'
sys.path.insert(0,str(E/'v6_economic_diffusion/src'))
from context6 import sha,js

def md(d):
 return '|'+ '|'.join(d.columns)+'|\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+'\n'.join('|'+ '|'.join(str(x) for x in row)+'|' for row in d.itertuples(index=False,name=None))+'\n'

def run():
 s=pd.read_csv(OUT/'summary.csv');y=pd.read_csv(OUT/'annual_summary.csv');q=pd.read_csv(OUT/'frequency_summary.csv');hits=s[s.diagnostic_target_hit]
 cols=['policy','precision','event_recall','point_recall','active_date_fraction','precision_lower','precision_upper']
 base=E/'v23_event_weighting/outputs';comparisons={}
 for d,fn,key in [(y,'annual_summary.csv','year'),(q,'frequency_summary.csv','frequency')]:
  b=pd.read_csv(base/fn).query("model=='risk_blend' and policy=='top_0.1'")
  a=d[d.policy.eq('all_p0.11')];fields=['precision','event_recall','point_recall']
  out=a[[key]+fields+['active_date_fraction']].merge(b[[key]+fields],on=key,suffixes=('_new','_base'));out.to_csv(OUT/f'{key}_baseline_comparison.csv',index=False);comparisons[key]=out
 txt='''# EP32 V27：出现满足汇总门槛的历史候选

固定市场126日条件及双模型基底，0.10—0.15的11个门槛中，0.11和0.115同时满足原日期平均precision≥23.50%、周期recall≥41.25%。按事前规定优先较低门槛保留召回，选择0.11进入独立重算。

0.11对应precision24.65%、周期recall44.39%、时点recall14.44%；有信号日期占27.45%，任务内首次检出中位延迟的平均为46.75自然日。24.65%是已知标签下的原日期等权precision，不是所有信号未来结果均已解决。

'''+md(hits[cols])+ '\n完整门槛区间：\n\n'+md(s[cols])+ '\n逐年与原risk_blend比较：\n\n'+md(comparisons['year'])+'\n逐频率：\n\n'+md(comparisons['frequency'])+'''

2023周期recall从47.00%降至18.57%；周度precision22.27%尚未单独达到23.50%。汇总达标不等于每年或每个频率均达标。时点recall从20.35%降至14.44%，也不能隐藏。

0.11共20,308条报警，其中11,841条标签已知、8,467条未知（计数口径41.69%未知，任务平均未知比例另见表）。若把全部未知分别设为负/正，仅用于敏感性界限，全部报警日期的precision可在12.15%—59.03%；这不是置信区间，且与原排除无已知报警日期的precision分母不同。实际未知标签继续保留未知，未被填充。

用户随后明确选择“按已确认的汇总门槛验收，完整保留年度和频率局限”。该选择不改变上述失败分解或原样本边界；最终验收仍须独立重算本候选，不能只依赖本次网格最佳。

主样本2021—2024年9月固定24个月随访；全二三级行业、三频率三阈值双基准保留。原市场状态只影响是否报警，全部可评价周期仍作recall分母。历史已反复探索，严格PIT BLOCKED_DATA和独立前瞻FORWARD_PENDING不变。

[全区间结果](../outputs/summary.csv) · [年度对照](../outputs/year_baseline_comparison.csv) · [频率对照](../outputs/frequency_baseline_comparison.csv) · [评分验证](../outputs/validation.json)
'''
 (ROOT/'reports/threshold_review.md').write_text(txt)
 previous=json.loads((OUT/'predecessors.json').read_text());assert all(sha(p)==h for p,h in previous.items())
 assert len(s)==11 and len(hits)==2 and hits.policy.isin(['all_p0.11','all_p0.115']).all()
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):assert (p.parent/link).exists()
 js(OUT/'report_validation.json',dict(status='PASS',previous_unchanged=True,diagnostic_hits=hits[['policy','precision','event_recall']].to_dict('records'),selected_policy='all_p0.11',user_accepts_aggregate_gate=True,independent_recalculation_pending=True))
 files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts]
 js(OUT/'manifest.json',dict(files=files,file_count=len(files)));print('V27 report PASS',len(files),'files')

if __name__=='__main__':run()
