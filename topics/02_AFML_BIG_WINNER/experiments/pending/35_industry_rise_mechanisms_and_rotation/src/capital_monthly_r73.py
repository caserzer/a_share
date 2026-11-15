import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r73';out.mkdir(exist_ok=True);paths=[ROOT/'outputs/r72/company_pairs.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'protocols/r73.json',Path(__file__)]
 p=pd.read_parquet(paths[0]);p['instrument']=p.ts_code.str[-2:]+p.ts_code.str[:6];cols=KEY+['month','security_id','instrument','unresolved'];m=pd.concat([pd.read_parquet(x,columns=cols) for x in paths[1:3]],ignore_index=True);m=m[m.era.eq('SW2021')];catalogue=pd.concat([pd.read_parquet(x,columns=KEY+['date']) for x in paths[3:5]],ignore_index=True);catalogue=catalogue[catalogue.era.eq('SW2021')];details=[];rows=[]
 for date in sorted(p['asof'].unique()):
  date=pd.Timestamp(date);month=date.to_period('M')-1;members=m[m.month.eq(month)];parent=members[members.level.eq('L1')].set_index('security_id').industry_code;assert parent.index.is_unique;cat=catalogue[catalogue.date.eq(date)][KEY].drop_duplicates();members=members.merge(cat,on=KEY,how='inner',validate='many_to_one');members['parent_l1']=members.security_id.map(parent);members['scope']=np.where(members.parent_l1.isna(),'unknown_identity',np.where(members.parent_l1.isin(['801780.SI','801790.SI']),'financial_excluded','nonfinancial_accounting'))
  for period in ['2026-03-31','2026-06-30']:
   q=p[p['asof'].eq(date)&p.end_date.eq(pd.Timestamp(period))];j=members.merge(q,on='instrument',how='left',validate='many_to_one');j['snapshot']=date;j['period']=period;j['known']=j.joint_known.eq(True)&j.scope.eq('nonfinancial_accounting')
   for name,field in [('capex','c_pay_acq_const_fiolta'),('ocf','n_cashflow_act'),('profit','n_income_attr_p')]:
    j[name+'_up']=(j[field+'_current']>j[field+'_prior']).where(j.known);j[name+'_down']=(j[field+'_current']<j[field+'_prior']).where(j.known)
   details.append(j);groups={k:g for k,g in j.groupby(KEY)}
   for key in cat.itertuples(index=False,name=None):
    g=groups.get(key,pd.DataFrame());n=len(g);den=n+(int(g.unresolved.max()) if n else 0);valid=g[g.known] if n else g;up=valid[valid.capex_up.eq(True)] if n else valid;known=len(valid)
    rows.append(dict(zip(KEY,key),snapshot=date,period=period,member_month=str(month),members=n,denominator=den,joint_known=known,coverage_gate=bool(known>=5 and den and known/den>=.8),financial_excluded=int(g.scope.eq('financial_excluded').sum()) if n else 0,identity_unknown=int(g.scope.eq('unknown_identity').sum()) if n else 0,capex_up=len(up),both_improve=int((up.ocf_up.eq(True)&up.profit_up.eq(True)).sum()) if n else 0,both_decline=int((up.ocf_down.eq(True)&up.profit_down.eq(True)).sum()) if n else 0))
 d=pd.concat(details,ignore_index=True);d.to_parquet(out/'member_evidence.parquet',index=False);js(out/'industry_evidence.json',rows);summary=pd.DataFrame(rows).groupby(['snapshot','period','level']).agg(industries=('industry_code','size'),passing=('coverage_gate','sum'),joint_members=('joint_known','sum'),financial_excluded=('financial_excluded','sum'),identity_unknown=('identity_unknown','sum')).reset_index();js(out/'summary.json',summary.to_dict('records'));js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},member_rows=len(d),industry_rows=len(rows),no_market_outcomes=True));print(summary.to_string(index=False))
if __name__=='__main__':run()
