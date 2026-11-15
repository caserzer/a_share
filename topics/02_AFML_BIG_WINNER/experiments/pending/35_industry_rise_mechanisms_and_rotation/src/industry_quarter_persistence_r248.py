from common import *
import pandas as pd
FIELDS={'capex':'c_pay_acq_const_fiolta','ocf':'n_cashflow_act','profit':'n_income_attr_p'}
VARIANTS={'h1_native':('h1','native_known'),'h1_common':('h1','common_known'),'q1_common':('q1','common_known'),'q2_common':('q2','common_known')}
METRICS=['capex_up_share','ocf_up_share','profit_up_share','all_three_up_share','coherence']
def run():
 out=ROOT/'outputs/r248';out.mkdir(exist_ok=True);base=ROOT/'outputs/r147/evaluation/outputs/r73';source=pd.read_parquet(base/'member_evidence.parquet');cols=KEY+['snapshot','month','security_id','instrument','unresolved','parent_l1','scope'];m=source[cols].drop_duplicates();assert not m.duplicated(KEY+['snapshot','security_id']).any();m['ts_code']=m.instrument.str[2:]+'.'+m.instrument.str[:2]
 q=pd.read_parquet(ROOT/'outputs/r247/quarter_fields.parquet');wide=q.pivot(index=['asof','ts_code'],columns='field',values=['q1_sign','h1_sign','q2_sign']);wide.columns=[t.replace('_sign','')+'_'+next(k for k,v in FIELDS.items() if v==f) for t,f in wide.columns];wide=wide.reset_index().rename(columns={'asof':'snapshot'});m=m.merge(wide,on=['snapshot','ts_code'],how='left',validate='many_to_one')
 for quarter in ['q1','h1','q2']:
  cs=[quarter+'_'+f for f in FIELDS];m[cs]=m[cs].fillna('unknown');m[quarter+'_known']=m[cs].ne('unknown').all(axis=1)&m.scope.eq('nonfinancial_accounting')
 m['native_known']=m.h1_known;m['common_known']=m.q1_known&m.q2_known&m.h1_known;m.to_parquet(out/'member_diagnostic.parquet',index=False)
 original=pd.DataFrame(json.loads((base/'industry_evidence.json').read_text()));original['snapshot']=pd.to_datetime(original.snapshot);cat=original[original.period.eq('2026-06-30')];groups={k:g for k,g in m.groupby(KEY+['snapshot'])};rows=[]
 for r in cat.to_dict('records'):
  ident={k:r[k] for k in KEY+['snapshot']};g=groups.get(tuple(ident.values()),pd.DataFrame());n=len(g);den=n+int(g.unresolved.max()) if n else 0;assert n==r['members'] and den==r['denominator']
  for variant,(quarter,eligibility) in VARIANTS.items():
   selected=g[g[eligibility]] if n else g;known=len(selected);gate=known>=5 and den>0 and known/den>=.8;counts={f:int(selected[quarter+'_'+f].eq('positive').sum()) if known else 0 for f in FIELDS};up=selected[selected[quarter+'_capex'].eq('positive')] if known else selected;improve=int((up[quarter+'_ocf'].eq('positive')&up[quarter+'_profit'].eq('positive')).sum()) if len(up) else 0;decline=int((up[quarter+'_ocf'].eq('negative')&up[quarter+'_profit'].eq('negative')).sum()) if len(up) else 0;allup=int(selected[[quarter+'_'+f for f in FIELDS]].eq('positive').all(axis=1).sum()) if known else 0
   row=dict(ident,variant=variant,members=n,denominator=den,known=known,coverage=known/den if den else np.nan,gate=gate,gate_reason='pass' if gate else 'no_members' if not den else 'fewer_than5' if known<5 else 'coverage_below80',capex_up=counts['capex'],ocf_up=counts['ocf'],profit_up=counts['profit'],all_three_up=allup,both_improve=improve,both_decline=decline,financial_excluded=r['financial_excluded'],identity_unknown=r['identity_unknown'])
   row.update({f+'_up_share':counts[f]/known if gate else np.nan for f in FIELDS});row['all_three_up_share']=allup/known if gate else np.nan;row['coherence']=(improve-decline)/len(up) if gate and len(up) else np.nan;rows.append(row)
 industries=pd.DataFrame(rows);industries.to_parquet(out/'industry_diagnostic.parquet',index=False);comparisons=[]
 for a,b in [('h1_common','h1_native'),('q2_common','h1_common'),('q2_common','q1_common')]:
  x=industries[industries.variant.eq(a)].merge(industries[industries.variant.eq(b)],on=KEY+['snapshot'],suffixes=('_new','_base'),validate='one_to_one');x['comparison']=a+'-'+b;x['both_gate']=x.gate_new&x.gate_base
  for metric in METRICS:
   rec=x[KEY+['snapshot','comparison','both_gate','known_new','known_base','denominator_new']].copy();rec['metric']=metric;rec['difference']=x[metric+'_new']-x[metric+'_base'];rec['status']=np.where(~x.both_gate,'coverage_failed',np.where(rec.difference.notna(),'comparable','zero_capex_up_denominator'));comparisons.append(rec)
 comparisons=pd.concat(comparisons,ignore_index=True);comparisons.to_parquet(out/'comparisons.parquet',index=False);industries.groupby(['snapshot','level','variant']).agg(industries=('industry_code','size'),passing=('gate','sum'),known_member_links=('known','sum')).reset_index().to_csv(out/'coverage.csv',index=False)
 summaries=[]
 for key,g in comparisons.groupby(['snapshot','level','comparison','metric']):
  valid=g[g.status.eq('comparable')];summaries.append(dict(zip(['snapshot','level','comparison','metric'],key),catalogue=len(g),comparable=len(valid),positive=int(valid.difference.gt(0).sum()),negative=int(valid.difference.lt(0).sum()),equal=int(valid.difference.eq(0).sum()),mean_difference=valid.difference.mean(),median_difference=valid.difference.median()))
 pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False);inputs=[base/'member_evidence.parquet',base/'industry_evidence.json',ROOT/'outputs/r247/quarter_fields.parquet',ROOT/'protocols/r248.json',Path(__file__)];js(out/'verification.json',dict(status='PASS',member_links=len(m),catalogue_rows=len(cat),industry_variant_rows=len(industries),comparison_rows=len(comparisons),adoption=False,inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.csv','.parquet']}));print(industries[industries.snapshot.eq('2026-09-30')].groupby(['level','variant']).gate.agg(['size','sum']).to_string())
if __name__=='__main__':run()
