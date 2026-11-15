from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
from regime_onset_persistence_r228 import METRICS

def run():
 out=ROOT/'outputs/r228';o=pd.read_parquet(out/'paths.parquet');d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');m=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=list(m.index);positions={v:i for i,v in enumerate(cal)};lookup={k:g.set_index('date') for k,g in d.groupby(KEY)};checks=0;maximum=0.
 for row in o.to_dict('records'):
  pos=positions[row['date']];g=lookup[tuple(row[c] for c in KEY)]
  for h in [5,20,60]:
   dates=cal[pos+1:pos+h+2];z=g.reindex(dates);valid=len(dates)==h+1 and z.nav.notna().all() and z.block.nunique()==1
   assert valid==(row['status'+str(h)]=='valid')
   if not valid:continue
   prices=z.nav.tolist();bench=m.loc[dates].tolist();peak=prices[0];dd=0.
   for value in prices:peak=max(peak,value);dd=min(dd,value/peak-1)
   ret=prices[-1]/prices[0]-1;market=bench[-1]/bench[0]-1
   for name,value in [('return',ret),('market',market),('excess',ret-market),('drawdown',dd),('min_from_entry',min(prices)/prices[0]-1)]:
    assert np.isclose(row[name+str(h)],value,atol=1e-12);maximum=max(maximum,abs(row[name+str(h)]-value));checks+=1
  c=(1+row['return60'])/(1+row['return20'])-1;ce=c-((1+row['market60'])/(1+row['market20'])-1)
  assert np.isclose(row['continuation20_60'],c,atol=1e-12,equal_nan=True) and np.isclose(row['continuation_excess20_60'],ce,atol=1e-12,equal_nan=True)
 a=pd.read_parquet(out/'alert_followup.parquet');source=pd.read_parquet(ROOT/'outputs/r221/actions.parquet');cols=IDS+['industry_code','date'];assert len(a)==int(source.alert.sum());pd.testing.assert_frame_equal(a[cols].sort_values(cols).reset_index(drop=True),source[source.alert][cols].sort_values(cols).reset_index(drop=True))
 dates=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);lookup={k:g for k,g in a.groupby(IDS+['date'])};metricchecks=0
 for row in dates.to_dict('records'):
  g=lookup[tuple(row[c] for c in IDS+['date'])];v=g if row['followup_cohort']=='all' else g[g.success20.eq(1 if row['followup_cohort']=='success20' else 0)]
  for metric in METRICS:
   x=v[metric].dropna();value=sum(x)/len(x) if len(x) else np.nan;assert len(x)==row[metric+'_known'] and len(v)-len(x)==row[metric+'_unknown'];assert np.isclose(value,row[metric],atol=1e-12,equal_nan=True);metricchecks+=1
 js(out/'independent_verification.json',dict(status='PASS',paths=len(o),path_values=checks,max_error=maximum,alerts=len(a),date_metric_checks=metricchecks,scope='Independent calendar reindex, scalar paths, alert identity, continuation formulas and date means/counts',code_sha256=sha(__file__)))
 print(len(o),checks,len(a),metricchecks,maximum)
if __name__=='__main__':run()
