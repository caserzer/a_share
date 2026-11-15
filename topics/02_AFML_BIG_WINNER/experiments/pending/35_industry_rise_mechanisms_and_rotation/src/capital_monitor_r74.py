import pandas as pd
from common import *
def expected(date):return pd.Timestamp(date).to_period('Q').end_time.normalize() if pd.Timestamp(date).is_quarter_end else (pd.Timestamp(date).to_period('Q')-1).end_time.normalize()
def build(source):
 rows=[];df=pd.DataFrame(source);df['snapshot']=pd.to_datetime(df.snapshot);df['period_date']=pd.to_datetime(df.period)
 for key,g in df.groupby(KEY+['snapshot']):
  date=key[-1];period=expected(date);q=g[g.period_date.eq(period)];latest=q.iloc[0] if len(q) else None;good=g[g.coverage_gate & g.period_date.le(period)].sort_values('period_date');last=good.iloc[-1] if len(good) else None
  excluded=bool(g.financial_excluded.max()>0 and g.financial_excluded.max()==g.members.max());status='financial_excluded' if excluded else 'period_not_in_source' if latest is None else 'historical_proxy_available' if latest.coverage_gate else 'insufficient_coverage'
  row=dict(zip(KEY,key[:-1]),snapshot=date,expected_period=period,status=status,selected_period=latest.period if latest is not None else None,current_joint_known=int(latest.joint_known) if latest is not None else None,current_denominator=int(latest.denominator) if latest is not None else None,current_capex_up_fraction=None,current_both_improve_fraction=None,current_both_decline_fraction=None,last_covered_period=last.period if last is not None else None,last_joint_known=int(last.joint_known) if last is not None else None,last_capex_up=int(last.capex_up) if last is not None else None,last_both_improve=int(last.both_improve) if last is not None else None,last_both_decline=int(last.both_decline) if last is not None else None)
  if status=='historical_proxy_available':
   row['current_capex_up_fraction']=latest.capex_up/latest.joint_known
   if latest.capex_up:row.update(current_both_improve_fraction=latest.both_improve/latest.capex_up,current_both_decline_fraction=latest.both_decline/latest.capex_up)
  rows.append(row)
 return rows

def run():
 out=ROOT/'outputs/r74';out.mkdir(exist_ok=True);source=ROOT/'outputs/r73/industry_evidence.json';rows=build(json.loads(source.read_text()));js(out/'monthly_observations.json',rows);df=pd.DataFrame(rows);basepath=ROOT/'outputs/r63/evidence_matrix.parquet';base=pd.read_parquet(basepath);extra=[]
 for x in base.to_dict('records'):
  q=df[df.snapshot.le(pd.Timestamp(x['asof']))]
  for k in KEY:q=q[q[k].eq(x[k])]
  z=q.sort_values('snapshot').iloc[-1].to_dict() if len(q) else None;rec={'operating_status':'no_snapshot','operating_snapshot':None,'operating_expected_period':expected(x['asof']),'operating_last_covered_period':None,'operating_current_capex_up_fraction':None,'operating_current_both_improve_fraction':None,'operating_current_both_decline_fraction':None}
  if z:
   same=z['snapshot']==pd.Timestamp(x['asof']);rec.update(operating_status=z['status'] if same else 'older_snapshot_not_current',operating_snapshot=z['snapshot'],operating_last_covered_period=z['last_covered_period'])
   if same:
    for k in ['capex_up_fraction','both_improve_fraction','both_decline_fraction']:rec['operating_current_'+k]=z['current_'+k]
  extra.append(rec)
 result=pd.concat([base.reset_index(drop=True),pd.DataFrame(extra)],axis=1);result.to_parquet(out/'evidence_matrix.parquet',index=False)
 summary=df.groupby(['snapshot','status']).size().reset_index(name='industries');js(out/'coverage.json',summary.to_dict('records'));paths=[source,basepath,ROOT/'protocols/r74.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},observations=len(rows),base_rows=len(base),ranking_changed=False));print(summary.to_string(index=False))
if __name__=='__main__':run()
