from common import *
import pandas as pd

def states(close):
 ret=close.pct_change(fill_method=None);vol=ret.rolling(21,min_periods=21).std();threshold=vol.shift(1).rolling(252,min_periods=126).median();trend=close/close.shift(63)-1
 frame=pd.DataFrame(dict(trend63=trend,vol21=vol,prior_vol_median=threshold));valid=frame.notna().all(axis=1)
 frame['regime']=pd.Series(None,index=frame.index,dtype='object');frame.loc[valid,'regime']=[('up' if a>=0 else 'down')+'_'+('high' if b>=c else 'low') for a,b,c in frame.loc[valid,['trend63','vol21','prior_vol_median']].itertuples(index=False,name=None)]
 frame['known_at']=frame.index;return frame

def run():
 out=ROOT/'outputs/r195';out.mkdir(exist_ok=True);source=CACHE/'forecast_v5/CSI_ALL.parquet';close=pd.read_parquet(source).close.sort_index();assert close.index.is_unique and close.notna().all()
 result=states(close);result.index.name='date';result.to_parquet(out/'market_regimes.parquet')
 # Every month-end is rebuilt from its own prefix, excluding all future values.
 ends=pd.Series(close.index,index=close.index).groupby(close.index.to_period('M')).max();checks=0
 for date in ends:
  expected=states(close.loc[:date]).iloc[-1];actual=result.loc[date]
  for c in ['trend63','vol21','prior_vol_median']:assert np.isclose(expected[c],actual[c],atol=1e-14,equal_nan=True)
  assert (pd.isna(expected.regime) and pd.isna(actual.regime)) or expected.regime==actual.regime;checks+=1
 # Coverage of every frozen core prediction, not just successful groups.
 p=pd.read_parquet(ROOT/'outputs/r131/predictions.parquet');x=p.merge(result.reset_index()[['date','regime']],on='date',how='left',validate='many_to_one');x['regime']=x.regime.fillna('unknown')
 x.groupby(['era','level','task','horizon','regime']).agg(rows=('prediction','size'),origins=('date','nunique')).reset_index().to_csv(out/'core_prediction_coverage.csv',index=False)
 result.assign(year=result.index.year,state=result.regime.fillna('unknown')).groupby(['year','state']).size().rename('days').to_csv(out/'annual_state_counts.csv')
 js(out/'verification.json',dict(status='PASS',scope='Every month-end prefix rebuild equals full calculation; no future threshold, state coverage not performance',prefix_checks=checks,rows=len(result),known=int(result.regime.notna().sum()),unknown_core_prediction_rows=int(x.regime.eq('unknown').sum()),inputs={str(source):sha(source),'protocols/r195.json':sha(ROOT/'protocols/r195.json'),'src/regimes_r195.py':sha(__file__)},outputs={f:sha(out/f) for f in ['market_regimes.parquet','core_prediction_coverage.csv','annual_state_counts.csv']},adoption=False))
 print('REGIMES',len(result),checks,'prefix checks; core unknown',int(x.regime.eq('unknown').sum()))
if __name__=='__main__':run()
