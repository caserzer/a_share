"""Local activity field support only; never join labels or compute signal returns."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha


def main():
    out=EP/'outputs/activity_feasibility';out.mkdir(exist_ok=True)
    if (out/'receipt.json').exists():raise FileExistsError('audit exists')
    receiptfile=PRIOR/'receipt.json';receipt=json.loads(receiptfile.read_text())
    afile=CACHE/'extension_v2/products/assignments.parquet'
    a=pd.read_parquet(afile,columns=['month','date','security_id','industry_code','unresolved','level','era']);a=a[a.level.eq('L3')]
    assert not a.duplicated(['era','month','industry_code','security_id']).any()
    calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values();ids=sorted(a.security_id.unique());indices={s:i for i,s in enumerate(ids)}
    fields=['volume','money','turnover_rate'];support={f:np.zeros((len(cal),len(ids)),bool) for f in fields}
    paths={Path(x).stem:Path(x) for x in receipt['price_reads']};stocks=[];providers={};total=0;vwap_comparable=0;vwap_outside=0
    for i,sid in enumerate(ids):
        path=paths[sid];assert sha(path)==receipt['price_reads'][str(path)]
        cols=['date','low','high','low_conflict','high_conflict','source_providers']+fields+[f+'_conflict' for f in fields]
        d=pd.read_parquet(path,columns=cols);assert not d.date.duplicated().any();total+=len(d)
        for k,n in d.source_providers.map(lambda x:'|'.join(sorted(x)) if x is not None else 'UNKNOWN').value_counts().items():providers[k]=providers.get(k,0)+int(n)
        x=d.set_index('date').reindex(cal);row={'security_id':sid,'rows':len(d)}
        for f in fields:
            v=pd.to_numeric(x[f],errors='coerce');valid=np.isfinite(v)&v.ge(0)&x[f+'_conflict'].eq(False)
            # 84 consecutive observations, preceding 63 positive denominator, no filling gaps.
            full=valid.astype(int).rolling(84,min_periods=84).sum().eq(84)
            denominator=v.where(valid).shift(21).rolling(63,min_periods=63).sum().gt(0)
            support[f][:,i]=(full&denominator).to_numpy()
            row[f+'_known']=int(valid.sum());row[f+'_conflict']=int(x[f+'_conflict'].eq(True).sum());row[f+'_zero']=int((valid&v.eq(0)).sum())
        ok=x.volume.gt(0)&x.money.gt(0)&x.low.gt(0)&x.high.ge(x.low)
        for f in ['volume','money','low','high']:ok &= x[f+'_conflict'].eq(False)
        avg=x.money/x.volume;outside=ok&((avg<x.low*.99)|(avg>x.high*1.01))
        vwap_comparable+=int(ok.sum());vwap_outside+=int(outside.sum());row['vwap_comparable']=int(ok.sum());row['vwap_outside_1pct']=int(outside.sum())
        stocks.append(row)
        if (i+1)%1000==0:print('verified activity partitions',i+1,flush=True)
    cohorts={k:(np.array([indices[x] for x in g.security_id]),int(g.unresolved.max()),g.date.max()) for k,g in a.groupby(['era','month','industry_code'])}
    gridfile=EP/'outputs/r01/weekly_catalog.parquet';grid=pd.read_parquet(gridfile,columns=['era','industry_code','date','day_i','eligible']);rows=[]
    for r in grid.itertuples():
        assert cal[r.day_i]==r.date
        cohort=cohorts.get((r.era,r.date.to_period('M')-1,r.industry_code));row=dict(era=r.era,industry_code=r.industry_code,date=r.date,price_eligible=bool(r.eligible),membership_known=cohort is not None)
        for f in fields:row[f+'_supported']=False;row[f+'_known_members']=None;row[f+'_coverage']=None
        if cohort is not None:
            indexes,u,anchor=cohort;assert anchor<r.date;n=len(indexes)+u
            for f in fields:
                count=int(support[f][r.day_i,indexes].sum());row[f+'_known_members']=count;row[f+'_coverage']=count/n;row[f+'_supported']=count>=5 and count/n>=.8
        rows.append(row)
    w=pd.DataFrame(rows);w.to_parquet(out/'weekly_support.parquet',index=False);pd.DataFrame(stocks).to_parquet(out/'stock_coverage.parquet',index=False)
    annual=[]
    for (era,year),g in w.groupby(['era',w.date.dt.year]):
        annual.append(dict(era=era,year=int(year),catalog_rows=len(g),price_eligible=int(g.price_eligible.sum()),**{f+'_common_support':int((g.price_eligible&g[f+'_supported']).sum()) for f in fields}))
    ticketfile=EP/'outputs/r02/common_catalog.parquet';tickets=pd.read_parquet(ticketfile,columns=['era','industry_code','date','ticket_id']);tickets=tickets[tickets.ticket_id.notna()]
    joined=tickets.merge(w,on=['era','industry_code','date'],validate='one_to_one');assert len(joined)==len(tickets)
    result=dict(scope='Feasibility only; no new predictions, outcome joins, or return evaluation',strict_pit=False,
        support_rule='Descriptive 84 consecutive nonnegative nonconflicting field observations; prior63 denominator>0; >=5 valid members and >=80% resolved+unresolved prior-month members',
        partitions=len(ids),raw_rows=total,catalog_rows=len(w),missing_membership=int((~w.membership_known).sum()),
        price_eligible=int(w.price_eligible.sum()),common_support={f:int((w.price_eligible&w[f+'_supported']).sum()) for f in fields},
        common_ticket_denominator=len(tickets),supported_tickets={f:int(joined[f+'_supported'].sum()) for f in fields},
        field_counts={f:{k:int(pd.DataFrame(stocks)[f+'_'+k].sum()) for k in ['known','conflict','zero']} for f in fields},
        vwap_unit_diagnostic=dict(comparable=vwap_comparable,outside_low_high_with_1pct_tolerance=vwap_outside,interpretation='Descriptive money/volume consistency only; not proof of historical units or PIT'),
        provider_sets=providers,annual=annual,inputs={str(f):sha(f) for f in [receiptfile,afile,calendarfile,gridfile,ticketfile,Path(__file__)]},
        partition_hashes='All partitions verified against P29 price_reads',outputs={f.name:sha(f) for f in out.glob('*.parquet')})
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','annual','provider_sets','outputs']},ensure_ascii=False))


if __name__=='__main__':main()
