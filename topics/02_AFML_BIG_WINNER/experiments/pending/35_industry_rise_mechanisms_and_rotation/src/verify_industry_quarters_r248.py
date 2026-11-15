from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r248';base=ROOT/'outputs/r147/evaluation/outputs/r73';m=pd.read_parquet(out/'member_diagnostic.parquet');q=pd.read_parquet(ROOT/'outputs/r247/quarter_fields.parquet');source=pd.read_parquet(base/'member_evidence.parquet');cols=KEY+['snapshot','month','security_id','instrument','unresolved','parent_l1','scope'];expected=source[cols].drop_duplicates().sort_values(KEY+['snapshot','security_id']).reset_index(drop=True);got=m.sort_values(KEY+['snapshot','security_id']).reset_index(drop=True);pd.testing.assert_frame_equal(expected,got[cols]);assert m.month.eq(m.snapshot.dt.to_period('M')-1).all()
 fields={'capex':'c_pay_acq_const_fiolta','ocf':'n_cashflow_act','profit':'n_income_attr_p'};lookup={(r['asof'],r['ts_code'],r['field']):r for r in q.to_dict('records')};checks=0;member_groups={}
 for r in m.to_dict('records'):
  issuer=r['instrument'][2:]+'.'+r['instrument'][:2];assert r['ts_code']==issuer
  for quarter in ['q1','h1','q2']:
   signs=[]
   for short,field in fields.items():
    src=lookup.get((r['snapshot'],issuer,field));sign=src[quarter+'_sign'] if src else 'unknown';assert r[quarter+'_'+short]==sign;signs.append(sign);checks+=1
   known=all(s!='unknown' for s in signs) and r['scope']=='nonfinancial_accounting';assert r[quarter+'_known']==known
  assert r['native_known']==r['h1_known'] and r['common_known']==(r['q1_known'] and r['h1_known'] and r['q2_known']);member_groups.setdefault(tuple(r[k] for k in KEY+['snapshot']),[]).append(r)
 cat=pd.DataFrame(json.loads((base/'industry_evidence.json').read_text()));cat['snapshot']=pd.to_datetime(cat.snapshot);cat=cat[cat.period.eq('2026-06-30')].set_index(KEY+['snapshot']);industry=pd.read_parquet(out/'industry_diagnostic.parquet');assert len(industry)==4*len(cat) and not industry.duplicated(KEY+['snapshot','variant']).any();values={}
 for r in industry.to_dict('records'):
  key=tuple(r[k] for k in KEY+['snapshot']);g=member_groups.get(key,[]);original=cat.loc[key];quarter,eligibility={'h1_native':('h1','native_known'),'h1_common':('h1','common_known'),'q1_common':('q1','common_known'),'q2_common':('q2','common_known')}[r['variant']];eligible=[x for x in g if x[eligibility]];n=len(eligible);den=len(g)+max([int(x['unresolved']) for x in g],default=0);gate=n>=5 and den>0 and 5*n>=4*den;assert r['members']==len(g)==original.members and r['denominator']==den==original.denominator and r['known']==n and r['gate']==gate
  up=[x for x in eligible if x[quarter+'_capex']=='positive'];improve=sum(x[quarter+'_ocf']=='positive' and x[quarter+'_profit']=='positive' for x in up);decline=sum(x[quarter+'_ocf']=='negative' and x[quarter+'_profit']=='negative' for x in up);allup=sum(all(x[quarter+'_'+f]=='positive' for f in fields) for x in eligible);expected_values={f+'_up_share':sum(x[quarter+'_'+f]=='positive' for x in eligible)/n if gate else np.nan for f in fields};expected_values['all_three_up_share']=allup/n if gate else np.nan;expected_values['coherence']=(improve-decline)/len(up) if gate and up else np.nan
  for name,value in expected_values.items():assert np.isclose(r[name],value,equal_nan=True,atol=1e-12);checks+=1
  values[key+(r['variant'],)]=(gate,expected_values,n)
 comparisons=pd.read_parquet(out/'comparisons.parquet');assert len(comparisons)==len(cat)*15
 for r in comparisons.to_dict('records'):
  key=tuple(r[k] for k in KEY+['snapshot']);a,b=r['comparison'].split('-');ga,va,na=values[key+(a,)];gb,vb,nb=values[key+(b,)];difference=va[r['metric']]-vb[r['metric']];assert np.isclose(r['difference'],difference,equal_nan=True,atol=1e-12);assert r['known_new']==na and r['known_base']==nb and r['both_gate']==(ga and gb)
  if a in ['q2_common'] :assert na==nb
  status='coverage_failed' if not(ga and gb) else 'comparable' if pd.notna(difference) else 'zero_capex_up_denominator';assert status==r['status']
 summary=pd.read_csv(out/'summary.csv',parse_dates=['snapshot'])
 for r in summary.to_dict('records'):
  g=comparisons
  for k in ['snapshot','level','comparison','metric']:g=g[g[k].eq(r[k])]
  v=g[g.status.eq('comparable')];assert len(g)==r['catalogue'] and len(v)==r['comparable'] and sum(v.difference>0)==r['positive'] and sum(v.difference<0)==r['negative'] and sum(v.difference==0)==r['equal'];assert np.isclose(r['mean_difference'],v.difference.mean(),equal_nan=True,atol=1e-12);assert np.isclose(r['median_difference'],v.difference.median(),equal_nan=True,atol=1e-12)
 receipt=json.loads((out/'verification.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(Path(f))==h
 for f,h in receipt['outputs'].items():assert sha(out/f)==h
 js(out/'independent_verification.json',dict(status='PASS',member_links=len(m),source_sign_and_metric_checks=checks,industry_rows=len(industry),comparison_rows=len(comparisons),summary_rows=len(summary),code_sha256=sha(Path(__file__)),adoption=False));print('PASS',len(m),checks,len(industry),len(comparisons))
if __name__=='__main__':run()
