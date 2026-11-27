"""Fixed direction on each source; controls keep the original buy if a signal is missing."""
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent))
from reserves import *
from fetch import RANGES
def main():
    m,cards=prepare()
    raw=pd.read_parquet(OUT/'five_minute_daily.parquet')
    raw['date']=pd.to_datetime(raw.date)
    rawc=pd.read_parquet(PRIVATE/'close.parquet').reindex(index=m.days,columns=m.symbols)
    raw['reference_close']=rawc.to_numpy()[m.days.get_indexer(raw.date),m.symbols.get_indexer(raw.instrument)]
    raw['reference_known']=raw.reference_close.gt(0)
    raw['endprice_diff']=raw['last']-raw.reference_close
    raw['accepted']=raw.reference_known & raw.endprice_diff.abs().le(.011)
    raw.groupby(raw.date.dt.year).agg(days=('date','size'),reference_known=('reference_known','sum'),accepted=('accepted','sum'),max_abs_error=('endprice_diff',lambda v:v.abs().max())).to_csv(OUT/'close_checks.csv')
    raw.loc[~raw.accepted,['date','instrument','last','reference_close','endprice_diff']].to_csv(OUT/'close_exceptions.csv',index=False)
    raw=raw[raw.accepted].copy()
    def panel(col):
        return raw.pivot(index='date',columns='instrument',values=col).reindex(index=m.days,columns=m.symbols)
    ss=panel('sum_ss');neg=panel('negative_ss')
    neg5=neg.rolling(5).sum();ss5=ss.rolling(5).sum();r=panel('sum_r').rolling(5).sum()
    n=panel('n').rolling(5).sum();avg=r/n
    var=ss5/n-avg**2
    forecasts={
        'less_down_5':-neg5/ss5.replace(0,np.nan),
        'less_down_20':-neg.rolling(20).sum()/ss.rolling(20).sum().replace(0,np.nan),
        'positive_skew_5':(panel('sum_cube').rolling(5).sum()/n-3*avg*(ss5/n)+2*avg**3)/(var**1.5),
        'close_above_vwap_5':panel('vwap_gap').rolling(5).mean(),
        'positive_open30_5':panel('open30').rolling(5).mean(),
        'up_amount_5':panel('up_amount').rolling(5).sum()/panel('amount').rolling(5).sum(),
        'positive_ret_volume_corr_5':panel('ret_volume_corr').rolling(5).mean(),
    }
    close=pd.DataFrame(m.c,index=m.days,columns=m.symbols)
    ret=close.pct_change(fill_method=None)
    daily_proxy=-ret.clip(upper=0).pow(2).rolling(5).sum()/ret.pow(2).rolling(5).sum().replace(0,np.nan)
    forecasts['daily_ohlcv_proxy_5']=daily_proxy.where(forecasts['less_down_5'].notna())
    plans={name:{} for name in ['rank','ridge',*forecasts]};statsrows=[];choices=[]
    ranges=[m.days.get_indexer([a,b]) for a,b in RANGES]
    ridge=pd.read_parquet(HERE.parent/'p2/results/scores.parquet').groupby('entry_idx')
    for e,core,p,n_buy in cards:
        if not any(a<=e<=b-10 for a,b in ranges):continue
        rr=p.instrument.to_numpy();cols=m.symbols.get_indexer(rr)
        plans['rank'][e]=m.symbols.get_indexer(np.r_[core,rr[:n_buy]])
        g=ridge.get_group(e).sort_values(['R','instrument'],ascending=False)
        plans['ridge'][e]=m.symbols.get_indexer(g.head(len(g)//10).instrument)
        for name,pan in forecasts.items():
            score=pan.iloc[e-1].to_numpy()[cols].copy()
            score[~np.isfinite(score)]=np.nan
            picks=choose(p,n_buy,score,'n1')
            plans[name][e]=m.symbols.get_indexer(np.r_[core,rr[picks]])
            valid=np.isfinite(score)
            statsrows.append(dict(spec=name,entry_idx=e,date=m.days[e-1],reserves=len(p),covered=valid.sum(),base_slots=n_buy,covered_slots=valid[:n_buy].sum(),changes=len(set(picks)-set(range(n_buy)))))
            for j,s in enumerate(rr):
                choices.append((e,name,s,score[j],j<n_buy,j in picks))
    pd.DataFrame(statsrows).to_csv(OUT/'coverage.csv',index=False)
    pd.DataFrame(choices,columns='entry_idx spec instrument score baseline_buy selected'.split()).to_parquet(OUT/'choices.parquet',index=False)
    evaluate(m,plans,RANGES,OUT)
if __name__=='__main__':main()
