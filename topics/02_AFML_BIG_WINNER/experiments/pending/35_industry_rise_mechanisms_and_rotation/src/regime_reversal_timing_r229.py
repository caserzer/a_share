from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
from portfolio_r04 import path_for

def run():
 out=ROOT/'outputs/r229';out.mkdir(exist_ok=True);files=[ROOT/'outputs/r220/actions.parquet',ROOT/'outputs/r129/daily_2026-10-21.parquet',CACHE/'forecast_v5/CSI_ALL.parquet'];p=pd.read_parquet(files[0]);assert p.horizon.eq(20).all();d=pd.read_parquet(files[1]);m=pd.read_parquet(files[2]).close;cal=pd.DatetimeIndex(m.index);d['day_i']=cal.get_indexer(d.date);lookup={k:g.set_index('date') for k,g in d.groupby(KEY)};rows=[]
 for row in p[KEY+['date']].drop_duplicates().to_dict('records'):
  i=cal.get_indexer([row['date']])[0];rec=dict(row,path_status='unknown_path',breach=np.nan,entry_to_breach=np.nan,signal_to_breach=np.nan,breach_date=pd.NaT,entry_date=pd.NaT)
  if i>=0 and i+21<len(cal):
   dates=cal[i+1:i+22];a=path_for(lookup[tuple(row[k] for k in KEY)],dates);b=m.loc[dates].to_numpy()/m.loc[dates[0]]
   if a is not None:
    offsets=np.flatnonzero(a/b-1<=-.08);rec.update(path_status='valid',breach=float(len(offsets)>0),entry_date=dates[0])
    if len(offsets):j=int(offsets[0]);assert 1<=j<=20;rec.update(entry_to_breach=j,signal_to_breach=j+1,breach_date=dates[j])
  rows.append(rec)
 o=pd.DataFrame(rows);o.to_parquet(out/'paths.parquet',index=False);p=p.merge(o,on=KEY+['date'],validate='many_to_one');assert p.status.eq(p.path_status).all();known=p.y.notna();assert p.loc[known,'y'].eq(p.loc[known,'breach']).all();p.to_parquet(out/'alerts_and_paths.parquet',index=False);metrics=[]
 for key,g in p.groupby(IDS+['date']):
  v=g[g.path_status.eq('valid')];positive=v[v.breach.eq(1)];hit=positive[positive.alert];alerts=v[v.alert];metrics.append(dict(zip(IDS+['date'],key),candidates=len(g),known=len(v),unknown=len(g)-len(v),alerts=int(g.alert.sum()),unknown_alerts=int((g.alert&g.path_status.ne('valid')).sum()),positive=len(positive),hit=len(hit),missed=len(positive)-len(hit),false_alert=int(alerts.breach.eq(0).sum()),precision=len(hit)/len(alerts) if len(alerts) else np.nan,recall=len(hit)/len(positive) if len(positive) else np.nan,mean_entry_lead=hit.entry_to_breach.mean(),median_entry_lead=hit.entry_to_breach.median()))
 dates=pd.DataFrame(metrics);dates.to_csv(out/'date_metrics.csv',index=False);dates.groupby(IDS)[['precision','recall','mean_entry_lead','median_entry_lead']].mean().reset_index().to_csv(out/'summary.csv',index=False);pairs=[];ids=[c for c in IDS if c!='variant']
 for key,g in p.groupby(ids):
  base=g[g.variant.eq('base')];ident=dict(zip(ids,key));dg=dates
  for c,v in ident.items():dg=dg[dg[c].eq(v)]
  for variant in ['state','interaction']:
   q=g[g.variant.eq(variant)].merge(base,on=['industry_code','date'],suffixes=('_new','_base'),validate='one_to_one');assert len(q)==len(base);assert np.allclose(q.breach_new,q.breach_base,equal_nan=True);positive=q[q.breach_base.eq(1)];both=positive[positive.alert_new&positive.alert_base];assert both.entry_to_breach_new.eq(both.entry_to_breach_base).all();rec=dict(ident,comparison=variant+'-base',positive_origins=len(positive),both_hits=len(both),gained_hits=int((positive.alert_new&~positive.alert_base).sum()),lost_hits=int((~positive.alert_new&positive.alert_base).sum()),same_origin_lead_delta=0 if len(both) else np.nan)
   for metric in ['precision','recall','mean_entry_lead']:
    w=dg.pivot(index='date',columns='variant',values=metric);x=w[variant]-w['base'];rec['delta_'+metric]=x.mean();rec[metric+'_paired_dates']=int(x.notna().sum())
   pairs.append(rec)
 pd.DataFrame(pairs).to_csv(out/'comparisons.csv',index=False);js(out/'verification.json',dict(status='PASS',paths=len(o),known_paths=int(o.path_status.eq('valid').sum()),breach_paths=int(o.breach.eq(1).sum()),source_rows=len(p),label_checks=int(known.sum()),inputs={str(f):sha(f) for f in files+[ROOT/'protocols/r229.json',Path(__file__),ROOT/'src/portfolio_r04.py']},outputs={f:sha(out/f) for f in ['paths.parquet','alerts_and_paths.parquet','date_metrics.csv','summary.csv','comparisons.csv']},adoption=False))
 print(pd.DataFrame(pairs).groupby('comparison')[['delta_precision','delta_recall','delta_mean_entry_lead','gained_hits','lost_hits']].median().to_string())
if __name__=='__main__':run()
