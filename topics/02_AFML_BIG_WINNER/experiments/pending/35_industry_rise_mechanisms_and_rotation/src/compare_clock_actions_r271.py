from common import *
import pandas as pd
out=ROOT/'outputs/r271';ids=KEY+['date','horizon','method','variant'];a=pd.read_parquet(out/'snapshot/actions/actions.parquet');b=pd.read_parquet(out/'signal/actions/actions.parquet');z=a.merge(b,on=ids,suffixes=('_snapshot','_signal'),validate='one_to_one');assert len(z)==len(a)==len(b);assert z.status_snapshot.equals(z.status_signal);assert np.allclose(z.ret_snapshot,z.ret_signal,equal_nan=True);assert np.array_equal(z[z.method.isin(['FS','FSE'])].alert_snapshot,z[z.method.isin(['FS','FSE'])].alert_signal)
ka=['era','level','horizon','method','variant','date','cost'];a=pd.read_csv(out/'snapshot/actions/date_metrics.csv',parse_dates=['date']);b=pd.read_csv(out/'signal/actions/date_metrics.csv',parse_dates=['date']);d=a.merge(b,on=ka,suffixes=('_snapshot','_signal'),validate='one_to_one');assert d.alerts_snapshot.eq(d.alerts_signal).all();assert d.eligible_snapshot.eq(d.eligible_signal).all();rows=[]
for key,g in d.groupby(ka[:-2]+['cost']):
 for period,v in [('all',g)]+[(str(y),gg) for y,gg in g.groupby(g.date.dt.year)]:
  for scope,sub in [('known_paths',v),('complete_dates',v[v.known_paths_snapshot.eq(v.eligible_snapshot)])]:
   rec=dict(zip(ka[:-2]+['cost'],key),period=period,scope=scope,dates=len(sub))
   for met in ['cash_policy_gain','market_policy_gain','precision','recall','wrong_absolute_exit','wrong_relative_exit']:rec['delta_'+met]=(sub[met+'_snapshot']-sub[met+'_signal']).mean()
   rows.append(rec)
pd.DataFrame(rows).to_csv(out/'clock_comparisons.csv',index=False)
a=pd.read_csv(out/'snapshot/random/date_metrics.csv',parse_dates=['date']);b=pd.read_csv(out/'signal/random/date_metrics.csv',parse_dates=['date']);k=ka+['policy'];d=a.merge(b,on=k,suffixes=('_snapshot','_signal'),validate='one_to_one');assert np.allclose(d.random_constant_snapshot,d.random_constant_signal);assert np.allclose(d.random_unknown_coefficient_snapshot,d.random_unknown_coefficient_signal);symbols=[]
for key,g in d.groupby(['era','level','horizon','method','variant','cost','policy']):
 c=(g.selection_constant_snapshot-g.selection_constant_signal).mean();coef=(g.selection_unknown_coefficient_snapshot-g.selection_unknown_coefficient_signal).mean();symbols.append(dict(zip(['era','level','horizon','method','variant','cost','policy'],key),known_constant=c,unknown_coefficient=coef,missing_cancels=coef==0,break_even_unknown_gain=-c/coef if coef else np.nan))
 # Independently reconstruct each monthly contribution from paired original rows.
 for row in g.to_dict('records'):
  v=z.copy()
  for field in ['era','level','horizon','method','variant','date']:v=v[v[field].eq(row[field])]
  assert len(v)==row['n_snapshot'];cost=row['cost'];known=v.status_snapshot.eq('valid');diff=v.alert_snapshot.astype(int)-v.alert_signal.astype(int);ret=v.loc[known,'ret_snapshot'];market=v.loc[known,'market_snapshot'];hold=(1+ret)*(1-cost);exitvalue=(1-cost) if row['policy']=='cash' else (1-cost)**3*(1+market);constant=float(((exitvalue-hold)*diff[known]).sum()/len(v));unknown=float(diff[~known].sum()/len(v));assert np.isclose(constant,row['selection_constant_snapshot']-row['selection_constant_signal'],atol=1e-12);assert np.isclose(unknown,row['selection_unknown_coefficient_snapshot']-row['selection_unknown_coefficient_signal'])
pd.DataFrame(symbols).to_csv(out/'clock_missing_sensitivity.csv',index=False)
for clock in ['signal','snapshot']:
 for part in ['actions','random']:assert json.loads((out/clock/part/'independent_verification.json').read_text())['status']=='PASS'
js(out/'independent_verification.json',dict(status='PASS',paired_rows=len(z),clock_comparisons=len(rows),symbolic_comparisons=len(symbols),unknown_cancels=sum(x['missing_cancels'] for x in symbols),scope='Both clock path/selection/cashflow and random verifiers; paired action counts, identical random expectation, direct paired-row cashflow and symbolic missing coefficients',adoption=False));print('PAIRED ACTIONS',len(z),len(symbols))
