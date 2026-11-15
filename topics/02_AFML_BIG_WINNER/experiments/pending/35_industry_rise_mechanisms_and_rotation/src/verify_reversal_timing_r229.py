from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r229';o=pd.read_parquet(out/'paths.parquet');d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');m=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=list(m.index);pos={x:i for i,x in enumerate(cal)};lookup={k:g.set_index('date') for k,g in d.groupby(KEY)};crossings=0
 for row in o.to_dict('records'):
  start=pos[row['date']]+1;dates=cal[start:start+21];z=lookup[tuple(row[k] for k in KEY)].reindex(dates);valid=len(dates)==21 and z.nav.notna().all() and z.block.nunique()==1;assert valid==(row['path_status']=='valid')
  if not valid:assert pd.isna(row['breach']);continue
  first=None
  for j,day in enumerate(dates):
   relative=(float(z.loc[day,'nav'])/float(z.iloc[0].nav))/(float(m.loc[day])/float(m.loc[dates[0]]))-1
   if relative<=-.08:first=j;break
  assert row['breach']==float(first is not None)
  if first is not None:assert row['entry_to_breach']==first and row['signal_to_breach']==first+1 and row['breach_date']==dates[first];crossings+=1
 a=pd.read_parquet(out/'alerts_and_paths.parquet');src=pd.read_parquet(ROOT/'outputs/r220/actions.parquet');cols=IDS+['industry_code','date','alert'];pd.testing.assert_frame_equal(a[cols].sort_values(cols[:-1]).reset_index(drop=True),src[cols].sort_values(cols[:-1]).reset_index(drop=True));dm=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);lookup={k:g for k,g in a.groupby(IDS+['date'])}
 for row in dm.to_dict('records'):
  g=lookup[tuple(row[k] for k in IDS+['date'])];v=g[g.path_status.eq('valid')];positive=v[v.breach.eq(1)];hits=positive[positive.alert];alerts=v[v.alert];assert len(hits)==row['hit'] and len(positive)-len(hits)==row['missed'] and int(alerts.breach.eq(0).sum())==row['false_alert'];assert np.isclose(hits.entry_to_breach.mean(),row['mean_entry_lead'],equal_nan=True);assert np.isclose(len(hits)/len(positive) if len(positive) else np.nan,row['recall'],equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',paths=len(o),crossings=crossings,source_rows=len(a),date_groups=len(dm),code_sha256=sha(__file__),scope='Scalar first-crossing dates, path eligibility, original alert identities and date hit/miss/lead/recall'))
 print(len(o),crossings,len(a),len(dm))
if __name__=='__main__':run()
