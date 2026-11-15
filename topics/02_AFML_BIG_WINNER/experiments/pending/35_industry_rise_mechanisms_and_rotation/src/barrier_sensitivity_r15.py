import pandas as pd
from common import *
from events_r14 import all_report_barriers


def monthly_from_history(g,date):
    q=g[g.publication_proxy_date<date].sort_values('publication_proxy_date')
    if q.empty:return dict(status='no_report',revision=np.nan)
    current=q.iloc[-1];published=current.publication_proxy_date
    rec=dict(latest_publication=published,previous_publication=pd.NaT,revision=np.nan,status='unknown')
    if (date-published).days>180:rec['status']='stale';return rec
    if len(q)<2:rec['status']='no_prior';return rec
    previous=q.iloc[-2];rec['previous_publication']=previous.publication_proxy_date
    if (published-previous.publication_proxy_date).days>365:rec['status']='prior_stale';return rec
    if not np.isfinite(current.value) or not np.isfinite(previous.value):rec['status']='unknown_current_or_prior';return rec
    denominator=abs(current.value)+abs(previous.value)
    if denominator==0:rec['status']='zero_denominator';return rec
    rec.update(status='valid',revision=(current.value-previous.value)/denominator);return rec


def run():
    out=ROOT/'outputs/r15';values=pd.read_parquet(ROOT/'data/r11_analyst_forecasts.parquet')
    ep=ROOT.parent/'24_conditional_return_distribution_exploration/outputs/r19_eps_expectations'
    receipt=json.loads((ROOT/'outputs/r11/receipt.json').read_text())
    assert sha(ep/'validated_extractions.parquet')==receipt['source_extraction_sha256']
    assert sha(ep/'selected_reports.parquet')==receipt['source_metadata_sha256']
    reports=pd.read_parquet(ep/'validated_extractions.parquet',columns=['infoCode','stockCode','publishDate','available_date']).merge(pd.read_parquet(ep/'selected_reports.parquet',columns=['infoCode','orgCode']),on='infoCode',validate='one_to_one').rename(columns={'stockCode':'stock_code','orgCode':'broker'})
    reports['publication_proxy_date']=pd.concat([pd.to_datetime(reports.publishDate),pd.to_datetime(reports.available_date)],axis=1).max(axis=1)
    expanded=all_report_barriers(values,reports[['infoCode','stock_code','broker','publication_proxy_date']])
    keys=['stock_code','broker','fiscal_year','publication_proxy_date']
    collapsed=expanded.groupby(keys).value.agg(['nunique','first','count','size']).reset_index()
    collapsed['value']=collapsed['first'].where((collapsed.nunique if False else collapsed['nunique']).eq(1)&collapsed['count'].eq(collapsed['size']))
    dates=sorted(pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=['date']).date.unique())
    rows=[]
    for key,g in collapsed.groupby(['stock_code','broker','fiscal_year']):
        for date in dates:
            date=pd.Timestamp(date)
            if key[2] not in [date.year,date.year+1] or date<pd.Timestamp('2020-01-01'):continue
            rows.append(dict(stock_code=key[0],broker=key[1],fiscal_year=key[2],date=date,**monthly_from_history(g,date)))
    monthly=pd.DataFrame(rows);monthly.to_parquet(ROOT/'data/r15_company_broker_revisions.parquet',index=False)
    old=pd.read_parquet(ROOT/'data/r11_company_broker_revisions.parquet')
    pair=old.merge(monthly,on=['stock_code','broker','fiscal_year','date'],how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
    pair['change']=np.select([pair.revision_old.notna()&pair.revision_new.isna(),pair.revision_old.isna()&pair.revision_new.notna(),pair.revision_old.notna()&pair.revision_new.notna()&~np.isclose(pair.revision_old,pair.revision_new,equal_nan=True)],['lost','gained','changed_value'],default='unchanged_or_both_unknown')
    pair.to_parquet(ROOT/'data/r15_company_pair_audit.parquet',index=False)
    pair.groupby(['change']).size().rename('rows').to_csv(out/'company_changes.csv')
    members=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=['month','era','level','industry_code','security_id','instrument']);members['stock_code']=members.instrument.str[2:]
    coverage=[]
    for date in sorted(monthly.date.unique()):
        date=pd.Timestamp(date);m=members[members.month==date.to_period('M')-1]
        for offset in [0,1]:
            v=monthly[(monthly.date==date)&(monthly.fiscal_year==date.year+offset)&monthly.status.eq('valid')].groupby('stock_code').revision.median().rename('revision')
            g=m.join(v,on='stock_code',validate='many_to_one').groupby(KEY).agg(members=('security_id','size'),known=('revision','count'),covered_member_median=('revision','median')).reset_index()
            g['date']=date;g['fy_offset']=offset;g['fiscal_year']=date.year+offset;g['coverage']=g.known/g.members;g['eligible']=(g.known>=5)&(g.coverage>=.8);g['full_factor']=g.covered_member_median.where(g.eligible);coverage.append(g)
    c=pd.concat(coverage,ignore_index=True);c.to_parquet(ROOT/'data/r15_revision_coverage.parquet',index=False)
    c.groupby(['era','level','fy_offset']).agg(rows=('date','size'),strict=('eligible','sum'),partial5=('known',lambda x:int(x.ge(5).sum()))).to_csv(out/'coverage_summary.csv')
    old_c=pd.read_parquet(ROOT/'data/r11_revision_coverage.parquet')
    compared=old_c.merge(c,on=KEY+['date','fy_offset'],suffixes=('_old','_new'),validate='one_to_one')
    compared.groupby(['era','level','fy_offset']).agg(old_strict=('eligible_old','sum'),new_strict=('eligible_new','sum'),old_known=('known_old','sum'),new_known=('known_new','sum')).to_csv(out/'coverage_changes.csv')
    js(out/'data_receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r15.json'),code_sha256=sha(__file__),forecast_source_sha256=sha(ROOT/'data/r11_analyst_forecasts.parquet'),
        original_coverage_sha256=sha(ROOT/'data/r11_revision_coverage.parquet'),corrected_coverage_sha256=sha(ROOT/'data/r15_revision_coverage.parquet'),
        original_company_rows=len(old),corrected_valid_company_rows=int(monthly.status.eq('valid').sum()),changes=pair.change.value_counts().to_dict()))
    print(pair.change.value_counts().to_string(),flush=True)
if __name__=='__main__':run()
