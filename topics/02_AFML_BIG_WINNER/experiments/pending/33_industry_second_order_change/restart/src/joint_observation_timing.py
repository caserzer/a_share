import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p52';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
f=EP/'restart/p50/evaluated.parquet';pf=EP/'restart/p30/training_panel.parquet';ids=['era','industry_code','date'];q=pd.read_parquet(f,columns=ids+['block','week','B_selected','P_selected','B_edge','P_edge']);p=pd.read_parquet(pf,columns=ids+['day_i','nav','status','boundary_proxy']);q=q.merge(p,on=ids,validate='one_to_one');rows=[];segments=[]
def finish(seg,start_known,end_reason):
 if not seg:return
 g=pd.DataFrame(seg);b=g[g.B_selected];p=g[g.P_selected];both=len(b)>0 and len(p)>0
 firstB=b.iloc[0] if len(b) else None;firstP=p.iloc[0] if len(p) else None
 lag=int(firstP.day_i-firstB.day_i) if both else None
 if both:
  early,late=(firstB,firstP) if lag>=0 else (firstP,firstB);change=late.nav/early.nav-1
 else:change=None
 rows.append(dict(era=g.era.iloc[0],industry_code=g.industry_code.iloc[0],block=int(g.block.iloc[0]),start=str(g.date.iloc[0].date()),last_observed=str(g.date.iloc[-1].date()),start_known=start_known,end_reason=end_reason,weeks=len(g),B_first=str(firstB.date.date()) if firstB is not None else None,P_first=str(firstP.date.date()) if firstP is not None else None,relation=('P_EARLIER' if lag<0 else 'B_EARLIER' if lag>0 else 'SAME_WEEK') if both else 'ONLY_B' if len(b) else 'ONLY_P',P_minus_B_sessions=lag,earlier_to_later_nav_change=change,observed_segment_has_proxy=bool(g.status.eq('STALE_PROXY').any() or g.boundary_proxy.any())))
 segments.append(g)
for _,g in q.groupby(['era','industry_code','block']):
 prev=None;seg=[];known=False
 for row in g.sort_values('date').to_dict('records'):
  consecutive=prev is not None and row['week']==prev['week']+1
  if seg and not consecutive:finish(seg,known,'GAP');seg=[]
  active=bool(row['B_selected'] or row['P_selected'])
  if active:
   if not seg:known=consecutive and not (prev['B_selected'] or prev['P_selected'])
   seg.append(row)
  elif seg:finish(seg,known,'BOTH_EXIT');seg=[]
  prev=row
 if seg:finish(seg,known,'END_OR_BLOCK_BOUNDARY')
a=pd.DataFrame(rows);a.to_csv(OUT/'segments.csv',index=False);a.groupby(['start_known','end_reason','relation']).size().rename('segments').to_csv(OUT/'composition.csv');known=a[a.start_known];both=known[known.P_minus_B_sessions.notna()];both.groupby('relation')[['P_minus_B_sessions','earlier_to_later_nav_change']].median().to_csv(OUT/'paired_medians.csv')
assert sum(len(g) for g in segments)==int((q.B_selected|q.P_selected).sum())
for g in segments:
 assert (g.B_selected|g.P_selected).all() and g.week.diff().dropna().eq(1).all()
inputs=[f,pf,Path(__file__),EP/'restart/P52_joint_observation_timing_plan.md'];(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',no_future_labels_read=True,segments=len(a),known_starts=len(known),unknown_starts=int((~a.start_known).sum()),original_B_edges=int(q.B_edge.sum()),original_P_edges=int(q.P_edge.sum()),active_rows_covered=sum(len(g) for g in segments),inputs={str(x):sha(x) for x in inputs},artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n');print(a.groupby(['start_known','end_reason','relation']).size().to_string());print(both.groupby('relation')[['P_minus_B_sessions','earlier_to_later_nav_change']].median().to_string());print('known',len(known),'both',len(both),'median_signed_lag',both.P_minus_B_sessions.median())
