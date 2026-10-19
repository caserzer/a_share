"""R16 historical daily-derived features, no future information in predictors."""
import json
import numpy as np
import pandas as pd
from prepare_panel import DATA,OUT
from build_three_factor_panel import PANEL
from diagnose_prediction_target import DEST
FEATURE_PANEL=OUT/'local_cache/improvement_panel.parquet'


def run():
    base=pd.read_parquet(PANEL)
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(DATA/'qlib/cn_data_pit_largecap/calendars/day.txt',header=None)[0]))
    indices=pd.read_csv(DATA/'processed/index/benchmark_indices_daily.csv',parse_dates=['date'])
    market=pd.DataFrame(index=calendar)
    for name in ['csi300','all_a']:
        close=indices[indices.index_alias==name].set_index('date').close.reindex(calendar)
        returns=close.pct_change(fill_method=None)
        for n in [5,21,63,126,252]:market[f'{name}_mom{n}']=close/close.shift(n)-1
        for n in [21,63]:market[f'{name}_vol{n}']=returns.rolling(n).std()*np.sqrt(252)
        market[f'{name}_ma20']=close/close.rolling(20).mean()-1
        market[f'{name}_drawdown252']=close/close.rolling(252).max()-1
    benchmark=indices[indices.index_alias=='csi300'].set_index('date').close.reindex(calendar)
    mret=benchmark.pct_change(fill_method=None)
    pieces=[]
    for stock,g in base.groupby('instrument',sort=True):
        b=pd.read_csv(DATA/f'raw/akshare/day/qfq/{stock}.csv',parse_dates=['date']).set_index('date').reindex(calendar)
        close=b.close.where(b.close>0);r=close.pct_change(fill_method=None)
        f=pd.DataFrame(index=calendar)
        for n in [5,10]:f[f'reversal{n}']=close/close.shift(n)-1
        f['beta63']=r.rolling(63).cov(mret)/mret.rolling(63).var()
        f['beta252']=r.rolling(252).cov(mret)/mret.rolling(252).var()
        f['idio_vol63']=np.sqrt((r.rolling(63).var()-r.rolling(63).cov(mret)**2/mret.rolling(63).var()).clip(lower=0))*np.sqrt(252)
        f['skew63']=r.rolling(63).skew()
        f['downvol63']=np.sqrt((r.clip(upper=0)**2).rolling(63).mean())*np.sqrt(252)
        f['up_fraction21']=(r>0).astype(float).where(r.notna()).rolling(21).mean()
        f['ma20_distance']=close/close.rolling(20).mean()-1
        for n in [21,63,126]:f[f'relative_mom{n}']=close/close.shift(n)-benchmark/benchmark.shift(n)
        f=f.join(market).reindex(pd.DatetimeIndex(g.date));f.index.name='date'
        joined=g.merge(f.reset_index(),on='date',how='left',validate='one_to_one')
        for h in [1,3,6]:
            joined[f'market_label_{h}']=benchmark.reindex(pd.DatetimeIndex(joined[f'end_{h}'])).to_numpy()/benchmark.reindex(joined.date).to_numpy()-1
        pieces.append(joined)
    panel=pd.concat(pieces,ignore_index=True).replace([np.inf,-np.inf],np.nan)
    panel.to_parquet(FEATURE_PANEL,index=False)
    market.to_parquet(OUT/'local_cache/improvement_market_features.parquet')
    required=['beta63','idio_vol63','reversal5','relative_mom21','csi300_mom21','all_a_mom21']
    g=panel[panel.common_eligible & (panel.date>='2021-01-01')]
    (DEST/'new_feature_audit.json').write_text(json.dumps(dict(prediction_rows=len(g),missing_by_feature=g[required].isna().sum().to_dict(),
        feature_semantics='rolling historical price/market features; market_label_* are outcomes, excluded from predictors'),indent=2)+'\n')
    print(len(panel),len(g),g[required].isna().sum().to_dict())


if __name__=='__main__':run()
