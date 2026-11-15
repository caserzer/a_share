from common import *
import pandas as pd
from portfolio_r04 import path_for
from regime_reversal_actions_r220 import IDS
METRICS=['return5','excess5','return20','excess20','return60','excess60','drawdown60','min_from_entry60','continuation20_60','continuation_excess20_60']
def run():
 out=ROOT/'outputs/r228';out.mkdir(exist_ok=True);paths=[ROOT/'outputs/r221/actions.parquet',ROOT/'outputs/r129/daily_2026-10-21.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
 p=pd.read_parquet(paths[0]);d=pd.read_parquet(paths[1]);market=pd.read_parquet(paths[2]).close;cal=pd.DatetimeIndex(market.index);d['day_i']=cal.get_indexer(d.date);lookup={k:g.set_index('date') for k,g in d.groupby(KEY)};records=[]
 for row in p[KEY+['date']].drop_duplicates().to_dict('records'):
  i=cal.get_indexer([row['date']])[0];rec=dict(row);key=tuple(row[c] for c in KEY)
  for h in [5,20,60]:
   for name in ['return','excess','market','drawdown','min_from_entry']:rec[name+str(h)]=np.nan
   rec['status'+str(h)]='unknown_path';rec['maturity'+str(h)]=pd.NaT
   if i>=0 and i+h+1<len(cal):
    dates=cal[i+1:i+h+2];a=path_for(lookup[key],dates) if key in lookup else None
    if a is not None:
     b=market.loc[dates].to_numpy()/market.loc[dates[0]];rec.update({f'return{h}':a[-1]-1,f'market{h}':b[-1]-1,f'excess{h}':a[-1]-b[-1],f'drawdown{h}':(a/np.maximum.accumulate(a)-1).min(),f'min_from_entry{h}':a.min()-1,f'status{h}':'valid',f'maturity{h}':dates[-1]})
  rec['continuation20_60']=(1+rec['return60'])/(1+rec['return20'])-1;rec['continuation_excess20_60']=rec['continuation20_60']-((1+rec['market60'])/(1+rec['market20'])-1);rec['success20']=float(rec['return20']>=.05 and rec['excess20']>=.03) if np.isfinite(rec['return20']) else np.nan;records.append(rec)
 o=pd.DataFrame(records);o.to_parquet(out/'paths.parquet',index=False);p=p.merge(o,on=KEY+['date'],validate='many_to_one');assert np.allclose(p.ret,p.return20,equal_nan=True);known=p.y.notna();assert np.allclose(p.loc[known,'y'],p.loc[known,'success20']);a=p[p.alert].copy();a.to_parquet(out/'alert_followup.parquet',index=False);rows=[]
 for key,g in a.groupby(IDS+['date']):
  ident=dict(zip(IDS+['date'],key))
  for label,v in [('all',g),('success20',g[g.success20.eq(1)]),('not_success20',g[g.success20.eq(0)])]:
   rec=dict(ident,followup_cohort=label,alerts=len(g),selected=len(v),unknown20=int(g.success20.isna().sum()))
   for metric in METRICS:
    x=v[metric].dropna();rec[metric]=x.mean();rec[metric+'_known']=len(x);rec[metric+'_unknown']=len(v)-len(x)
   rows.append(rec)
 dates=pd.DataFrame(rows);dates.to_csv(out/'date_metrics.csv',index=False);group=IDS+['followup_cohort'];dates.groupby(group)[METRICS].mean().reset_index().to_csv(out/'summary.csv',index=False);paired=[]
 for key,g in dates.groupby([x for x in group if x!='variant']):
  base=g[g.variant.eq('base')].set_index('date')
  for variant in ['state','interaction']:
   other=g[g.variant.eq(variant)].set_index('date');assert base.index.equals(other.index)
   ident=dict(zip([x for x in group if x!='variant'],key),comparison=variant+'-base')
   for metric in METRICS:
    x=other[metric]-base[metric];paired.append(dict(ident,metric=metric,planned_dates=len(x),paired_dates=int(x.notna().sum()),delta=x.mean(),unknown_base=int(base[metric+'_unknown'].sum()),unknown_variant=int(other[metric+'_unknown'].sum())))
 q=pd.DataFrame(paired);q.to_csv(out/'comparisons.csv',index=False)
 js(out/'verification.json',dict(status='PASS',unique_paths=len(o),source_rows=len(p),alerts=len(a),known20=int(o.status20.eq('valid').sum()),known60=int(o.status60.eq('valid').sum()),inputs={str(x):sha(x) for x in paths+[ROOT/'protocols/r228.json',Path(__file__),ROOT/'src/portfolio_r04.py']},outputs={f:sha(out/f) for f in ['paths.parquet','alert_followup.parquet','date_metrics.csv','summary.csv','comparisons.csv']},adoption=False))
 print(q[q.followup_cohort.eq('all')].groupby(['comparison','metric']).delta.agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
