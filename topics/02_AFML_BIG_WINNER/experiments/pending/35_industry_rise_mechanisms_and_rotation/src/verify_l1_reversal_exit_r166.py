"""Independent scalar path, selection and cash-wealth verification."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r166';receipt=json.loads((out/'receipt.json').read_text())
 for path,h in receipt['reads'].items():assert sha(path)==h
 p=pd.read_parquet(out/'followup.parquet');d=pd.read_parquet(ROOT/'data/l1_daily.parquet');b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
 checked=0
 for row in p.to_dict('records'):
  g=d[d.industry_code.eq(row['industry_code'])&d.block.eq(row['block'])].sort_values('date').reset_index(drop=True)
  ix=g.index[g.date.eq(row['date'])].item();window=g.iloc[ix+1:ix+62]
  if len(window)!=61:
   assert pd.isna(row['return60']) and pd.isna(row['market60']);continue
  nav=window.nav.tolist();ret=nav[-1]/nav[0]-1;bm=b.loc[window.date.iloc[-1]]/b.loc[window.date.iloc[0]]-1
  peak=nav[0];dd=0
  for value in nav:peak=max(peak,value);dd=min(dd,value/peak-1)
  for name,expected in [('return60',ret),('market60',bm),('excess60',ret-bm),('drawdown60',dd)]:assert np.isclose(row[name],expected,atol=1e-12)
  checked+=1
 for date,g in p.groupby('date'):
  chosen=sorted(g.to_dict('records'),key=lambda x:(-x['raw_score'],x['industry_code']))[:int(np.ceil(len(g)/5))]
  assert set(g.loc[g.alert,'industry_code'])=={x['industry_code'] for x in chosen}
 dates=pd.read_csv(out/'date_metrics.csv',parse_dates=['date'])
 for row in dates.to_dict('records'):
  z=p[p.date.eq(row['date'])]
  if row['cohort']=='risk_alert':z=z[z.alert]
  if row['cohort']=='not_alert':z=z[~z.alert]
  q=z.dropna(subset=['return60','market60']);assert (row['origins'],row['complete'],row['unknown'])==(len(z),len(q),len(z)-len(q))
  c=row['cost'];cash=[];switch=[]
  for x in q.to_dict('records'):
   hold=(1+x['return60'])*(1-c);cash.append(1-c-hold);switch.append((1-c)*(1-c)*(1+x['market60'])*(1-c)-hold)
  for name,values in [('cash_improvement',cash),('market_improvement',switch)]:assert np.isclose(row[name],np.mean(values) if values else np.nan,equal_nan=True)
 summary=pd.read_csv(out/'date_summary.csv').set_index(['cohort','cost'])
 for key,g in dates.groupby(['cohort','cost']):
  for col in summary.columns:
   val=g.cash_improvement.count() if col=='months' else g[col].mean();assert np.isclose(summary.loc[key,col],val,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',independent_complete_paths=checked,origins=len(p),date_metric_rows=len(dates),calibrated=False,adoption=False))
 print('PASS independent paths and exit economics',checked,len(dates))
if __name__=='__main__':run()
