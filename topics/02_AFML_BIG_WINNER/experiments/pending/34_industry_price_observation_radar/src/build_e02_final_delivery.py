"""Local historical delivery: past-price questions only; evaluation stays separate."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha

def main():
 out=EP/'handoff/20261112_e02_final';dest=out/'observations'
 dest.mkdir(exist_ok=False)
 source=EP/'outputs/v2_s07_explained_primary/all_observations.parquet';d=pd.read_parquet(source);old=d.copy()
 def pct(x):return '未知' if pd.isna(x) else f'{x:.2%}'
 def question(r):
  if r.state=='NEW':return f'近5日{pct(r.r5)}、20日{pct(r.r20)}，相对市场20日{pct(r.relative20)}：价格改善是否来自更多成分而非少数权重？后续研究核对驱动与持续性，经济解释尚未确认。'
  if r.state=='TRACKING':return f'近5日{pct(r.r5)}、20日{pct(r.r20)}，已连续{int(r.weak_reviews)}次20日非正复核：下一次复核是否恢复改善或达到退出条件？入池以来{pct(r.since_entry)}不能证明基本面变化。'
  if r.state=='EXIT':return f'本期退出原因：{r.trigger_or_update_reason}。后续若有新的价格依据，须先满足重入间隔；此次退出是否是价格失效或数据/身份不可用，应分别核查。'
  if r.state=='DATA_INSUFFICIENT':return '先核对同链历史、行业身份与缺价状态；证据不足不能判断是否存在价格改善，不因缺数据作无机会结论。'
  return f'本期未新增限制：{r.non_admission_constraints}。近5日{pct(r.r5)}、20日{pct(r.r20)}；下一期核对条件是否变化，未入池不等于没有改善。'
 d['research_question']=[question(r) for r in d.itertuples()]
 assert d.research_question.notna().all() and d.research_question.str.len().gt(0).all()
 pd.testing.assert_frame_equal(d.drop(columns='research_question'),old.drop(columns='research_question'))
 d.to_parquet(dest/'all_observations.parquet',index=False);latest=d[d.date.eq(d.date.max())];latest.to_csv(dest/'latest_full_catalog.csv',index=False)
 active=latest[latest.state.isin(['NEW','TRACKING'])].sort_values(['state','industry_code'])
 lines=['# 20日主观察池：历史清单','',f'完整观察周截至{latest.date.max():%Y-%m-%d}，不是当前实时名单。价格数据截至2026-10-21，末周不完整，不入观察清单。',
 '',f'目录{len(latest)}，在池{len(active)}，新增{latest.state.eq("NEW").sum()}，数据不足{latest.state.eq("DATA_INSUFFICIENT").sum()}。在池中5日非正{active.r5.le(0).sum()}个为风险跟踪，不称仍在升温。',
 '', '|行业|状态|首次提示|5日|20日|相对市场20日|入池后同链变化|', '|---|---|---|---:|---:|---:|---:|']
 for r in active.itertuples():lines.append(f'|{r.industry_name}|{"新入观察" if r.state=="NEW" else "风险跟踪" if r.r5<=0 else "持续改善跟踪"}|{r.first_alert:%Y-%m-%d}|{pct(r.r5)}|{pct(r.r20)}|{pct(r.relative20)}|{pct(r.since_entry)}|')
 lines+=['','## 逐行业后续核查','']
 for r in active.itertuples():lines.append(f'- {r.industry_name}（{r.observation_id}）：{r.research_question}')
 lines+=['','规则：40日同链历史、近5/20日正收益准入；按20日涨幅排序，新增取5/空位/候选数最小值，在池最多20。连续两次20日非正、8观察周到期、数据或身份失效退出，至少4观察周后可重新入池。','', '全部历史、未触发、退出和数据不足见同目录文件；逐行未知、规则/数据版本、原始价格代理标记与具体限制保留。后验过程ID、覆盖和收益追踪存于评价目录，没有回填成当时已知信号。']
 (dest/'latest_review.md').write_text('\n'.join(lines)+'\n')
 (dest/'receipt.json').write_text(json.dumps({'inputs':{str(source):sha(source),str(Path(__file__)):sha(Path(__file__))},'rows':len(d),'original_fields_unchanged_except_research_question':True,'historical_only':True,'artifacts':{p.name:sha(p) for p in dest.iterdir() if p.is_file()}},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'rows':len(d),'latest_directory':len(latest),'active':len(active),'questions_complete':True},ensure_ascii=False))
if __name__=='__main__':main()
