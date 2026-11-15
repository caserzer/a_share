from common import *
import pandas as pd
from scipy.stats import norm

def run():
 out=ROOT/'outputs/r223';raw=pd.read_parquet(out/'paired_dates.parquet');monthly=pd.read_parquet(out/'monthly_deltas.parquet');summary=pd.read_csv(out/'uncertainty.csv');ident=[c for c in monthly if c not in ['month','delta','valid_dates','planned_dates','case_id']];lookup={k:g for k,g in raw.groupby(ident+['month'])};maximum=0.
 for row in monthly.to_dict('records'):
  g=lookup[tuple(row[k] for k in ident+['month'])];values=g.delta.dropna().tolist();mean=sum(values)/len(values) if values else np.nan;assert len(values)==row['valid_dates'] and len(g)==row['planned_dates'];assert np.isclose(mean,row['delta'],atol=1e-12,equal_nan=True)
 for row in summary.to_dict('records'):
  z=monthly[monthly.case_id.eq(row['case_id'])].dropna(subset=['delta']);values=z.delta.to_numpy();n=len(z);mu=values.mean() if n else np.nan;assert n==row['months'] and np.isclose(mu,row['mean'],atol=1e-12,equal_nan=True)
  if n>=2:
   dates=pd.PeriodIndex(z.month,freq='M').asi8;u=values-mu;variance=sum(float(u[i]*u[j])*max(0.,1-abs(int(dates[i]-dates[j]))/7.) for i in range(n) for j in range(n));se=np.sqrt(max(0,variance))/n;assert np.isclose(se,row['se'],atol=1e-12);maximum=max(maximum,abs(se-row['se']))
  if row['eligible']:
   critical=norm.isf(.05/(2*len(summary)));assert np.isclose(mu-critical*row['se'],row['adjusted_low'],atol=1e-12)
 js(out/'independent_verification.json',dict(status='PASS',monthly_rows=len(monthly),cases=len(summary),max_se_error=maximum,scope='All monthly paired-date means/counts, all case means, direct double-sum calendar HAC and adjusted lower intervals',code_sha256=sha(__file__)))
 print(len(monthly),len(summary),maximum)
if __name__=='__main__':run()
