"""Separate queried historical basket coverage from certified pre-close exposure."""
import pandas as pd
import numpy as np
from fetch import HERE,REG,OUT,FUNDS,hashlib,json
def main():
    score=pd.read_parquet(REG/'p2/results/scores.parquet')
    legs=pd.read_parquet(REG/'p2/results/next_rebalance.parquet')
    legs=legs[legs.arm=='rank']
    assert not legs.duplicated(['entry_idx','instrument']).any()
    days=pd.read_parquet(next(REG.parent.glob('36_*/private/market.parquet')),columns=[]).index
    shares=pd.read_parquet(OUT/'fund_share.parquet')
    nav=pd.read_parquet(OUT/'fund_nav.parquet')
    pcfs=pd.concat([pd.read_parquet(OUT/(f'etf_{market}_cons.parquet')) for market in FUNDS.values()],ignore_index=True)
    dates=sorted(pcfs.trade_date.unique())
    rows=[];stocks=[];budgets=[]
    for date in dates:
        signal=pd.Timestamp(date);g=score[score.signal_date==signal].sort_values(['R','instrument'],ascending=False)
        idx=days.get_loc(signal);k=len(g)//10;e=idx+1
        reserve=g.iloc[k:2*k].copy()
        covered=set();physical=set()
        sample=pcfs[pcfs.trade_date==date]
        prev=days[idx-1].strftime('%Y%m%d')
        for fund,grp in sample.groupby('ts_code'):
            sh=shares[shares.ts_code==fund].set_index('trade_date')
            nv=nav[nav.ts_code==fund].set_index('nav_date')
            history=[d.strftime('%Y%m%d') for d in days[idx-6:idx]]
            # Conservative availability sensitivity uses shares through t-1.
            values=sh.fd_share.reindex(history)
            previous_nav=nv.loc[prev] if prev in nv.index else None
            ann=str(previous_nav.ann_date) if previous_nav is not None else ''
            ids=grp.con_code.str.extract(r'^(\d{6})\.(SH|SZ)$')
            names=ids[1]+ids[0];present=names.notna()
            basket=set(names[present]);covered|=basket
            qty=pd.to_numeric(grp.qty,errors='coerce')
            proxies=set(names[present & (qty>0)&grp.sub_flag.eq('允许')])
            physical|=proxies
            rows.append(dict(date=date,fund=fund,pcf_rows=len(grp),equity_rows=int(present.sum()),
                             qty_and_allowed=len(proxies),cash_only_or_other=len(grp)-len(proxies),
                             reserve=len(reserve),overlap=sum(reserve.instrument.isin(basket)),overlap_qty_and_allowed=sum(reserve.instrument.isin(proxies)),
                             lagged6_share_dates=values.notna().sum(),lagged_5day_fd_share_delta=values.iloc[-1]-values.iloc[0],
                             prev_nav=previous_nav.unit_nav if previous_nav is not None else np.nan,
                             prev_nav_announcement_date=ann,prev_nav_ann_before_signal=ann<date if ann else False,
                             prev_nav_ann_on_signal=ann==date,pcf_first_version_certified=False,share_first_publication_certified=False,
                             unit_header_verified=False))
            for name in reserve.instrument:stocks.append((date,fund,name,name in basket,name in proxies))
        buy=legs[legs.entry_idx==e]
        budgets.append(dict(date=date,entry_idx=e,reserve=len(reserve),basket_name_coverage=sum(reserve.instrument.isin(covered)),
                            potential_quantity_coverage=sum(reserve.instrument.isin(physical)),actual_ridge_candidate_buys=len(buy),
                            planned_ridge_leg=buy.planned.sum(),filled_ridge_leg=buy.bought.sum(),
                            filled_name_overlap=buy.loc[buy.instrument.isin(covered),'bought'].sum(),
                            filled_qty_and_allowed_overlap=buy.loc[buy.instrument.isin(physical),'bought'].sum(),
                            strict_signal_budget=0.))
    dates_expected=pd.Series(sorted(score.signal_date.unique())).groupby(lambda i:pd.Timestamp(sorted(score.signal_date.unique())[i]).to_period('Q')).min()
    assert set(pd.to_datetime(dates))==set(pd.to_datetime(dates_expected))
    pd.DataFrame(rows).to_csv(OUT/'date_fund_coverage.csv',index=False)
    pd.DataFrame(budgets).to_csv(OUT/'candidate_budget.csv',index=False)
    pd.DataFrame(stocks,columns='date fund instrument present qty_and_allowed'.split()).to_parquet(OUT/'reserve_overlap.parquet',index=False)
    r=pd.DataFrame(rows);b=pd.DataFrame(budgets)
    print(r[['pcf_rows','equity_rows','qty_and_allowed','lagged6_share_dates','prev_nav_ann_before_signal','prev_nav_ann_on_signal']].sum())
    print(b.drop(columns=['date','entry_idx']).sum())
    files=[HERE/'fetch.py',HERE/'audit.py',REG/'p2/results/scores.parquet',REG/'p2/results/next_rebalance.parquet']+sorted(f for f in OUT.iterdir() if f.is_file() and f.name!='verification.json')
    (OUT/'verification.json').write_text(json.dumps({str(f):hashlib.file_digest(open(f,'rb'),'sha256').hexdigest() for f in files},indent=2)+'\n')
if __name__=='__main__':main()
