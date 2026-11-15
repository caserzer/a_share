"""Recover all-market local archived pages, keep both historical-proxy and archival clocks."""
import zipfile
import pandas as pd
from common import *
SOURCE=Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports/fixed_industry_pool/20261010-data-v1')


def next_session(dates,calendar):
    dates=pd.DatetimeIndex(dates); ix=calendar.searchsorted(dates,side='right')
    return pd.Series([calendar[i] if pd.notna(d) and i<len(calendar) else pd.NaT for d,i in zip(dates,ix)])


def asof_values(raw, date, field):
    # Same-date disagreements are missing, including latest-version conflicts.
    g=raw[raw.api.eq('fina_indicator_vip')&raw.proxy_available_date.le(date)].copy()
    g[field]=pd.to_numeric(g[field],errors='coerce')
    keys=['ts_code','end_date','proxy_available_date']
    a=g.groupby(keys)[field].agg(value='first',distinct=lambda x:x.nunique(dropna=False)).reset_index()
    a.loc[a.distinct.gt(1),'value']=np.nan
    a=a.sort_values('proxy_available_date').drop_duplicates(['ts_code','end_date'],keep='last')
    return a[['ts_code','end_date','value']]


def run():
    out=ROOT/'outputs/r03'; manifest=json.loads((SOURCE/'manifest.json').read_text())
    refs={}
    for name in ['inputs/provider_responses.zip','query_receipts.json','METHODS.md']:
        p=SOURCE/name;h=sha(p);assert h==manifest['files'][name],name;refs[str(p)]=h
    receipts=json.loads((SOURCE/'query_receipts.json').read_text())
    receipts=[r for r in receipts if r['api'] in ['fina_indicator_vip','income_vip','cashflow_vip']]
    parts=[];coverage=[]
    calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    with zipfile.ZipFile(SOURCE/'inputs/provider_responses.zip') as z:
        for r in receipts:
            payload=z.read(r['archived_response']);assert hashlib.sha256(payload).hexdigest()==r['raw_sha256']
            obj=json.loads(payload);assert obj['code']==0
            p=pd.DataFrame(obj['data']['items'],columns=obj['data']['fields']);assert len(p)==r['rows']
            p['api']=r['api'];p['query_id']=r['query_id'];p['source_page_sha256']=r['raw_sha256'];p['source_row']=np.arange(len(p))
            p['archived_available_at']=pd.Timestamp(r['retrieved_at']);parts.append(p)
        for (api,period),rs in pd.DataFrame(receipts).assign(period=lambda x:x.params.map(lambda p:p['period'])).groupby(['api','period']):
            ordered=sorted(rs.to_dict('records'),key=lambda r:r['params']['offset'])
            offsets=[r['params']['offset'] for r in ordered];limit=ordered[0]['params']['limit']
            assert offsets==list(range(0,len(offsets)*limit,limit))
            assert all(r['rows']==limit for r in ordered[:-1]) and ordered[-1]['rows']<limit
            coverage.append(dict(api=api,period=period,pages=len(ordered),raw_rows=sum(r['rows'] for r in ordered),pagination_complete=True))
    raw=pd.concat(parts,ignore_index=True)
    for col in ['ann_date','f_ann_date','end_date']:raw[col]=pd.to_datetime(raw[col],format='%Y%m%d',errors='coerce')
    raw['effective_ann_date']=raw[['ann_date','f_ann_date']].max(axis=1)
    raw['timing_valid']=raw.effective_ann_date.ge(raw.end_date)&raw.end_date.notna()
    raw['proxy_available_date']=next_session(raw.effective_ann_date,calendar).to_numpy()
    raw.loc[~raw.timing_valid,'proxy_available_date']=pd.NaT
    raw['quality']='Historical-proxy before archive acquisition; not complete PIT vintage history'
    raw.to_parquet(ROOT/'data/financial_archive_all_market.parquet',index=False)
    pd.DataFrame(coverage).to_csv(out/'raw_page_coverage.csv',index=False)
    js(out/'archive_receipt.json',dict(sources=refs,raw_rows=len(raw),issuers=raw.ts_code.nunique(),pages=len(receipts),
        invalid_timing_rows=int((~raw.timing_valid).sum()),archived_start=raw.archived_available_at.min(),archived_end=raw.archived_available_at.max(),
        output_sha256=sha(ROOT/'data/financial_archive_all_market.parquet'),protocol_sha256=sha(ROOT/'protocols/r03.json')))
    members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=KEY+['month','security_id','instrument','unresolved'])
    panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet');panel=panel[panel.era.eq('SW2021')&panel.date.between('2026-04-01','2026-09-30')]
    rows=[];company=[]
    for date in sorted(panel.date.unique()):
        date=pd.Timestamp(date)
        fields=[]
        for field in ['profit_dedt','grossprofit_margin']:
            f=asof_values(raw,date,field)
            cur=f[f.end_date.dt.year.eq(2026)].copy();prior=f[f.end_date.dt.year.eq(2025)].copy()
            prior['end_date']=prior.end_date+pd.DateOffset(years=1)
            joined=cur.merge(prior,on=['ts_code','end_date'],suffixes=('_current','_prior'),validate='one_to_one')
            if field=='profit_dedt':
                denominator=joined.value_current.abs()+joined.value_prior.abs()
                joined['dedt_change']=(joined.value_current-joined.value_prior)/denominator.where(denominator.gt(0));value='dedt_change'
            else:joined['margin_delta']=joined.value_current-joined.value_prior;value='margin_delta'
            fields.append(joined[['ts_code','end_date',value]])
        f=fields[0].merge(fields[1],on=['ts_code','end_date'],how='outer',validate='one_to_one')
        # Latest quarter: do not silently fall back to older good values when a newer quarter conflicts.
        f=f.sort_values('end_date').drop_duplicates('ts_code',keep='last')
        f['instrument']=f.ts_code.str[-2:]+f.ts_code.str[:6];f['date']=date;company.append(f)
        m=members[members.era.eq('SW2021')&members.month.eq(date.to_period('M')-1)]
        j=m.merge(f,on='instrument',how='left',validate='many_to_one')
        for key,g in j.groupby(KEY):
            denominator=len(g)+int(g.unresolved.max());rec=dict(zip(KEY,key),date=date,members=len(g),denominator=denominator)
            for field in ['dedt_change','margin_delta']:
                n=int(g[field].notna().sum());rec[field+'_valid']=n;rec[field+'_coverage']=n/denominator
                rec[field]=g[field].mean() if n>=5 and n/denominator>=.8 else np.nan
            rows.append(rec)
    pd.concat(company,ignore_index=True).to_parquet(ROOT/'data/company_financial_factors.parquet',index=False)
    industry=pd.DataFrame(rows);industry.to_parquet(ROOT/'data/industry_financial_factors.parquet',index=False)
    result=panel.merge(industry,on=KEY+['date'],how='left',suffixes=('','_financial'),validate='one_to_one')
    result.to_parquet(ROOT/'data/financial_monthly_panel.parquet',index=False)
    result.groupby(['level','date'])[['dedt_change','margin_delta']].count().to_csv(out/'industry_factor_coverage.csv')
    print('RECOVERED',len(raw),'records',raw.ts_code.nunique(),'issuers;',len(industry),'industry origins',flush=True)

if __name__=='__main__':run()
