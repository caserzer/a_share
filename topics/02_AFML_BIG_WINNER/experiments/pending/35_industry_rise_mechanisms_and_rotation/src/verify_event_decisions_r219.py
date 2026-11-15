from common import *
import pandas as pd
out=ROOT/'outputs/r219';root=ROOT/'outputs/r144/evaluation';p=pd.read_parquet(ROOT/'outputs/r205/predictions.parquet');d=pd.read_parquet(out/'decisions.parquet');o=pd.read_parquet(out/'outcomes.parquet');members=pd.read_parquet(out/'control_members.parquet');keys=['family','event_id','target_type','horizon','method','variant'];joined=p.merge(d,on=keys,validate='one_to_one',suffixes=('_src','_out'));assert len(joined)==len(p)==len(d);assert np.array_equal(joined.prediction_src,joined.prediction_out);assert np.allclose(joined.y_src,joined.y_out,equal_nan=True);assert d.choose_event.eq(d.prediction.gt(0)).all()
ctx=pd.read_parquet(root/'data/r26_non_event_context.parquet');old=pd.read_parquet(root/'data/r14_industry_events.parquet');new=pd.read_parquet(root/'data/r26_industry_events.parquet');k=KEY+['signal_date'];bad=set(map(tuple,old[k].drop_duplicates().to_numpy()))-set(map(tuple,new[k].drop_duplicates().to_numpy()));member_lookup={};membershipchecks=0
for key,g in members.groupby(['family','era','level','date','quintile','horizon']):
 family,era,level,date,quintile,h=key;z=ctx[ctx.era.eq(era)&ctx.level.eq(level)&ctx.date.eq(date)&ctx.quintile.eq(quintile)&~ctx.is_event];expected=set(z.industry_code)
 if family=='unknown_controls':expected={c for c in expected if (era,level,c,date) not in bad}
 assert expected==set(g.industry_code);assert np.allclose(g.weight,1/len(expected));assert len(expected)>=3;member_lookup[key]=sorted(expected);membershipchecks+=1
prices=pd.read_parquet(root/'cache/forecast_v5/daily_industries.parquet');market=pd.read_parquet(root/'cache/forecast_v5/CSI_ALL.parquet').close;look={k:g.set_index('date') for k,g in prices.groupby(KEY)};panels={f:pd.read_parquet(ROOT/f'outputs/r205/{f}_panel.parquet').set_index('event_id') for f in p.family.unique()};cache={};maximum=0.;checks=0
for row in o.to_dict('records'):
 z=panels[row['family']].loc[row['event_id']];target=z[row['target_type']+str(row['horizon'])];assert row['entry']==z.entry_date or (pd.isna(row['entry']) and pd.isna(z.entry_date))
 if pd.isna(target):assert row['status']=='unknown_original_target';continue
 dates=market.loc[row['entry']:row['exit']].index;assert len(dates)==row['horizon']+1;era=z.era;level=z.level
 def path(code):
  pk=(era,level,code,row['entry'],row['exit'])
  if pk not in cache:
   v=look[(era,level,code)].reindex(dates);cache[pk]=None if v.nav.isna().any() or v.block.nunique()!=1 else v.nav.to_numpy()/v.nav.iloc[0]
  return cache[pk]
 a=path(z.industry_code)
 if row['target_type']=='post':b=market.loc[dates].to_numpy()/market.loc[row['entry']]
 else:
  names=member_lookup[(row['family'],era,level,z.date,z.quintile,row['horizon'])];v=[path(c) for c in names];b=sum(v)/len(v) if all(x is not None for x in v) else None
 if a is None or b is None:assert row['status']=='unknown_path';continue
 assert row['status']=='valid';assert abs(a[-1]-b[-1]-target)<1e-10
 for prefix,w in [('event',a),('reference',b)]:
  peak=1.;dd=0.
  for value in w:peak=max(peak,value);dd=min(dd,value/peak-1)
  for col,value in [(prefix+'_return',w[-1]-1),(prefix+'_dd',dd)]:err=abs(value-row[col]);assert err<1e-12;maximum=max(maximum,err);checks+=1
known=d[d.status.eq('valid')];chosen=np.where(known.choose_event,known.event_return,known.reference_return);assert np.allclose(chosen,known.gross);assert d.loc[d.status.ne('valid'),'gross'].isna().all()
for label,cost in [('net20',.002),('net50',.005)]:
 for prefix,ret in [('',chosen),('always_event_',known.event_return),('always_reference_',known.reference_return)]:
  values=(1+ret)*(1-cost)-(1+cost);assert np.allclose(values,known[prefix+label],atol=1e-12);checks+=len(known)
js(out/'independent_verification.json',dict(status='PASS',forecasts=len(d),control_sets=membershipchecks,paths=len(cache),numeric_checks=checks,max_path_error=maximum,scope='All frozen choices/labels; original control membership including quarantine; full industry/reference paths and sequential drawdowns; independent entry/exit cashflow fees',script_sha256=sha(__file__)));print('PASS',len(d),membershipchecks,checks,maximum)
