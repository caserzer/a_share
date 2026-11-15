"""Independent interval/master/listing and all monthly financial joins."""
import pandas as pd
from common import *
def run():
    out=ROOT/'outputs/r117';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    releasefile=ROOT.parent/'30_pit_data_foundation_v1/outputs/pit_v5/release.json';root=Path(json.loads(releasefile.read_text())['path']);manifest=json.loads((root/'FULL_MANIFEST.json').read_text());expected={x['relative_path']:x['sha256'] for x in manifest};assert sha(root/'FULL_MANIFEST.json')==json.loads((root/'COMPLETE.json').read_text())['full_manifest_sha256']
    names=['inputs/normalized/securities.parquet','inputs/normalized/code_intervals.parquet','inputs/inputs/baseline/normalized/code_intervals.parquet']
    for n in names:assert sha(root/n)==expected[n]
    master=pd.read_parquet(root/names[0]).set_index('security_id');a=pd.read_parquet(root/names[1]);b=pd.read_parquet(root/names[2]);intervals=pd.read_parquet(out/'code_intervals.parquet')
    exp=pd.concat([a[['security_id','instrument','valid_from','valid_until_exclusive']].rename(columns={'valid_from':'start','valid_until_exclusive':'end'}).assign(source='continuity'),b[['security_id','historical_instrument','valid_from','valid_to']].rename(columns={'historical_instrument':'instrument','valid_from':'start','valid_to':'end'}).assign(source='bse_cutover')],ignore_index=True);exp['start']=pd.to_datetime(exp.start);exp['end']=pd.to_datetime(exp.end);pd.testing.assert_frame_equal(intervals,exp)
    s=pd.read_parquet(out/'stock_identity.parquet');f=pd.read_parquet(ROOT/'outputs/r116/monthly_ttm.parquet');old=pd.read_parquet(ROOT/'outputs/r112/valuation_monthly_coverage.parquet');old=old[old.date.isin(f.date.unique())].reset_index(drop=True);pd.testing.assert_frame_equal(s[old.columns],old)
    m=master.reindex(s.security_id).reset_index(drop=True)
    for c in ['exchange','listing_date','delist_date','bse_listing_proxy','identity_date_conflict']:pd.testing.assert_series_equal(s[c],m[c],check_names=False)
    pd.testing.assert_series_equal(s.canonical_instrument,m.instrument,check_names=False)
    for sid,g in s.groupby('security_id'):
        iv=exp[exp.security_id==sid]
        for x in g.itertuples():
            inst=x.canonical_instrument;status='static_metadata_proxy'
            if len(iv):
                matched=[r.instrument for r in iv.itertuples() if (pd.isna(r.start) or r.start<=x.date) and (pd.isna(r.end) or r.end>x.date)]
                inst=matched[0] if len(matched)==1 else None;status='explicit_interval_proxy' if len(matched)==1 else 'missing_code_interval' if not matched else 'ambiguous_code_interval'
            if pd.isna(x.canonical_instrument):inst=None;status='missing_master'
            assert status==x.identity_status and ((pd.isna(inst) and pd.isna(x.active_instrument)) or inst==x.active_instrument)
    listing=m.listing_date.where(m.exchange.ne('BJ'),m.bse_listing_proxy);active=s.date.ge(listing)&(m.delist_date.isna()|s.date.lt(m.delist_date))&m.identity_date_conflict.eq(False);assert active.equals(s.master_listed) and s.listing_agrees.equals(active.eq(s.listed));pd.testing.assert_series_equal(s.listing_start,listing,check_names=False)
    valid=s.active_instrument.str.fullmatch(r'(SH|SZ|BJ)[0-9]{6}',na=False);codes=(s.active_instrument.str[2:]+'.'+s.active_instrument.str[:2]).where(valid);pd.testing.assert_series_equal(codes,s.active_secucode,check_names=False)
    count=s[active&valid].groupby(['date','active_instrument']).security_id.nunique().to_dict();collision=pd.Series([count.get((d,c),0)>1 for d,c in zip(s.date,s.active_instrument)]);assert collision.equals(s.active_collision)
    eligible=s.identity_status.isin(['static_metadata_proxy','explicit_interval_proxy'])&valid&active&s.listing_agrees&~collision;assert eligible.equals(s.join_eligible);expected_join=codes.where(eligible);assert expected_join.isna().equals(s.join_secucode.isna());pd.testing.assert_series_equal(expected_join[eligible],s.loc[eligible,'join_secucode'],check_names=False)
    pd.testing.assert_series_equal(s.canonical_secucode,s.canonical_instrument.str[2:]+'.'+s.canonical_instrument.str[:2],check_names=False)
    companies=set(f.secucode);assert s.active_financial_partition.equals(codes.isin(companies));assert s.canonical_financial_partition.equals(s.canonical_secucode.isin(companies))
    j=pd.read_parquet(out/'linked_monthly.parquet');assert len(j)==2*len(s) and not j.duplicated(['security_id','date','clock']).any()
    for clock in ['notice','update']:
        q=j[j.clock==clock].reset_index(drop=True);pd.testing.assert_frame_equal(q[s.columns],s)
        ff=f[f.clock==clock].set_index(['secucode','date']).reindex(pd.MultiIndex.from_arrays([q.join_secucode,q.date])).reset_index(drop=True)
        for c in ['report_period','report_available_at','component_available_at','status','ttm_profit','report_age_days']:
            dest='financial_status' if c=='status' else c;a=q[dest];b=ff[c];assert a.isna().equals(b.isna());pd.testing.assert_series_equal(a[a.notna()],b[b.notna()],check_names=False)
    status=np.full(len(j),'financial_snapshot_linked',object);status[~j.active_financial_partition]='no_active_code_financial_partition';status[~j.join_eligible]='identity_unavailable_or_ambiguous';status[~j.master_listed]='not_listed';status[~j.listing_agrees]='listing_source_disagreement';assert np.array_equal(status,j.join_status)
    capital=np.isfinite(j.cap)&j.cap.gt(0)&np.isfinite(j.raw_close)&j.raw_close.gt(0)&np.isfinite(j.total_shares)&j.total_shares.gt(0)&j.share_effective_date.notna()&j.share_effective_date.le(j.date)&np.isclose(j.cap,j.raw_close*j.total_shares,rtol=1e-10,atol=0)
    ready=j.join_status.eq('financial_snapshot_linked')&j.financial_status.eq('known_ttm')&capital&np.isfinite(j.vendor_pe_ttm)&j.vendor_pe_ttm.ne(0);assert ready.equals(j.comparison_eligible)
    coverage=pd.read_csv(out/'coverage.csv').set_index(['clock','join_status','financial_state'])['rows'];expected=j.assign(financial_state=j.financial_status.fillna('not_linked')).groupby(['clock','join_status','financial_state']).size();pd.testing.assert_series_equal(coverage.sort_index(),expected.sort_index(),check_names=False)
    sm=json.loads((out/'summary.json').read_text());assert sm['identity_status']==s.identity_status.value_counts().to_dict();assert sm['comparison_by_clock']==j.groupby('clock').comparison_eligible.sum().to_dict();assert sm['comparison_negative_pe_by_clock']==j[j.comparison_eligible&j.vendor_pe_ttm.lt(0)].groupby('clock').size().to_dict()
    counts=dict(stock_month_rows=len(s),security_ids=s.security_id.nunique(),months=s.date.nunique(),linked_rows=len(j),listing_disagreements=int((~s.listing_agrees).sum()),active_collisions=int(s.active_collision.sum()),canonical_only_partition_rows=int((s.canonical_financial_partition&~s.active_financial_partition&s.master_listed).sum()))
    for k,v in counts.items():assert sm[k]==v
    assert not sm['strict_PIT'] and not sm['denominator_agreement_evaluated']
    js(out/'verification.json',dict(status='PASS',**counts,comparison_by_clock=sm['comparison_by_clock'],denominator_agreement_evaluated=False));print('PASS',counts)
if __name__=='__main__':run()
