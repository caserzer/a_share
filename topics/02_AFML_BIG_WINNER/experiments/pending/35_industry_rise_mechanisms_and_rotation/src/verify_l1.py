"""Independent direct constituent month-end reconciliation for predefined recent dates."""
import pandas as pd
from common import *


def run():
    rec=json.loads((ROOT/'outputs/r05/receipt.json').read_text());assert sha(ROOT/'data/l1_daily.parquet')==rec['daily_sha256']
    d=pd.read_parquet(ROOT/'data/l1_daily.parquet');m=pd.read_parquet(ROOT/'data/l1_assignments.parquet')
    assert not m.duplicated(['month','security_id']).any()
    assert set(d.industry_code)==set(pd.read_parquet(CACHE/'industry_v1/L1.parquet').index_code)
    assert (d.membership_asof<=d.date).all()
    assert not d.duplicated(KEY+['date']).any()
    assert all(g.sort_values('date').day_i.diff().dropna().eq(1).all() for _,g in d.groupby(KEY+['block']))
    stock_paths={Path(k).stem:Path(k) for k in rec['reads'] if '/normalized/prices_qfq/' in k}
    dates=[pd.Timestamp('2026-05-29'),pd.Timestamp('2026-08-31')]
    codes=sorted(d.industry_code.unique())[::10];results=[]
    for code in codes:
        series=d[d.industry_code.eq(code)].set_index('date')
        for end in dates:
            endrow=series.loc[end];start=pd.Timestamp(endrow.membership_asof)
            members=m[m.industry_code.eq(code)&m.month.eq(start.to_period('M'))]
            values=[]
            for row in members.itertuples():
                p=stock_paths[row.security_id];assert sha(p)==rec['reads'][str(p)]
                f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex([start,end])
                if f.qfq_close.notna().all() and f.qfq_close.gt(0).all() and f.close_conflict.eq(False).all() and f.factor_chain_id.notna().all() and f.factor_chain_id.nunique()==1:
                    values.append(f.qfq_close.iloc[1]/f.qfq_close.iloc[0]-1)
            assert len(values)/(len(members)+members.unresolved.max())>=.8
            observed=series.loc[end,'nav']/series.loc[start,'nav']-1
            expected=np.mean(values);error=abs(observed-expected);assert error<2e-6
            results.append(dict(code=code,start=start,end=end,stocks=len(values),expected=expected,observed=observed,error=error))
    pd.DataFrame(results).to_csv(ROOT/'outputs/r05/independent_monthly_reconciliation.csv',index=False)
    js(ROOT/'outputs/r05/verification.json',dict(status='PASS',industries=31,duplicate_members=0,membership_not_future=True,
        continuous_blocks=True,independent_direct_checks=len(results),max_error=max(x['error'] for x in results),
        limitation='sampled direct return checks, not a proof of complete historical membership/PIT parent mapping'))
    print('L1 VERIFIED',len(results),'direct month-end checks')

if __name__=='__main__':run()
