import pandas as pd
from common import *
from market_controls_r54 import features

def run():
 out=ROOT/'outputs/r54';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 p=pd.read_parquet(ROOT/'data/r54_market_controls.parquet');assert sha(ROOT/'data/r54_market_controls.parquet')==rec['feature_sha256']
 assert not {'return20','return60','excess20','excess60','maturity20','maturity60'}&set(p)
 market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet',columns=['close']).close;assert market.gt(0).all()
 d=pd.concat([pd.read_parquet(x,columns=KEY+['date','block','nav']) for x in [CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet']],ignore_index=True)
 groups={k:g.sort_values('date').reset_index(drop=True) for k,g in d.groupby(KEY+['block'])};sample=p[p.market_controls_complete].groupby(['era','level'],group_keys=False).sample(n=20,random_state=54);maximum=0.
 for x in sample.to_dict('records'):
  g=groups[tuple(x[k] for k in KEY+['block'])];i=int(g.index[g.date.eq(x['date'])][0]);w=g.iloc[i-126:i+1];assert len(w)==127
  positions=market.index.get_indexer(w.date);assert (np.diff(positions)==1).all();a=w.nav.to_numpy();b=market.reindex(w.date).to_numpy();ar=a[1:]/a[:-1]-1;br=b[1:]/b[:-1]-1
  design=np.column_stack([np.ones(126),br]);coef=np.linalg.lstsq(design,ar,rcond=None)[0];res=ar-design@coef;vol=np.sqrt((res@res)/125*252)
  error=max(abs(coef[1]-x['market_beta126']),abs(vol-x['residual_vol126']));maximum=max(maximum,error);assert error<1e-9
 # Causality and gaps with known linear market relation.
 idx=pd.bdate_range('2020-01-01',periods=300);returns=.002*np.sin(np.arange(300)/7)+.0001;mk=pd.Series(100*np.cumprod(1+returns),index=idx);nav=100*np.cumprod(1+1.5*returns)
 g=pd.DataFrame({'date':idx,'nav':nav});a=features(g,mk);assert abs(a.market_beta126.iloc[-1]-1.5)<1e-10
 changed=g.copy();changed.loc[200:,'nav']*=1.2;b=features(changed,mk);assert np.allclose(a.market_beta126.iloc[:200],b.market_beta126.iloc[:200],equal_nan=True)
 gap=features(g.drop(index=130),mk);assert gap.loc[gap.date.between(idx[131],idx[256]),'market_beta126'].isna().all();assert pd.notna(gap.loc[gap.date.eq(idx[257]),'market_beta126'].iloc[0])
 assert p.loc[~p.market_controls_complete,['market_beta126','residual_vol126']].isna().all().all()
 js(out/'verification.json',dict(status='PASS',direct_OLS_windows=len(sample),absolute_error_bound=1e-9,future_perturbation_invariant=True,gap_no_fill=True,no_outcomes_read=True,scope='partial historical proxy market controls, not full styles or predictive evidence'))
 print('R54 VERIFIED',len(sample),'OLS windows; max error',maximum)
if __name__=='__main__':run()
