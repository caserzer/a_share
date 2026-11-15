from common import *
import pandas as pd
IDS=['family','era','level','cohort','method','task','horizon','objective']
STATES=['down_low','down_high','up_low','up_high']
def run():
 out=ROOT/'outputs/r208';out.mkdir(exist_ok=True);summaries=[];bins=[];support=[];coverage=[];inputs=[];maximum=0.;total=0
 for rnd in [196,199,200,201]:
  path=ROOT/f'outputs/r{rnd}/predictions.parquet';inputs.append(path);p=pd.read_parquet(path);p=p[p.task.isin(['onset','reversal'])].copy();total+=len(p)
  coverage.append(dict(round=rnd,classifier_predictions=len(p)))
  lp=ROOT/f'outputs/r{rnd}/fold_ledger.json';inputs.append(lp)
  for f in json.loads(lp.read_text()):
   if f['task'] not in ['onset','reversal']:continue
   for state in STATES:
    support.append({**{k:v for k,v in f.items() if k not in ['state_fit_dates','state_cal_dates']},'round':rnd,'regime':state,'state_fit_dates':f.get('state_fit_dates',{}).get(state,0),'state_cal_dates':f.get('state_cal_dates',{}).get(state,0)})
  if p.empty:continue
  for c in IDS:
   if c not in p:p[c]='not_applicable'
  assert p.prediction.between(0,1).all();assert p.y.dropna().isin([0,1]).all()
  for key,g in p.groupby(IDS+['variant'],dropna=False):
   ident=dict(zip(IDS+['variant'],key));ident['round']=rnd
   scopes=[('all','all',g)]+[('year',str(k),v) for k,v in g.groupby('year')]+[('state',k,v) for k,v in g.groupby('regime')]
   for scope,value,a in scopes:
    q=a[a.y.notna()].copy();meta=dict(ident,scope=scope,scope_value=value);n=q.date.nunique()
    if not n:continue
    w=1/(n*q.groupby('date').y.transform('size'));y=q.y.to_numpy();pr=q.prediction.to_numpy();wt=w.to_numpy();cl=np.clip(pr,1e-12,1-1e-12);b=np.minimum((pr*10).astype(int),9)
    ece=0.;br=0.;rate=0.;forecast=0.
    for i in range(10):
     mask=b==i;mass=float(wt[mask].sum());obs=float(wt[mask]@y[mask]/mass) if mass else np.nan;prob=float(wt[mask]@pr[mask]/mass) if mass else np.nan
     if mass:ece+=mass*abs(prob-obs);rate+=mass*obs;forecast+=mass*prob
     bins.append(dict(meta,bin=i,lower=i/10,upper=(i+1)/10,rows=int(mask.sum()),dates=int(q.loc[mask,'date'].nunique()),weight=mass,probability=prob,event_rate=obs))
    err=max(abs(rate-wt@y),abs(forecast-wt@pr),abs(wt.sum()-1));maximum=max(maximum,err);assert err<1e-12
    summaries.append(dict(meta,rows=len(a),known=len(q),dates=n,unknown=int(a.y.isna().sum()),event_rate=wt@y,probability=wt@pr,bias=wt@(pr-y),brier=wt@((pr-y)**2),logloss=-wt@(y*np.log(cl)+(1-y)*np.log1p(-cl)),ece=ece))
 s=pd.DataFrame(summaries);s.to_csv(out/'calibration.csv',index=False);pd.DataFrame(bins).to_csv(out/'reliability_bins.csv',index=False);pd.DataFrame(support).to_csv(out/'state_support.csv',index=False)
 ids=['round']+IDS+['scope','scope_value'];pairs=[]
 for key,g in s.groupby(ids,dropna=False):
  z=g.set_index('variant')
  for v in ['state','interaction']:
   if v not in z.index or 'base' not in z.index:continue
   pairs.append(dict(zip(ids,key),comparison=v+'-base',dates=int(z.loc[v,'dates']),brier_improvement=z.loc['base','brier']-z.loc[v,'brier'],logloss_improvement=z.loc['base','logloss']-z.loc[v,'logloss'],ece_improvement=z.loc['base','ece']-z.loc[v,'ece'],absolute_bias_improvement=abs(z.loc['base','bias'])-abs(z.loc[v,'bias'])))
 pd.DataFrame(pairs).to_csv(out/'paired_calibration.csv',index=False)
 js(out/'verification.json',dict(status='PASS',predictions=total,summary_rows=len(s),reconstruction_max_error=maximum,coverage=coverage,adoption=False,inputs={str(x):sha(x) for x in inputs+[ROOT/'protocols/r208.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['calibration.csv','reliability_bins.csv','state_support.csv','paired_calibration.csv']}))
 print('predictions',total,'summary rows',len(s));print(pd.DataFrame(pairs).query("scope=='all' and horizon==20 and comparison=='interaction-base'").groupby('round')[['brier_improvement','logloss_improvement','ece_improvement']].agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
