from common import *
import pandas as pd
from portfolio_r04 import path_for
ROOT144=ROOT/'outputs/r144/evaluation';G=['family','era','level','target_type','horizon','method','variant']
def run():
 out=ROOT/'outputs/r219';out.mkdir(exist_ok=True);reads=[ROOT/'outputs/r205/predictions.parquet',ROOT144/'cache/forecast_v5/daily_industries.parquet',ROOT144/'cache/forecast_v5/CSI_ALL.parquet',ROOT144/'data/r26_non_event_context.parquet',ROOT144/'data/r14_industry_events.parquet',ROOT144/'data/r26_industry_events.parquet'];p=pd.read_parquet(reads[0]);prices=pd.read_parquet(reads[1]);market=pd.read_parquet(reads[2]).close;cal=pd.DatetimeIndex(market.index);prices['day_i']=cal.get_indexer(prices.date);look={k:g.set_index('date') for k,g in prices.groupby(KEY)};context=pd.read_parquet(reads[3]);old=pd.read_parquet(reads[4]);new=pd.read_parquet(reads[5]);k=KEY+['signal_date'];lost=old[k].drop_duplicates().merge(new[k].drop_duplicates(),on=k,how='left',indicator=True);quarantine=set(map(tuple,lost[lost._merge.eq('left_only')][k].to_numpy()));context['quarantined']=context[KEY+['date']].apply(tuple,axis=1).isin(quarantine);controls={}
 for family in ['fixed_fy','unknown_controls']:
  c=context[~context.is_event&context.quintile.notna()&(~context.quarantined if family=='unknown_controls' else True)]
  controls[family]={k:g.industry_code.tolist() for k,g in c.groupby(['era','level','date','quintile'])}
 panels={}
 for family in p.family.unique():
  path=ROOT/f'outputs/r205/{family}_panel.parquet';reads.append(path);panels[family]=pd.read_parquet(path).set_index('event_id')
 pathcache={};benchcache={};outcomes=[];memberrows=[];maxerr=0
 def path(era,level,code,entry,end):
  key=(era,level,code,entry,end)
  if key not in pathcache:
   dates=cal[(cal>=entry)&(cal<=end)];pathcache[key]=path_for(look[(era,level,code)],dates) if (era,level,code) in look else None
  return pathcache[key]
 for key,g in p.groupby(['family','event_id','target_type','horizon'],sort=False):
  family,eid,typ,h=key;row=g.iloc[0];z=panels[family].loc[eid];entry=z.entry_date;end=z[f'maturity{h}'];rec=dict(family=family,event_id=eid,target_type=typ,horizon=h,entry=entry,exit=end,status='unknown_original_target');rec['reference_members']=1
  if pd.isna(row.y):outcomes.append(rec);continue
  assert pd.notna(entry) and pd.notna(end) and entry>row.date
  dates=cal[(cal>=entry)&(cal<=end)];assert len(dates)==h+1;a=path(row.era,row.level,row.industry_code,entry,end);b=market.reindex(dates).to_numpy()/market.loc[entry]
  if typ=='matched_post':
   ck=(family,row.era,row.level,row.date,z.quintile,h)
   if ck not in benchcache:
    names=controls[family].get((row.era,row.level,row.date,z.quintile),[]);assert row.industry_code not in names;assert len(names)==z.control_count
    pp=[path(row.era,row.level,c,entry,end) for c in names];benchcache[ck]=np.mean(np.column_stack(pp),axis=1) if len(names)>=3 and all(v is not None for v in pp) else None
    for c in names:memberrows.append(dict(family=family,era=row.era,level=row.level,date=row.date,quintile=z.quintile,horizon=h,industry_code=c,weight=1/len(names)))
   b=benchcache[ck];rec['reference_members']=len(controls[family].get((row.era,row.level,row.date,z.quintile),[]))
  if a is None or b is None:rec['status']='unknown_path';outcomes.append(rec);continue
  er=a[-1]-1;br=b[-1]-1;err=abs(er-br-row.y);assert err<1e-10;maxerr=max(maxerr,err);dd=lambda w:float(np.min(w/np.maximum.accumulate(w)-1));rec.update(status='valid',event_return=er,reference_return=br,event_dd=dd(a),reference_dd=dd(b));outcomes.append(rec)
 o=pd.DataFrame(outcomes);o.to_parquet(out/'outcomes.parquet',index=False);pd.DataFrame(memberrows).to_parquet(out/'control_members.parquet',index=False);d=p.merge(o,on=['family','event_id','target_type','horizon'],validate='many_to_one');d['choose_event']=d.prediction.gt(0);d['gross']=np.where(d.choose_event,d.event_return,d.reference_return);d['drawdown']=np.where(d.choose_event,d.event_dd,d.reference_dd)
 for label,c in [('net20',.002),('net50',.005)]:d[label]=d.gross-c*(2+d.gross);d['always_event_'+label]=d.event_return-c*(2+d.event_return);d['always_reference_'+label]=d.reference_return-c*(2+d.reference_return)
 d.to_parquet(out/'decisions.parquet',index=False);daily=d.groupby(G+['date']).agg(planned=('prediction','size'),known=('gross','count'),industry_choices=('choose_event','sum'),gross=('gross','mean'),net20=('net20','mean'),net50=('net50','mean'),drawdown=('drawdown','mean')).reset_index();daily.to_csv(out/'date_metrics.csv',index=False);comparisons=[];paired=[]
 for key,g in d.groupby(['family','era','level','target_type','horizon']):
  for (am,av),(bm,bv),kind in [((m,v),(m,'base'),'regime') for m in ['controls','with_revision'] for v in ['state','interaction']]+[(('with_revision',v),('controls',v),'mechanism') for v in ['base','state','interaction']]:
   q=g[g.method.eq(am)&g.variant.eq(av)].merge(g[g.method.eq(bm)&g.variant.eq(bv)],on=['event_id','date'],validate='one_to_one',suffixes=('_a','_b'));assert len(q)==len(g[g.method.eq(am)&g.variant.eq(av)]);v=q[q.status_a.eq('valid')&q.status_b.eq('valid')].copy();ident=dict(zip(['family','era','level','target_type','horizon'],key),kind=kind,first=am+'_'+av,second=bm+'_'+bv);r=dict(ident,planned=len(q),matched=len(v),dates=v.date.nunique(),decision_changes=int(v.choose_event_a.ne(v.choose_event_b).sum()))
   for col in ['gross','net20','net50','drawdown']:
    v['delta']=v[col+'_a']-v[col+'_b'];r['delta_'+col]=v.groupby('date').delta.mean().mean()
    for date,value in v.groupby('date').delta.mean().items():paired.append(dict(ident,date=date,metric=col,delta=value))
   comparisons.append(r)
 pd.DataFrame(comparisons).to_csv(out/'comparisons.csv',index=False);pd.DataFrame(paired).to_parquet(out/'paired_dates.parquet',index=False);js(out/'verification.json',dict(status='PASS',predictions=len(d),valid=int(d.status.eq('valid').sum()),outcomes=len(o),outcome_valid=int(o.status.eq('valid').sum()),target_max_error=maxerr,adoption=False,inputs={str(x):sha(x) for x in reads+[ROOT/'protocols/r219.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['outcomes.parquet','control_members.parquet','decisions.parquet','date_metrics.csv','comparisons.csv','paired_dates.parquet']}));print('predictions',len(d),'valid',sum(d.status.eq('valid')),'outcomes',len(o));print(pd.DataFrame(comparisons).query("horizon==20").groupby(['kind','first']).delta_net50.agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
