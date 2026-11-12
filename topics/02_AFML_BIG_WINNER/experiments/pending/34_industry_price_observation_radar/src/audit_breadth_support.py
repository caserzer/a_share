"""Read-only local breadth feasibility: identity and price support, no returns or labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha


def main():
    out=EP/'outputs/breadth_feasibility';out.mkdir(exist_ok=True)
    if (out/'receipt.json').exists():raise FileExistsError('audit exists')
    receiptfile=PRIOR/'receipt.json';receipt=json.loads(receiptfile.read_text())
    afile=CACHE/'extension_v2/products/assignments.parquet'
    # Explicit projection excludes next_return, entry_open, entry_chain and all outcomes.
    cols=['month','date','security_id','industry_code','unresolved','level','era']
    a=pd.read_parquet(afile,columns=cols);a=a[a.level.eq('L3')].copy()
    assert not a.duplicated(['era','month','industry_code','security_id']).any()
    assert (a.groupby(['era','month','security_id']).industry_code.nunique()<=1).all()
    assert (a.date.dt.to_period('M')==a.month).all()
    calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values()
    ids=sorted(a.security_id.unique());indices={s:i for i,s in enumerate(ids)}
    valid20=np.zeros((len(cal),len(ids)),bool);current=np.zeros_like(valid20)
    path_byid={Path(x).stem:Path(x) for x in receipt['price_reads']}
    totalrows=conflicts=chainbreaks=0
    for i,sid in enumerate(ids):
        path=path_byid[sid];assert sha(path)==receipt['price_reads'][str(path)],path
        original=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id'])
        assert not original.date.duplicated().any();totalrows+=len(original)
        x=original.set_index('date').reindex(cal)
        valid=(x.qfq_close.notna() & np.isfinite(x.qfq_close) & x.qfq_close.gt(0) & x.close_conflict.eq(False) & x.factor_chain_id.notna())
        same=x.factor_chain_id.eq(x.factor_chain_id.shift())
        reset=~valid|~valid.shift(fill_value=False)|~same
        positions=np.arange(len(x));lastreset=np.maximum.accumulate(np.where(reset,positions,-1))
        run=positions-lastreset+1
        current[:,i]=valid.to_numpy();valid20[:,i]=valid.to_numpy() & (run>=21)
        conflicts+=int(x.close_conflict.eq(True).sum());chainbreaks+=int((valid & valid.shift(fill_value=False)&~same).sum())
        if (i+1)%1000==0:print(f'verified local price partitions {i+1}/{len(ids)}',flush=True)
    cohorts={}
    for (era,month,code),g in a.groupby(['era','month','industry_code']):
        cohorts[(era,str(month),code)]=(np.array([indices[x] for x in g.security_id]),int(g.unresolved.max()),g.date.max())
    gridfile=EP/'outputs/r01/weekly_catalog.parquet'
    grid=pd.read_parquet(gridfile,columns=['era','industry_code','date','day_i','eligible'])
    rows=[]
    for r in grid.itertuples():
        assert cal[r.day_i]==r.date
        key=(r.era,str(r.date.to_period('M')-1),r.industry_code);cohort=cohorts.get(key)
        row=dict(era=r.era,industry_code=r.industry_code,date=r.date,price_eligible=bool(r.eligible),membership_month=key[1])
        if cohort is None:
            row.update(status='NO_PRIOR_MONTH_MEMBERSHIP',members=None,unresolved=None,current_known=None,history20_known=None,coverage20=None,support5_80=False)
        else:
            si,u,anchor=cohort;assert anchor<r.date
            n=len(si);hist=int(valid20[r.day_i,si].sum());now=int(current[r.day_i,si].sum())
            row.update(status='HISTORICAL_PROXY_MEMBERSHIP',members=n,unresolved=u,current_known=now,history20_known=hist,coverage20=hist/(n+u),support5_80=hist>=5 and hist/(n+u)>=.8)
        rows.append(row)
    f=pd.DataFrame(rows);f.to_parquet(out/'weekly_support.parquet',index=False)
    summaries=[]
    for (era,year),g in f.groupby(['era',f.date.dt.year]):
        summaries.append(dict(era=era,year=int(year),catalog_rows=len(g),membership_known=int(g.members.notna().sum()),
                              price_eligible=int(g.price_eligible.sum()),breadth_support5_80=int(g.support5_80.sum()),
                              common_support=int((g.price_eligible&g.support5_80).sum())))
    result=dict(scope='Data feasibility only: no price-return signals or outcome evaluation',
                support_rule='Descriptive candidate: at least 5 members with all 21 consecutive valid same-chain closes and >=80% of resolved plus unresolved members',
                strict_pit=False,membership_projection=cols,price_partitions=len(ids),price_rows=totalrows,conflicting_close_rows=conflicts,valid_chain_changes=chainbreaks,
                catalog_rows=len(f),membership_missing=int(f.members.isna().sum()),price_eligible=int(f.price_eligible.sum()),
                common_support=int((f.price_eligible&f.support5_80).sum()),annual=summaries,
                membership_rows=len(a),duplicate_member_rows=0,multi_industry_identity_months=0,
                inputs={str(x):sha(x) for x in [receiptfile,afile,calendarfile,gridfile,Path(__file__)]},
                price_hash_verification='Every used partition matched P29 receipt price_reads',
                output_sha=sha(out/'weekly_support.parquet'))
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','annual','membership_projection']},ensure_ascii=False))


if __name__=='__main__':main()
