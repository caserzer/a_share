import pandas as pd
from common import *
from events_r14 import all_report_barriers


def monthly_fast(g,dates):
    g=g.sort_values('publication_proxy_date');history=pd.DatetimeIndex(g.publication_proxy_date);v=g.value.to_numpy();dates=pd.DatetimeIndex(dates)
    indices=history.searchsorted(dates,side='left')-1;rows=[]
    for date,i in zip(dates,indices):
        r=dict(date=date,latest_publication=pd.NaT,previous_publication=pd.NaT,revision=np.nan,status='no_report')
        if i>=0:
            r['latest_publication']=history[i]
            if (date-history[i]).days>180:r['status']='stale'
            elif i==0:r['status']='no_prior'
            else:
                r['previous_publication']=history[i-1]
                if (history[i]-history[i-1]).days>365:r['status']='prior_stale'
                elif not np.isfinite(v[i]) or not np.isfinite(v[i-1]):r['status']='unknown_current_or_prior'
                elif abs(v[i])+abs(v[i-1])==0:r['status']='zero_denominator'
                else:r.update(status='valid',revision=(v[i]-v[i-1])/(abs(v[i])+abs(v[i-1])))
        rows.append(r)
    return pd.DataFrame(rows)


def monthly_eps(values,reports,dates,withheld):
    eps=values[values.basis.eq('eps_cny_per_share')].copy()
    eps.loc[eps.infoCode.isin(withheld),'value']=np.nan
    eps['basis']='profit_cny' # adapter to shared barrier builder, values remain EPS
    expanded=all_report_barriers(eps,reports)
    keys=['stock_code','broker','fiscal_year','publication_proxy_date']
    collapsed=expanded.groupby(keys).value.agg(['nunique','first','count','size']).reset_index()
    collapsed['value']=collapsed['first'].where(collapsed['nunique'].eq(1)&collapsed['count'].eq(collapsed['size']))
    rows=[]
    for key,g in collapsed.groupby(['stock_code','broker','fiscal_year']):
        query=[d for d in dates if d.year in [key[2],key[2]-1] and d.year>=2020]
        if not query:continue
        q=monthly_fast(g,query)
        for k,v in zip(['stock_code','broker','fiscal_year'],key):q[k]=v
        rows.append(q)
    return pd.concat(rows,ignore_index=True)


def common_pairs(profit,eps):
    keys=['stock_code','broker','fiscal_year','date']
    q=profit[profit.status.eq('valid')].merge(eps[eps.status.eq('valid')],on=keys,suffixes=('_profit','_eps'),validate='one_to_one')
    same=q.latest_publication_profit.eq(q.latest_publication_eps)&q.previous_publication_profit.eq(q.previous_publication_eps)
    return q[same].copy(),q[~same].copy()


def run():
    out=ROOT/'outputs/r28';out.mkdir(exist_ok=True)
    ep=ROOT.parent/'24_conditional_return_distribution_exploration/outputs/r19_eps_expectations'
    paths=[ROOT/'data/r24_source_exclusion_overlay.parquet',ROOT/'data/r25_company_broker_revisions.parquet',ROOT/'outputs/r27/share_action_review.json',ep/'validated_extractions.parquet',ep/'selected_reports.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'protocols/r28.json',Path(__file__)]
    values=pd.read_parquet(paths[0]);profit=pd.read_parquet(paths[1]);review=json.loads(paths[2].read_text());guard={r['infoCode'] for r in review if r['review']=='explicit_eps_share_basis_context'};assert len(guard)==5
    reports=pd.read_parquet(paths[3],columns=['infoCode','stockCode','publishDate','available_date']).merge(pd.read_parquet(paths[4],columns=['infoCode','orgCode']),on='infoCode',validate='one_to_one').rename(columns={'stockCode':'stock_code','orgCode':'broker'})
    reports['publication_proxy_date']=pd.concat([pd.to_datetime(reports.publishDate),pd.to_datetime(reports.available_date)],axis=1).max(axis=1)
    reports=reports[['infoCode','stock_code','broker','publication_proxy_date']]
    dates=[pd.Timestamp(x) for x in sorted(pd.read_parquet(paths[7],columns=['date']).date.unique())]
    columns=['month']+KEY+['security_id','instrument']
    members=pd.concat([pd.read_parquet(p,columns=columns) for p in paths[5:7]],ignore_index=True);members['stock_code']=members.instrument.str[2:]
    all_cov=[];counts=[]
    for variant,blocked in [('raw_proxy',set()),('share_context_guard',guard)]:
        monthly=monthly_eps(values,reports,dates,blocked);monthly.to_parquet(ROOT/f'data/r28_{variant}_eps_monthly.parquet',index=False)
        paired,mismatch=common_pairs(profit,monthly);paired.to_parquet(ROOT/f'data/r28_{variant}_paired_brokers.parquet',index=False)
        mismatch.to_csv(out/f'{variant}_date_mismatch.csv',index=False)
        valid=monthly[monthly.status.eq('valid')]
        for date in dates:
            if date.year<2020:continue
            m=members[members.month.eq(date.to_period('M')-1)]
            for offset in [0,1]:
                ep=valid[valid.date.eq(date)&valid.fiscal_year.eq(date.year+offset)].groupby('stock_code').revision.median().rename('eps_only')
                pp=paired[paired.date.eq(date)&paired.fiscal_year.eq(date.year+offset)].groupby('stock_code')[['revision_profit','revision_eps']].median()
                joined=m.join(ep,on='stock_code').join(pp,on='stock_code')
                cov=joined.groupby(KEY).agg(members=('security_id','size'),eps_known=('eps_only','count'),common_known=('revision_profit','count'),profit_common=('revision_profit','median'),eps_common=('revision_eps','median')).reset_index()
                cov['date']=date;cov['fy_offset']=offset;cov['variant']=variant
                cov['eps_coverage']=cov.eps_known/cov.members;cov['common_coverage']=cov.common_known/cov.members
                cov['eps_strict']=cov.eps_known.ge(5)&cov.eps_coverage.ge(.8);cov['common_strict']=cov.common_known.ge(5)&cov.common_coverage.ge(.8)
                all_cov.append(cov)
        counts.append(dict(variant=variant,monthly_rows=len(monthly),valid_eps=len(valid),common_broker_rows=len(paired),date_mismatches=len(mismatch)))
        print(counts[-1],flush=True)
    cov=pd.concat(all_cov,ignore_index=True);cov.to_parquet(ROOT/'data/r28_common_coverage.parquet',index=False)
    summary=cov.groupby(['variant','era','level','fy_offset']).agg(industry_dates=('date','size'),eps_strict=('eps_strict','sum'),common_strict=('common_strict','sum'),common_at_least5=('common_known',lambda x:int(x.ge(5).sum()))).reset_index();summary.to_csv(out/'coverage_summary.csv',index=False)
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},counts=counts,withheld_reports=sorted(guard),industry_rows=len(cov),coverage_sha256=sha(ROOT/'data/r28_common_coverage.parquet'),quality='Historical-proxy selected-report sample; guard not complete share-base certification'))
    print(summary.to_string(index=False),flush=True)

if __name__=='__main__':run()
