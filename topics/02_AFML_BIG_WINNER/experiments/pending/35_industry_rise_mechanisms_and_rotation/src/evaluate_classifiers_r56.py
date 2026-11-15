import pandas as pd
from common import *
from evaluate_r02 import binary_metrics
from evaluate_size_r31 import interval

def run():
 out=ROOT/'outputs/r56';p=pd.read_parquet(out/'predictions.parquet');p['alert']=False;dates=[];cal=[];summary=[];annual=[]
 keys=['era','level','task','horizon','method']
 for key,g in p.groupby(keys+['date']):
  selected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(max(1,int(np.ceil(len(g)*.2)))).index;p.loc[selected,'alert']=True
  q=g.dropna(subset=['y']);dates.append(dict(zip(keys+['date'],key),n=len(q),brier=((q.prediction-q.y)**2).mean(),baseline=((q.training_mean-q.y)**2).mean()))
 for key,g in p.groupby(keys):
  summary.append(dict(zip(keys,key),**binary_metrics(g)));v=g.dropna(subset=['y']).copy();v['bin']=np.minimum((v.prediction*10).astype(int),9)
  for bucket,z in v.groupby('bin'):cal.append(dict(zip(keys,key),bin=bucket,n=len(z),prediction=z.prediction.mean(),observed=z.y.mean()))
 for key,g in p.groupby(keys+['year']):annual.append(dict(zip(keys+['year'],key),**binary_metrics(g)))
 d=pd.DataFrame(dates);d.to_csv(out/'date_metrics.csv',index=False);pd.DataFrame(summary).to_csv(out/'summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False);pd.DataFrame(cal).to_csv(out/'calibration.csv',index=False)
 inc=[];paired=[]
 for key,g in d.groupby(keys[:-1]):
  wide=g.pivot(index='date',columns='method',values='brier')
  for name,a,b in [('diffusion_with_market_controls','FSM','FSMD'),('diffusion_with_size','FS','FSD')]:
   z=wide[a]-wide[b];lo,hi=interval(z,3 if key[3]==20 else 6);half=(hi-lo)/2*2.807033768343811/2.5758293035489004;lo=z.mean()-half;hi=z.mean()+half
   inc.append(dict(zip(keys[:-1],key),comparison=name,months=int(z.count()),brier_reduction=z.mean(),low995=lo,high995=hi,result='historical_support' if key[3]==20 and z.count()>=24 and lo>0 else 'not_established' if key[3]==20 else 'secondary_descriptive'))
   for date,v in z.items():paired.append(dict(zip(keys[:-1],key),comparison=name,date=date,brier_reduction=v))
 pd.DataFrame(inc).to_csv(out/'increments.csv',index=False);pd.DataFrame(paired).to_csv(out/'paired_by_date.csv',index=False)
 print(pd.DataFrame(inc).query("comparison=='diffusion_with_market_controls'").to_string(index=False))
if __name__=='__main__':run()
