from common import *
import pandas as pd
from scipy.stats import spearmanr

def run():
 out=ROOT/'outputs/r202';f=pd.read_parquet(out/'sensitivities.parquet');maximum=0.
 for row in f.itertuples():
  x=(np.array(row.current_macro)-np.array(row.mean))/np.array(row.scale);u=[float(row.regime==s) for s in ['down_high','up_low','up_high']];a=list(x)
  if row.variant!='base':a+=u
  if row.variant=='interaction':a+=[v*flag for flag in u for v in x]
  value=float((np.array(a)-np.array(row.design_mean))@np.array(row.coef));err=abs(value-row.conditioned);assert err<1e-12;maximum=max(maximum,err);assert row.fit_last_date<row.date
 rawroot=ROOT/'outputs/r158/evaluation/data';raw=pd.concat([pd.read_parquet(rawroot/'monthly_panel.parquet'),pd.read_parquet(rawroot/'l1_monthly_panel.parquet')],ignore_index=True);raw.index.name='row_id'
 p=pd.read_parquet(out/'scores.parquet');keys=['era','level','date','lag','variant','method'];groups={k:g for k,g in p.groupby(keys)};d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);errmax=0.
 for key,z in groups.items():
  rawz=raw.loc[z.row_id];rank=(rawz[['mom20','mom60','vol20','dd60']].rank()-.5)/len(rawz)-.5;base=((rank.mom20+rank.mom60)/2-rank.vol20+rank.dd60)/3
  if key[-1]=='F':expected=base.to_numpy()
  else:
   feature=f[f.lag.eq(key[3])&f.variant.eq(key[4])].set_index('row_id').loc[z.row_id,'exposure' if key[-1]=='F_exposure' else 'conditioned'];factor=(feature.rank()-.5)/len(feature)-.5;expected=(base.to_numpy()+factor.to_numpy())/2
  assert np.allclose(expected,z.score,atol=1e-12)
 for row in d.to_dict('records'):
  z=groups[tuple(row[k] for k in keys)];known=z[f"excess{row['horizon']}"].notna();v=z[known];top=z[z.selected];expected=z.sort_values(['score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(z))));assert set(top.industry_code)==set(expected.industry_code)
  y=f"excess{row['horizon']}";ic=spearmanr(v.score,v[y]).statistic if len(v)>=20 and v.score.nunique()>1 and v[y].nunique()>1 else np.nan;value=sum(top[y])/len(top) if top[y].notna().all() else np.nan
  for a,b in [(ic,row['ic']),(value,row['top_excess'])]:
   assert np.isclose(a,b,atol=1e-12,equal_nan=True)
   if pd.notna(a):errmax=max(errmax,abs(a-b))
 js(out/'independent_verification.json',dict(status='PASS',saved_parameter_scores=len(f),score_max_error=maximum,metrics=len(d),metric_max_error=errmax,scope='all current design scores, prior fit dates, selected identities, IC and complete top forward means; does not independently refit historical windows',code_sha256=sha(__file__)))
 print(len(f),len(d),maximum,errmax)
if __name__=='__main__':run()
