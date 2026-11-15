import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r94';out.mkdir(exist_ok=True);ip=ROOT/'outputs/r73/industry_evidence.json';mp=ROOT/'outputs/r73/member_evidence.parquet';fp=ROOT/'outputs/r72/selected_fields.parquet';bp=ROOT/'outputs/r93/task_evidence.parquet';industries=pd.DataFrame(json.loads(ip.read_text()));industries['snapshot']=pd.to_datetime(industries.snapshot);members=pd.read_parquet(mp);fields=pd.read_parquet(fp);f=fields[fields.end_date.dt.year.eq(2026)].copy();f['period']=f.end_date.dt.strftime('%Y-%m-%d');available=f.groupby(['asof','period','ts_code']).agg(first_proxy=('available_at','min'),last_proxy=('available_at','max'),selected_fields=('field','size'),invalid_fields=('status',lambda s:int(s.ne('available').sum()))).reset_index();j=members.merge(available,left_on=['snapshot','period','ts_code'],right_on=['asof','period','ts_code'],how='left',validate='many_to_one');j.to_parquet(out/'member_disclosure_clock.parquet',index=False)
 observed=[]
 for key,g in j.groupby(KEY+['snapshot','period']):
  q=g[g.selected_fields.notna()];observed.append(dict(zip(KEY+['snapshot','period'],key),observed_members=len(q),first_proxy=q.first_proxy.min(),last_proxy=q.last_proxy.max(),invalid_fields=int(q.invalid_fields.sum())))
 audit=industries.merge(pd.DataFrame(observed),on=KEY+['snapshot','period'],how='left',validate='one_to_one');audit.to_parquet(out/'period_coverage.parquet',index=False);rows=[]
 for key,g in audit.groupby(KEY+['snapshot']):
  g=g[g.observed_members.gt(0)].sort_values('period');x=g.iloc[-1] if len(g) else None;row=dict(zip(KEY+['snapshot'],key),period=None,status='no_observed_period',first_proxy=None,last_proxy=None,observed_members=0,invalid_fields=0,denominator=None,joint_known=None,capex_up_fraction=None,both_improve_fraction=None,both_decline_fraction=None)
  if x is not None:
   status='financial_excluded' if x.financial_excluded==x.members and x.members>0 else 'source_limited_disclosed_period_available' if x.coverage_gate else 'latest_observed_period_insufficient_coverage'
   row.update(period=x.period,status=status,first_proxy=x.first_proxy,last_proxy=x.last_proxy,observed_members=int(x.observed_members),invalid_fields=int(x.invalid_fields),denominator=int(x.denominator),joint_known=int(x.joint_known))
   if status=='source_limited_disclosed_period_available':row.update(capex_up_fraction=x.capex_up/x.joint_known,both_improve_fraction=x.both_improve/x.capex_up if x.capex_up else None,both_decline_fraction=x.both_decline/x.capex_up if x.capex_up else None)
  rows.append(row)
 js(out/'observations.json',rows);obs=pd.DataFrame(rows);base=pd.read_parquet(bp);keys=base[KEY+['asof']].drop_duplicates();extra=[]
 for x in keys.to_dict('records'):
  g=obs[obs.snapshot.le(x['asof'])]
  for k in KEY:g=g[g[k].eq(x[k])]
  g=g.sort_values('snapshot');z=g.iloc[-1] if len(g) else None;rec=dict(**x,disclosed_view_status='no_source_snapshot',disclosed_source_snapshot=None,disclosed_source_age_days=None,disclosed_last_period=None,disclosed_period_age_days=None,disclosed_last_status=None,disclosed_last_proxy=None,disclosed_last_capex_up_fraction=None,disclosed_last_both_improve_fraction=None,disclosed_last_both_decline_fraction=None,disclosed_scope='latest_observed_in_limited_Q1_H1_source_not_complete_public_disclosure')
  if z is not None:
   rec.update(disclosed_view_status=z.status if z.snapshot==x['asof'] else 'older_source_snapshot_not_current',disclosed_source_snapshot=z.snapshot,disclosed_source_age_days=(x['asof']-z.snapshot).days,disclosed_last_period=z.period,disclosed_period_age_days=(x['asof']-pd.Timestamp(z.period)).days if z.period else None,disclosed_last_status=z.status,disclosed_last_proxy=z.last_proxy)
   for k in ['capex_up_fraction','both_improve_fraction','both_decline_fraction']:rec['disclosed_last_'+k]=z[k]
  extra.append(rec)
 extras=pd.DataFrame(extra);extras.to_parquet(out/'industry_date_view.parquet',index=False);result=base.merge(extras,on=KEY+['asof'],how='left',validate='many_to_one');result.to_parquet(out/'task_evidence.parquet',index=False);summary=extras.groupby(['asof','level','disclosed_view_status','disclosed_last_period'],dropna=False).size().reset_index(name='industries');js(out/'coverage.json',summary.to_dict('records'));paths=[ip,mp,fp,bp,ROOT/'protocols/r94.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},observations=len(rows),task_rows=len(result),source_limited=True));print(summary.to_string(index=False))
if __name__=='__main__':run()
