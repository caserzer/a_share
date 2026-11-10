"""Independent numerical checks of forward price, drawdown, beta and causality."""
from common31 import *


def run():
    outcome=pd.read_parquet(CACHE/'outcomes.parquet')
    observations=pd.read_parquet(CACHE/'observations.parquet').set_index('row_id')
    daily=pd.read_parquet(OLD/'daily_industries.parquet')
    paths={k:g.set_index('date').nav.sort_index() for k,g in daily.groupby(KEY)}
    indexes={bm:pd.read_parquet(OLD/f'{bm}.parquet').close.sort_index() for bm in ['CSI300','CSI_ALL']}
    checks=[]
    for r in outcome[outcome.outcome_status.eq('OK')].sample(180,random_state=32).itertuples():
        origin=observations.loc[r.row_id];p=paths[tuple(origin[k] for k in KEY)];b=indexes[r.benchmark]
        entry=b.index[b.index>origin.date][0]
        target=entry+pd.DateOffset(months=r.months)
        terminal=b.index[b.index>=target][0]
        assert r.entry_date==entry and r.end_date==terminal
        x=p.loc[entry:terminal]
        assert x.index.equals(b.loc[entry:terminal].index)
        ret=x.iloc[-1]/x.iloc[0]-1
        mdd=min(x.iloc[i]/x.iloc[:i+1].max()-1 for i in range(len(x)))
        assert np.isclose(ret,r.industry_return) and np.isclose(mdd,r.max_drawdown)
        assert np.isclose(ret-(b.loc[terminal]/b.loc[entry]-1),r.excess_return)
        if pd.notna(r.beta252):
            history=p.loc[:origin.date].iloc[-253:]
            stock_r=np.diff(np.log(history.to_numpy()))
            market_r=np.diff(np.log(b.reindex(history.index).to_numpy()))
            assert len(stock_r)==252
            beta=np.cov(stock_r,market_r,ddof=1)[0,1]/np.var(market_r,ddof=1)
            assert np.isclose(beta,r.beta252,rtol=1e-9,atol=1e-9)
        checks.append(f'raw path independently verified {r.row_id} {r.months} {r.benchmark}')
    missing=outcome[~outcome.outcome_status.eq('OK')]
    assert missing[['industry_return','excess_return','max_drawdown']].isna().all().all()
    checks.append('missing price outcomes are NaN, not zero')
    # Adversarial example: repeated alerts cannot enter before fixed release;
    # a signal exactly at release is permitted, regardless of later outcome.
    cal=pd.bdate_range('2021-01-01','2022-12-31')
    f=pd.DataFrame(dict(era=['X']*4,level=['L3']*4,industry_code=['TEST']*4,block=[1]*4,
        row_id=range(4),date=pd.to_datetime(['2021-01-04','2021-02-01','2021-07-02','2021-07-05'])))
    assert episode_starts(f,cal).tolist()==[True,False,False,True]
    assert episode_starts(f.iloc[:3],cal).tolist()==[True,False,False]
    checks.append('adversarial launch release and prefix checks')
    primary=pd.read_csv(OUT/'primary_accepted_outcomes.csv.gz')
    assert ((primary.y.isna()) & primary.outcome_status.eq('OK')).any()
    checks.append('cycle-unknown observations with known returns included')
    js(OUT/'independent_numerical_validation.json',dict(status='PASS',checks=checks,checks_count=len(checks)))
    print('PASS',len(checks),'independent checks')


if __name__=='__main__':run()
