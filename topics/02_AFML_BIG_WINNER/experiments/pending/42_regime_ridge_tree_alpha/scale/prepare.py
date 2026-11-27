"""Daily cohort and six observable scale series, rebuilt from EP36 archived market data."""
from scale_common import *
from ep41inputs import read
from prepare_inputs import compute

VOL=['vol5','vol20','vol60']

def main():
    fields='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()
    raw=[read(f) for f in fields]
    close=raw[0]
    features=compute(*raw,read('market').close)
    valid_count=np.zeros(close.shape,dtype=np.int16)
    for col in COLS:valid_count+=features[col].notna().to_numpy()
    eligible=raw[-1] & (close.gt(0)&np.isfinite(close)).rolling(61).sum().eq(61) & (close.shift(5)/close.shift(60)).ne(1) & (close/close.shift(5)).ne(1)
    eligible &= valid_count>=.8*len(COLS)
    key=pd.read_parquet(SCORES,columns=KEY)
    dates=pd.DatetimeIndex(sorted(key.signal_date.unique()))
    baseline=eligible.reindex(dates)
    assert int(baseline.sum().sum())==len(key)
    scale={}
    for col in VOL:
        x=features[col].where(eligible & features[col].gt(0))
        log=np.log(x)
        scale[col+'_m']=log.median(axis=1)
        scale[col+'_s']=log.quantile(.75,axis=1)-log.quantile(.25,axis=1)
    scale=pd.DataFrame(scale)
    scale.to_parquet(RES/'scale_clock.parquet')
    cohorts=[]
    for q in sorted(dates.to_period('Q').unique()):
        last=close.index.searchsorted(q.start_time)-1
        names=close.columns[eligible.iloc[last].to_numpy()]
        days=dates[dates.to_period('Q')==q]
        idx=close.index.get_indexer(days); js=close.columns.get_indexer(names)
        z=pd.DataFrame({'signal_date':np.repeat(days,len(js)),'instrument':np.tile(names,len(days)),
                        'observed':np.isfinite(close.to_numpy()[np.ix_(idx,js)]).ravel(),
                        'eligible':eligible.to_numpy()[np.ix_(idx,js)].ravel()})
        for col in STOCK:z[col]=features[col].to_numpy()[np.ix_(idx,js)].ravel()
        cohorts.append(z)
    atomic_parquet(pd.concat(cohorts,ignore_index=True),WORK/'fixed_cohort.parquet')
    eligible.to_parquet(RES/'eligible.parquet')
    print('fixed cohort and clock',len(dates),len(key))
if __name__=='__main__':main()
