import pandas as pd
from common import *
def inputs():
 protocol=json.loads((ROOT/'protocols/r68.json').read_text());date=pd.Timestamp(protocol['asof']);month=pd.Period(protocol['membership_month'])
 paths=[ROOT/'outputs/r67/same_period_pairs.json',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'protocols/r68.json']
 pairs=pd.DataFrame(json.loads(paths[0].read_text()));pairs['end_date']=pd.to_datetime(pairs.end_date);pairs['instrument']=(pairs.ts_code.str[-2:]+pairs.ts_code.str[:6]).where(pairs.ts_code.str.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)'))
 members=pd.concat([pd.read_parquet(p,columns=KEY+['month','instrument','security_id','unresolved']) for p in paths[1:3]],ignore_index=True);members=members[members.era.eq('SW2021')&members.month.eq(month)];assert not members.duplicated(KEY+['security_id']).any()
 catalogue=pd.concat([pd.read_parquet(p,columns=KEY+['date']) for p in paths[3:5]],ignore_index=True);catalogue=catalogue[catalogue.era.eq('SW2021')&catalogue.date.eq(date)].drop_duplicates(KEY)
 members=members.merge(catalogue[KEY],on=KEY,how='inner',validate='many_to_one')
 return protocol,paths,pairs,members,catalogue

def run():
 out=ROOT/'outputs/r68';out.mkdir(exist_ok=True);protocol,paths,pairs,members,catalogue=inputs();rows=[];details=[]
 js(out/'identity_quarantine.json',pairs[pairs.instrument.isna()].to_dict('records'))
 for period in protocol['periods']:
  for field in sorted(pairs.field.unique()):
   f=pairs[pairs.end_date.eq(pd.Timestamp(period))&pairs.field.eq(field)&pairs.instrument.notna()];assert not f.instrument.duplicated().any()
   j=members.merge(f.drop(columns='ts_code'),on='instrument',how='left',validate='many_to_one');j['audit_period']=period;j['audit_field']=field;details.append(j)
   grouped={key:g for key,g in j.groupby(KEY)}
   for key in catalogue[KEY].itertuples(index=False,name=None):
    g=grouped.get(key,pd.DataFrame());n=len(g);u=int(g.unresolved.max()) if n else 0;den=n+u;known=int(g.eligible.eq(True).sum()) if n else 0
    rows.append(dict(zip(KEY,key),period=period,field=field,resolved_members=n,unresolved=u,denominator=den,known=known,coverage=known/den if den else None,coverage_gate=bool(known>=protocol['gate']['minimum_known'] and den and known/den>=protocol['gate']['minimum_fraction']),no_pair=int(g.eligible.isna().sum()) if n else 0,current_conflicts=int(g.current_status.eq('conflicting_latest_values').sum()) if n else 0,prior_conflicts=int(g.prior_status.eq('conflicting_latest_values').sum()) if n else 0))
 d=pd.concat(details,ignore_index=True);d.to_parquet(out/'member_links.parquet',index=False);js(out/'industry_coverage.json',rows)
 a=pd.DataFrame(rows);summary=[]
 for key,g in a.groupby(['level','period','field']):summary.append(dict(zip(['level','period','field'],key),industries=len(g),passing=int(g.coverage_gate.sum()),median_coverage=float(g.coverage.median()),median_members_passing=float(g[g.coverage_gate].resolved_members.median()),median_members_failing=float(g[~g.coverage_gate].resolved_members.median())))
 js(out/'summary.json',summary);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths+[Path(__file__)]},catalogue=len(catalogue),coverage_rows=len(rows),links=len(d),no_outcomes_read=True))
 print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':run()
