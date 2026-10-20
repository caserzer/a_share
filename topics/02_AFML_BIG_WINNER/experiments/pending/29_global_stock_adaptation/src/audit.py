"""Freeze outcome-blind target selection and audit inherited OOS/data boundaries."""
from common import *


def select_cohort(snapshot,metadata):
    allowed=['date','instrument','industry_id','industry_sector','industry_stale','industry_published','log_cap','vol63','board']
    s=snapshot[allowed].merge(metadata[['instrument','listing_date','delist_date','name']],on='instrument',validate='one_to_one').copy()
    assert s.date.nunique()==1
    s['size_bin']=np.searchsorted(s.log_cap.quantile([1/3,2/3]).to_numpy(),s.log_cap,side='right')
    single=s.sort_values(['listing_date','instrument']).instrument.iloc[0]
    chosen=[single];queues={}
    for industry,g in s.groupby('industry_id'):
        bybin=[]
        for b,z in g.groupby('size_bin'):
            stocks=sorted(z.instrument,key=lambda x:tie(f'cohort:{b}:{x}'))
            bybin.append(stocks)
        queue=[]
        while any(bybin):
            for b in bybin:
                if b:queue.append(b.pop(0))
        queues[industry]=[x for x in queue if x!=single]
    industries=sorted(queues,key=lambda x:tie('industry:'+x))
    while len(chosen)<C['cohort']['size'] and any(queues.values()):
        for industry in industries:
            if queues[industry] and len(chosen)<C['cohort']['size']:chosen.append(queues[industry].pop(0))
    result=s.set_index('instrument').loc[chosen].reset_index();result['selection_order']=range(len(result))
    return single,result


def main():
    assert not (MANIFEST/'preregistration.json').exists()
    prior=json.loads((MANIFEST/'prior_preservation.json').read_text())
    assert all(digest(EP.parent/k)==v for k,v in prior.items())
    panelpath=EP28/'outputs/local_cache/panel.parquet';p=pd.read_parquet(panelpath)
    assert len(p)==43960 and not p.duplicated(['date','instrument']).any()
    metadata_path=TOPIC/'data/raw/akshare/status/instrument_metadata_target_universe.csv'
    meta=pd.read_csv(metadata_path,parse_dates=['listing_date','delist_date'])
    p=p.merge(meta[['instrument','listing_date','delist_date','name']],on='instrument',how='left',validate='many_to_one')
    p=p.sort_values(['date','instrument']).reset_index(drop=True);assert p.listing_date.notna().all()
    snapshot=p[p.date==C['cohort']['origin']];single,cohort=select_cohort(snapshot,meta)
    # Selection code does not accept outcomes/model scores. Perturbing them cannot affect selection.
    copy=snapshot.copy();copy['y_6']=np.arange(len(copy));again,check=select_cohort(copy,meta)
    pd.testing.assert_frame_equal(cohort,check);assert again==single
    records=json.loads(cohort.to_json(orient='records',date_format='iso'))
    write_json(EP/'configs/target_cohort.yaml',dict(origin=C['cohort']['origin'],single_stock=single,
        rule=C['cohort'],future_outcomes_not_used=True,source_population='EP28 D0 at first origin; inherited selection bias remains',companies=records))
    p.to_parquet(CACHE/'panel.parquet',index=False)
    files=[panelpath,metadata_path,EP28/'outputs/manifests/preregistration.json',EP28/'outputs/audits/data_gate.json',
           EP28/'outputs/audits/validation.json',EP28/'outputs/metrics/summary.csv',
           EP28/'outputs/manifests/prospective_lock.json']
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        files += [EP28/f'outputs/local_cache/{quarter}_predictions.parquet']
    pd.DataFrame([dict(path=str(f.relative_to(TOPIC)),sha256=digest(f),bytes=f.stat().st_size) for f in files]).to_csv(MANIFEST/'input_sources.csv',index=False)
    baseline=pd.read_parquet(EP28/'outputs/local_cache/all_predictions.parquet')
    for name in ['M_R','L2']:
        g=baseline[baseline.model.eq(name)]
        assert len(g)==29596 and g.actual.notna().sum()==27230
        assert int(np.nansum(labels(g.actual)))==4581
    known=p.industry_id.ne('UNKNOWN');assert (p.loc[known,'industry_published']<p.loc[known,'date']).all()
    assert (p.feature_cutoff<=p.date).all()
    test=p[p.date>=C['prediction_start']]
    eligibility=[]
    for stock in cohort.instrument:
        g=test[test.instrument==stock];row=meta[meta.instrument==stock].iloc[0]
        eligibility.append(dict(instrument=stock,name=row['name'],predicted_months=g.date.nunique(),known_labels=int(g.y_6.notna().sum()),
            missing_mature=int((g.end_6.notna()&g.y_6.isna()).sum()),unmature=int(g.end_6.isna().sum()),
            expected_origins=test.date.nunique(),not_in_D0_months=test.date.nunique()-g.date.nunique(),delist_date=row.delist_date))
    pd.DataFrame(eligibility).to_csv(AUDIT/'cohort_eligibility_coverage.csv',index=False)
    warm=[]
    for q in pd.period_range(C['warmup_start'],C['warmup_end'],freq='Q'):
        tr=p[(p.date<q.start_time)&(p.end_6<q.start_time)&p.y_6.notna()]
        warm.append(dict(quarter=str(q),rows=len(tr),months=tr.date.nunique(),events=int((tr.y_6<-.2).sum()),max_label=str(tr.end_6.max())))
        assert len(tr)>1000 and tr.y_6.lt(-.2).nunique()==2
    write_json(AUDIT/'warmup_feasibility.json',warm)
    write_json(AUDIT/'data_gate.json',dict(passed_for_limited_D0_exploration=True,independent_confirmation_allowed=False,
        D0_original_columns_preserved=True,single_stock=single,cohort_size=len(cohort),cohort_industries=cohort.industry_id.nunique(),
        first_origin_eligible=len(snapshot),prior_files_preserved=len(prior),input_panel_sha256=digest(panelpath),
        EP29_panel_sha256=digest(CACHE/'panel.parquet'),global_historical_residuals_source='2019-2020 new purged quarterly OOS; 2021+ immutable EP28 OOS',
        financial_and_valuation_similarity_excluded=True,stale_industry_peer_fallback=True,D1_formal_replacement=False,
        limits=['legacy lifetime ST and stock-pool bias','qfq is not certified total return','original financial/valuation vintages absent',
                'delisting settlement and special actions incomplete','published industry snapshots are retrospective proxy evidence',
                'all 2021+ history repeatedly researched; no untouched holdout']))
    print('Single',single,'cohort',len(cohort),'industries',cohort.industry_id.nunique(),'warmup quarters',len(warm),flush=True)


if __name__=='__main__':main()
