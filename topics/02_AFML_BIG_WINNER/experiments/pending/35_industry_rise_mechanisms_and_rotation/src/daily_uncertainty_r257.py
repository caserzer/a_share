from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r257';source=ROOT/'outputs/r256/predictions.parquet';p=pd.read_parquet(source);calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values();rows=[];blocks=[];summary=[];resamples=[]
 for key,g in p.groupby(['era','level','year']):
  index=KEY+['date'];wide=g.pivot(index=index,columns='variant',values=['y','monthly_probability','daily_probability']);assert wide['y'].nunique(axis=1).le(1).all()
  y=wide['y']['base'];spec=[(v+'_daily-monthly',wide.daily_probability[v],wide.monthly_probability[v]) for v in ['base','state','interaction']]+[(v+'_daily-base_daily',wide.daily_probability[v],wide.daily_probability['base']) for v in ['state','interaction']]
  cal=calendar[calendar.year==key[2]];ordinal={d:i for i,d in enumerate(cal)}
  for name,a,b in spec:
   diff=((a-y)**2-(b-y)**2).dropna();daily=diff.groupby('date').mean().to_frame('difference');daily['session_index']=[ordinal[d] for d in daily.index];daily['block']=daily.session_index//21;ident=dict(zip(['era','level','year'],key),comparison=name)
   for date,x in daily.iterrows():rows.append(dict(ident,date=date,difference=x.difference,session_index=int(x.session_index),block=int(x.block)))
   agg=daily.groupby('block').difference.agg(['sum','count']);available=[]
   for i in range((len(cal)+20)//21):
    n=int(agg.loc[i,'count']) if i in agg.index else 0;t=float(agg.loc[i,'sum']) if n else None
    blocks.append(dict(ident,block=i,start=cal[i*21],end=cal[min((i+1)*21,len(cal))-1],dates=n,total=t))
    if n:available.append((t,n))
   rec=dict(ident,dates=len(daily),calendar_sessions=len(cal),missing_dates=len(cal)-len(daily),observed_blocks=len(available),point=float(daily.difference.mean()),status='evaluated' if len(available)>=8 else 'insufficient_blocks')
   if len(available)>=8:
    vals=np.array(available);rng=np.random.default_rng(35099);idx=rng.integers(0,len(vals),size=(20000,len(vals)));sim=vals[idx,0].sum(axis=1)/vals[idx,1].sum(axis=1);q=np.quantile(sim,[.025,.975,.05/80,1-.05/80]);rec.update(dict(zip(['low95','high95','low_family','high_family'],map(float,q))));rec['finding']='lower_error' if q[3]<0 else 'higher_error' if q[2]>0 else 'uncertain'
    resamples.append(pd.DataFrame(dict(ident,replicate=np.arange(20000),difference=sim)))
   summary.append(rec)
 pd.DataFrame(rows).to_parquet(out/'date_differences.parquet',index=False);pd.DataFrame(blocks).to_parquet(out/'calendar_blocks.parquet',index=False);pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);pd.concat(resamples,ignore_index=True).to_parquet(out/'resamples.parquet',index=False)
 assert len(summary)==40
 js(out/'receipt.json',dict(status='PASS',family=40,replicates=20000,seed=35099,source_sha256=sha(source),calendar_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),protocol_sha256=sha(ROOT/'protocols/r257.json'),code_sha256=sha(__file__),adoption=False))
 print(pd.DataFrame(summary).groupby(['comparison','finding']).size().to_string())
if __name__=='__main__':run()
