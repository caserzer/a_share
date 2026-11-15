"""Historical code intervals, listing gates, and exact monthly TTM/PE joins."""
import pandas as pd
from common import *
RELEASE=ROOT.parent/'30_pit_data_foundation_v1/outputs/pit_v5/release.json'
def interval_choice(g,date,fallback):
    if g.empty:return fallback,'static_metadata_proxy'
    q=g[(g.start.isna()|g.start.le(date))&(g.end.isna()|g.end.gt(date))]
    if len(q)==1:return q.instrument.iloc[0],'explicit_interval_proxy'
    return None,'missing_code_interval' if q.empty else 'ambiguous_code_interval'
def run():
    out=ROOT/'outputs/r117';out.mkdir(exist_ok=True);release=Path(json.loads(RELEASE.read_text())['path']);manifest=release/'FULL_MANIFEST.json';complete=release/'COMPLETE.json';assert sha(manifest)==json.loads(complete.read_text())['full_manifest_sha256'];entries={x['relative_path']:x for x in json.loads(manifest.read_text())}
    names=['inputs/normalized/securities.parquet','inputs/normalized/code_intervals.parquet','inputs/inputs/baseline/normalized/code_intervals.parquet'];frames=[];paths=[RELEASE,manifest,complete]
    for n in names:
        p=release/n;assert sha(p)==entries[n]['sha256'];frames.append(pd.read_parquet(p));paths.append(p)
    master,code,bse=frames;assert master.security_id.is_unique
    code=code[['security_id','instrument','valid_from','valid_until_exclusive']].rename(columns={'valid_from':'start','valid_until_exclusive':'end'});code['source']='continuity'
    bse=bse[['security_id','historical_instrument','valid_from','valid_to']].rename(columns={'historical_instrument':'instrument','valid_from':'start','valid_to':'end'});bse['source']='bse_cutover'
    intervals=pd.concat([code,bse],ignore_index=True);intervals['start']=pd.to_datetime(intervals.start);intervals['end']=pd.to_datetime(intervals.end);intervals.to_parquet(out/'code_intervals.parquet',index=False)
    sp=ROOT/'outputs/r112/valuation_monthly_coverage.parquet';fp=ROOT/'outputs/r116/monthly_ttm.parquet';fin=pd.read_parquet(fp);stocks=pd.read_parquet(sp);stocks=stocks[stocks.date.isin(fin.date.unique())].reset_index(drop=True)
    cols=['security_id','instrument','exchange','listing_date','delist_date','bse_listing_proxy','identity_date_conflict'];s=stocks.merge(master[cols].rename(columns={'instrument':'canonical_instrument'}),on='security_id',how='left',validate='many_to_one');rows=[]
    groups={sid:g for sid,g in intervals.groupby('security_id')}
    for x in s[['security_id','date','canonical_instrument']].itertuples(index=False):
        instrument,status=interval_choice(groups.get(x.security_id,intervals.iloc[:0]),x.date,x.canonical_instrument)
        if pd.isna(x.canonical_instrument):status='missing_master';instrument=None
        rows.append((instrument,status))
    s[['active_instrument','identity_status']]=pd.DataFrame(rows,index=s.index)
    s['listing_start']=s.listing_date.where(s.exchange.ne('BJ'),s.bse_listing_proxy);s['master_listed']=s.date.ge(s.listing_start)&(s.delist_date.isna()|s.date.lt(s.delist_date))&s.identity_date_conflict.eq(False);s['listing_agrees']=s.master_listed.eq(s.listed)
    validcode=s.active_instrument.str.fullmatch(r'(SH|SZ|BJ)[0-9]{6}',na=False);s['active_secucode']=(s.active_instrument.str[2:]+'.'+s.active_instrument.str[:2]).where(validcode)
    s['canonical_secucode']=s.canonical_instrument.str[2:]+'.'+s.canonical_instrument.str[:2]
    collisions=s[s.master_listed&validcode].groupby(['date','active_instrument']).security_id.nunique();s['active_collision']=[collisions.get((date,inst),0)>1 for date,inst in zip(s.date,s.active_instrument)]
    companies=set(fin.secucode);s['active_financial_partition']=s.active_secucode.isin(companies);s['canonical_financial_partition']=s.canonical_secucode.isin(companies)
    s['join_eligible']=s.identity_status.isin(['static_metadata_proxy','explicit_interval_proxy'])&validcode&s.master_listed&s.listing_agrees&~s.active_collision
    s['join_secucode']=s.active_secucode.where(s.join_eligible);s.to_parquet(out/'stock_identity.parquet',index=False)
    j=s.merge(pd.DataFrame({'clock':['notice','update']}),how='cross').merge(fin.rename(columns={'secucode':'join_secucode','status':'financial_status'}),on=['join_secucode','date','clock'],how='left',validate='many_to_one')
    j['join_status']=np.select([~j.listing_agrees,~j.master_listed,~j.join_eligible,~j.active_financial_partition],['listing_source_disagreement','not_listed','identity_unavailable_or_ambiguous','no_active_code_financial_partition'],default='financial_snapshot_linked')
    assert j.loc[j.join_status.eq('financial_snapshot_linked'),'financial_status'].notna().all()
    capgood=np.isfinite(j.cap)&j.cap.gt(0)&np.isfinite(j.raw_close)&j.raw_close.gt(0)&np.isfinite(j.total_shares)&j.total_shares.gt(0)&j.share_effective_date.notna()&j.share_effective_date.le(j.date)&np.isclose(j.cap,j.raw_close*j.total_shares,rtol=1e-10,atol=0)
    j['comparison_eligible']=j.join_status.eq('financial_snapshot_linked')&j.financial_status.eq('known_ttm')&capgood&np.isfinite(j.vendor_pe_ttm)&j.vendor_pe_ttm.ne(0)
    j.to_parquet(out/'linked_monthly.parquet',index=False)
    j.assign(financial_state=j.financial_status.fillna('not_linked')).groupby(['clock','join_status','financial_state']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    summary=dict(stock_month_rows=len(s),security_ids=s.security_id.nunique(),months=s.date.nunique(),linked_rows=len(j),identity_status=s.identity_status.value_counts().to_dict(),listing_disagreements=int((~s.listing_agrees).sum()),active_collisions=int(s.active_collision.sum()),canonical_only_partition_rows=int((s.canonical_financial_partition&~s.active_financial_partition&s.master_listed).sum()),comparison_by_clock=j.groupby('clock').comparison_eligible.sum().to_dict(),comparison_negative_pe_by_clock=j[j.comparison_eligible&j.vendor_pe_ttm.lt(0)].groupby('clock').size().to_dict(),strict_PIT=False,denominator_agreement_evaluated=False)
    js(out/'summary.json',summary)
    paths +=[sp,fp,Path(__file__),ROOT/'protocols/r117.json',ROOT/'src/common.py'];js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},outputs={n:sha(out/n) for n in ['code_intervals.parquet','stock_identity.parquet','linked_monthly.parquet','coverage.csv','summary.json']}));print(summary)
if __name__=='__main__':run()
