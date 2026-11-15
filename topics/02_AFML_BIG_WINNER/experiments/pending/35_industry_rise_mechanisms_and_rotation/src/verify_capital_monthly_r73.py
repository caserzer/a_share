import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r73';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 sources=pd.read_parquet(ROOT/'outputs/r72/company_pairs.parquet');lookup={(x['asof'],x['ts_code'],x['end_date']):x for x in sources.to_dict('records')}
 cols=KEY+['month','security_id','instrument','unresolved'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)],ignore_index=True);members=members[members.era.eq('SW2021')];membership={tuple(x[k] for k in KEY)+ (x['month'],x['security_id']):x for x in members.to_dict('records')};parents={(x.month,x.security_id):x.industry_code for x in members[members.level.eq('L1')].itertuples()}
 d=pd.read_parquet(out/'member_evidence.parquet');assert not d.duplicated(KEY+['snapshot','period','security_id']).any()
 for x in d.to_dict('records'):
  month=x['snapshot'].to_period('M')-1;key=tuple(x[k] for k in KEY)+(month,x['security_id']);assert key in membership and x['month']==month and x['instrument']==membership[key]['instrument'];parent=parents.get((month,x['security_id']));scope='unknown_identity' if parent is None else 'financial_excluded' if parent in ['801780.SI','801790.SI'] else 'nonfinancial_accounting';assert scope==x['scope'];issuer=x['instrument'][2:]+'.'+x['instrument'][:2];s=lookup.get((x['snapshot'],issuer,pd.Timestamp(x['period'])));known=scope=='nonfinancial_accounting' and s is not None and s['joint_known'];assert known==x['known']
  if known:
   for name,field in [('capex','c_pay_acq_const_fiolta'),('ocf','n_cashflow_act'),('profit','n_income_attr_p')]:
    assert x[name+'_up']==(s[field+'_current']>s[field+'_prior']) and x[name+'_down']==(s[field+'_current']<s[field+'_prior'])
 rows=json.loads((out/'industry_evidence.json').read_text());groups={k:g for k,g in d.groupby(KEY+['snapshot','period'])}
 for x in rows:
  key=tuple(x[k] for k in KEY)+(pd.Timestamp(x['snapshot']),x['period']);g=groups.get(key,pd.DataFrame());n=len(g);den=n+(int(g.unresolved.max()) if n else 0);q=g[g.known] if n else g;up=q[q.capex_up.eq(True)] if n else q
  assert n==x['members'] and den==x['denominator'] and len(q)==x['joint_known'] and len(up)==x['capex_up'];assert x['coverage_gate']==bool(len(q)>=5 and den and len(q)/den>=.8)
  for category,sign in [('both_improve','up'),('both_decline','down')]:assert x[category]==(int((up['ocf_'+sign].eq(True)&up['profit_'+sign].eq(True)).sum()) if n else 0)
 old=json.loads((ROOT/'outputs/r70/industry_evidence.json').read_text());sept={tuple(x[k] for k in KEY+['period']):x for x in rows if pd.Timestamp(x['snapshot'])==pd.Timestamp('2026-09-30')};assert len(sept)==len(old)
 for x in old:
  y=sept[tuple(x[k] for k in KEY+['period'])]
  for k in ['denominator','joint_known','coverage_gate','capex_up','both_improve','both_decline']:assert x[k]==y[k]
 for x in json.loads((out/'summary.json').read_text()):
  q=[z for z in rows if z['snapshot']==x['snapshot'] and z['period']==x['period'] and z['level']==x['level']];assert len(q)==x['industries'] and sum(z['coverage_gate'] for z in q)==x['passing'] and sum(z['joint_known'] for z in q)==x['joint_members']
 js(out/'verification.json',dict(status='PASS',member_rows=len(d),industry_rows=len(rows),september_R70_rows_reproduced=len(old),monthly_membership_and_source_clocks_checked=True));print('R73 VERIFIED',len(d),len(rows),'September',len(old))
if __name__=='__main__':run()
