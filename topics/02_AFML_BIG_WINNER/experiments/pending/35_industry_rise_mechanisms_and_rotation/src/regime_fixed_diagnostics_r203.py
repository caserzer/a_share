from common import *
import pandas as pd
SOURCES={'fixed_rank':'outputs/r132/evaluation/outputs/r01/date_metrics.csv','financial_r03':'outputs/r165/evaluation/outputs/r03/date_metrics.csv','financial_r07':'outputs/r165/evaluation/outputs/r07/date_metrics.csv'}
STATES=['down_low','down_high','up_low','up_high','unknown']
def run():
 out=ROOT/'outputs/r203';out.mkdir(exist_ok=True);state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;parts=[];summaries=[];paired=[];gates=[];coverage=[]
 for family,path in SOURCES.items():
  d=pd.read_csv(ROOT/path,parse_dates=['date']);d['family']=family;d['regime']=d.date.map(state).fillna('unknown');parts.append(d)
  keys=[c for c in ['era','level','cohort','delay','horizon'] if c in d];metrics=[c for c in ['ic','top_excess','top_minus_equal'] if c in d]
  for key,g in d.dropna(subset=['horizon','method']).groupby(keys,dropna=False):
   ident=dict(zip(keys,key));ident['family']=family
   for method,z in g.groupby('method'):
    for st in STATES:
     v=z[z.regime.eq(st)];coverage.append(dict(ident,method=method,regime=st,rows=len(v),dates=v.date.nunique(),known_ic=int(v.ic.notna().sum())))
     for metric in metrics:
      x=v.dropna(subset=[metric]);summaries.append(dict(ident,method=method,regime=st,metric=metric,dates=x.date.nunique(),years=x.date.dt.year.nunique(),mean=x[metric].mean(),sample_gate=bool(x.date.nunique()>=24 and x.date.dt.year.nunique()>=3)))
   methods=set(g.method);pairs=[(x,'F') for x in methods if x!='F'] if 'F' in methods else []
   for a,b in sorted(pairs):
    for metric in metrics:
     x=g[g.method.eq(a)][['date','regime',metric]];y=g[g.method.eq(b)][['date','regime',metric]];q=x.merge(y,on=['date','regime'],suffixes=('_a','_b'),validate='one_to_one')
     for st in STATES:
      v=q[q.regime.eq(st)].dropna(subset=[metric+'_a',metric+'_b']);delta=v[metric+'_a']-v[metric+'_b'];paired.append(dict(ident,first=a,second=b,regime=st,metric=metric,dates=len(v),delta=delta.mean()))
   if family!='fixed_rank':
    for year in sorted(g.date.dt.year.unique()):
     prior=g[g.date.lt(pd.Timestamp(int(year),1,1))];months=prior.date.nunique();assert months<18
     gates.append(dict(ident,year=int(year),prior_signal_months_upper_bound=months,required_mature_train_months=18,status='insufficient_history_before_any_row_or_class_gate'))
 pd.concat(parts,ignore_index=True).to_parquet(out/'dated_metrics.parquet',index=False);pd.DataFrame(summaries).to_csv(out/'state_summary.csv',index=False);pd.DataFrame(paired).to_csv(out/'state_pairs.csv',index=False);pd.DataFrame(coverage).to_csv(out/'coverage.csv',index=False);js(out/'early_training_gates.json',gates)
 # Independently weighted state means reconstruct the full valid-date mean.
 maxerr=0.;summary=pd.DataFrame(summaries)
 for family,path in SOURCES.items():
  d=pd.read_csv(ROOT/path);keys=[c for c in ['era','level','cohort','delay','horizon','method'] if c in d]
  for key,g in d.dropna(subset=['horizon','method']).groupby(keys,dropna=False):
   for metric in [c for c in ['ic','top_excess','top_minus_equal'] if c in d]:
    q=summary[summary.family.eq(family)&summary.metric.eq(metric)]
    for k,v in zip(keys,key):q=q[q[k].eq(v)]
    assert q.dates.sum()==g[metric].notna().sum()
    if q.dates.sum():
     actual=float((q['mean'].fillna(0)*q.dates).sum()/q.dates.sum());err=abs(actual-g[metric].mean());assert err<1e-12;maxerr=max(maxerr,err)
 js(out/'verification.json',dict(status='PASS',source_rows=sum(len(x) for x in parts),state_summary_rows=len(summaries),state_pair_rows=len(paired),early_gate_records=len(gates),weighted_reconstruction_error=maxerr,adoption=False,new_models=0,fixed_rank_learnable_regime_complete=False,inputs={x:sha(ROOT/x) for x in list(SOURCES.values())+['outputs/r195/market_regimes.parquet','protocols/r203.json','src/regime_fixed_diagnostics_r203.py']},outputs={x:sha(out/x) for x in ['dated_metrics.parquet','state_summary.csv','state_pairs.csv','coverage.csv','early_training_gates.json']}))
 print(len(summaries),len(paired),len(gates),maxerr)
if __name__=='__main__':run()
