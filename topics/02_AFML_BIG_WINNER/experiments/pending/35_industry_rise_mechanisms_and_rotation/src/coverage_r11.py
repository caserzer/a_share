"""Fixed-year profit revision data coverage only; no outcome evaluation."""
import pandas as pd
from common import *

def revisions_at(values,date):
    # Same broker and same explicit fiscal year; no EPS share-unit comparison.
    eligible=values[(values.basis=='profit_cny')&(values.publication_proxy_date<date)&values.broker.notna()].copy()
    rows=[]
    for key,g in eligible.groupby(['stock_code','broker','fiscal_year']):
        if key[2] not in [date.year,date.year+1]:continue
        # Conflicting simultaneous reports are not resolved by report id.
        dates=g.groupby('publication_proxy_date').value.agg(['nunique','first']).sort_index()
        dates.loc[dates['nunique']!=1,'first']=np.nan
        current=dates.iloc[-1];published=dates.index[-1]
        if (date-published).days>180 or pd.isna(current['first']):continue
        previous=dates.iloc[:-1];previous=previous[previous.index>=published-pd.Timedelta(days=365)]
        if previous.empty:continue
        old=previous.iloc[-1]['first'];denom=abs(old)+abs(current['first'])
        if pd.isna(old) or denom==0:continue
        rows.append(dict(stock_code=key[0],broker=key[1],fiscal_year=key[2],
            revision=(current['first']-old)/denom,latest_publication=published,previous_publication=previous.index[-1]))
    return pd.DataFrame(rows,columns=['stock_code','broker','fiscal_year','revision','latest_publication','previous_publication'])

def run():
    values=pd.read_parquet(ROOT/'data/r11_analyst_forecasts.parquet')
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=KEY+['date'])
    members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=['month','era','level','industry_code','security_id','instrument'])
    members['stock_code']=members.instrument.str[2:]
    companies=[];coverage=[]
    for date in sorted(panel.date.unique()):
        date=pd.Timestamp(date)
        if date<pd.Timestamp('2020-01-01'):continue
        rev=revisions_at(values,date)
        if len(rev):
            rev['date']=date;companies.append(rev)
        m=members[members.month==date.to_period('M')-1]
        for offset in [0,1]:
            v=rev[rev.fiscal_year==date.year+offset].groupby('stock_code').revision.median().rename('revision')
            joined=m.join(v,on='stock_code',validate='many_to_one')
            for key,g in joined.groupby(KEY):
                known=g.revision.notna().sum();n=len(g)
                coverage.append(dict(zip(KEY,key),date=date,fiscal_year=date.year+offset,fy_offset=offset,
                    members=n,known=int(known),coverage=known/n,eligible=bool(known>=5 and known/n>=.8),
                    covered_member_median=g.revision.median() if known else np.nan,full_factor=g.revision.median() if known>=5 and known/n>=.8 else np.nan))
    frame=pd.DataFrame(coverage);frame.to_parquet(ROOT/'data/r11_revision_coverage.parquet',index=False)
    pd.concat(companies,ignore_index=True).to_parquet(ROOT/'data/r11_company_broker_revisions.parquet',index=False)
    result=frame.groupby(['era','level','fy_offset']).agg(industry_dates=('eligible','size'),eligible=('eligible','sum'),
        any_coverage=('known',lambda x:int(x.gt(0).sum())),median_coverage=('coverage','median'),max_coverage=('coverage','max'))
    result.to_csv(ROOT/'outputs/r11/revision_coverage.csv')
    print(result.to_string(),flush=True)
if __name__=='__main__':run()
