"""Independently reconstruct every repaired macro sensitivity via normal equations."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r158';root=out/'evaluation';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 assert sha(ROOT/'protocols/r13.json')==sha(root/'protocols/r13.json')
 panel=pd.concat([pd.read_parquet(root/'data/monthly_panel.parquet'),pd.read_parquet(root/'data/l1_monthly_panel.parquet')],ignore_index=True)
 old_panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');new_panel=pd.read_parquet(root/'data/monthly_panel.parquet');pairs=old_panel.merge(new_panel,on=KEY+['date'],how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');both=pairs[pairs._merge.eq('both')];changed=both[~np.isclose(both.past_excess20_old,both.past_excess20_new,atol=1e-12,rtol=1e-10,equal_nan=True)];changed[KEY+['date','past_excess20_old','past_excess20_new']].to_csv(out/'historical_fit_input_changes.csv',index=False)
 states=pd.read_parquet(root/'data/r13_macro_states.parquet');features=pd.read_parquet(root/'data/r13_sensitivities.parquet');groups={k:g for k,g in panel.groupby(KEY)};checked=0;maxerror=0.
 for key,features_g in features.groupby(KEY+['lag']):
  st=states[states.lag.eq(key[-1])];g=groups[key[:3]].merge(st,on='date',validate='one_to_one').sort_values('date');h=g.dropna(subset=['lag_pmi','lag_money','past_excess20']);dates=h.date.to_numpy();x=h[['lag_pmi','lag_money']].to_numpy();y=h.past_excess20.to_numpy();current=g.set_index('date')[['pmi','money']]
  for row in features_g.itertuples():
   mask=(dates<row.date.to_datetime64())&(dates>=(row.date-pd.DateOffset(months=36)).to_datetime64());xx=x[mask];yy=y[mask];mu=xx.mean(axis=0);sd=xx.std(axis=0);z=(xx-mu)/sd;coef=np.linalg.solve(z.T@z+np.eye(2),z.T@(yy-yy.mean()));values=np.array([coef.mean(),coef@((current.loc[row.date].to_numpy()-mu)/sd)]);err=float(np.max(np.abs(values-[row.exposure,row.conditioned])));maxerror=max(maxerror,err)
   assert len(xx)==row.n_fit and err<1e-10 and np.allclose(coef,row.coef,atol=1e-10) and np.allclose(mu,row.mu) and np.allclose(sd,row.sd)
   assert pd.Timestamp(dates[mask].max())==row.fit_last_date and row.fit_last_date<row.date;checked+=1
 for name,keys in [('coverage',['era','level','date']),('date_metrics',['era','level','date','lag','method','horizon']),('increments',['era','level','lag','horizon','baseline'])]:
  old=pd.read_csv(ROOT/f'outputs/r13/{name}.csv');new=pd.read_csv(root/f'outputs/r13/{name}.csv');expected=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');actual=pd.read_csv(out/f'{name}_comparison.csv');pd.testing.assert_frame_equal(expected.assign(_merge=expected._merge.astype(str)),actual,check_dtype=False,rtol=1e-10,atol=1e-12)
 assert json.loads((root/'outputs/r13/verification.json').read_text())['status']=='PASS'
 js(out/'verification.json',dict(status='PASS',all_sensitivity_normal_equation_checks=checked,max_error=maxerror,scope='Every repaired exposure, conditioned score, coefficients, normalization and historical fit window; all comparison tables; original full selection verifier',verifier_sha256=sha(Path(__file__))))
 print('R158 VERIFIED',checked,maxerror)
if __name__=='__main__':run()
