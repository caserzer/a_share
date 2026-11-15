"""Historical evidence matrix; no stage inference or combined allocation score."""
import pandas as pd
from common import *
from versioned_observations import capture,verify_bundle


def assemble(obs,expectation,valuation,mechanism,asof,clock):
    date=pd.Timestamp(asof);result=obs.copy()
    if not pd.to_datetime(result['asof']).eq(date).all():raise ValueError('snapshot date mismatch')
    if result.duplicated(KEY).any():raise ValueError('duplicate observation identity')
    for name in ['momentum_contribution','volatility_contribution','drawdown_contribution']:result[name]=np.nan
    for _,g in result[result.price_ready].groupby(['era','level']):
        ranks=g[['mom20','mom60','vol20','dd60']].apply(centered_rank)
        result.loc[g.index,'momentum_contribution']=(ranks.mom20+ranks.mom60)/6
        result.loc[g.index,'volatility_contribution']=-ranks.vol20/3
        result.loc[g.index,'drawdown_contribution']=ranks.dd60/3
    e=expectation[(expectation.date<=date)&expectation.fiscal_year.eq(date.year+1)].copy()
    if e.duplicated(KEY+['date']).any():raise ValueError('duplicate expectation identity/date')
    e=e.sort_values('date').groupby(KEY).tail(1)
    e=e[KEY+['date','known','members','coverage','eligible','full_factor']].rename(columns={c:'expectation_'+c for c in ['date','known','members','coverage','eligible','full_factor']})
    result=result.merge(e,on=KEY,how='left',validate='one_to_one')
    result['expectation_age_days']=(date-result.expectation_date).dt.days
    result['expectation_status']=np.select([result.expectation_date.isna(),result.expectation_date.lt(date),~result.expectation_eligible.eq(True)],['missing_snapshot','older_snapshot_not_current','insufficient_issuer_coverage'],default='historical_proxy_available')
    v=valuation[valuation.date.eq(date)][KEY+['pe_rank504','pe_rank504_coverage','pe_positive_fraction','turn_rank504']]
    result=result.merge(v,on=KEY,how='left',validate='one_to_one')
    result['valuation_status']=np.where(result.pe_rank504.notna(),'historical_proxy_coverage_disclosed','missing_valuation')
    result['diffusion_status']=np.where(result[['breadth21','breadth63']].notna().all(axis=1),'observed_price_breadth_not_economic_stage','missing_diffusion')
    mech=mechanism[pd.to_datetime(mechanism['asof']).eq(date)&mechanism.clock.eq(clock)]
    if set(map(tuple,mech[KEY].to_numpy()))!=set(map(tuple,result[KEY].to_numpy())):raise ValueError('mechanism catalogue mismatch')
    result=result.merge(mech[KEY+['facts','observed_issuers','all_member_proxy_sample_fraction','evidence_state']],on=KEY,validate='one_to_one')
    result['clock']=clock
    result['clock_scope']='company_facts_only_other_dimensions_historical_proxy_not_acquisition_gated'
    result['holdings_crowding_status']='missing_holdings_data'
    result['dual_crowding_status']='unknown_not_inferred_from_turnover'
    result['economic_stage']='not_established'
    result['capture_kind']='historical_replay'
    result['next_update']='manual_after_new_local_source_version'
    result['price_invalidation']=np.where(result.price_ready,'none_detected_in_price_inputs','missing_or_insufficient_price_inputs')
    result['stage_invalidation']='economic_stage_not_validated'
    return result


def changes(old,new):
    if set(old.clock)!=set(new.clock) or old.clock.nunique()!=1:raise ValueError('clock mismatch')
    merged=old.merge(new,on=KEY+['clock'],how='outer',suffixes=('_old','_new'),validate='one_to_one',indicator=True)
    merged['rank_change']=merged.price_rank_new-merged.price_rank_old
    merged['fact_count_change']=merged.facts_new-merged.facts_old
    merged['readiness_lost']=merged.price_ready_old.eq(True)&~merged.price_ready_new.eq(True)
    merged['readiness_gained']=~merged.price_ready_old.eq(True)&merged.price_ready_new.eq(True)
    merged['sample_fraction_change']=merged.all_member_proxy_sample_fraction_new-merged.all_member_proxy_sample_fraction_old
    merged['interpretation']='evidence_or_universe_change_not_proven_economic_transition'
    return merged[KEY+['clock','asof_old','asof_new','rank_change','fact_count_change','sample_fraction_change','readiness_lost','readiness_gained','_merge','interpretation']]


def run():
    out=ROOT/'outputs/r25/monitor';out.mkdir(exist_ok=True)
    paths=[ROOT/'protocols/r21.json',ROOT/'outputs/r20/full_catalogue_evidence.csv',ROOT/'data/r25_revision_coverage.parquet',CACHE/'joint_pe_v35/daily_expansion.parquet',Path(__file__)]
    protocol=json.loads(paths[0].read_text());mech=pd.read_csv(paths[1]);e=pd.read_parquet(paths[2]);v=pd.read_parquet(paths[3],columns=KEY+['date','pe_rank504','pe_rank504_coverage','pe_positive_fraction','turn_rank504'])
    frames=[];bundles=[]
    for date in protocol['dates']:
        p=capture(ROOT/'data/update_store',[CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet'],CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'outputs/universe_current.csv',date)
        verify_bundle(p);bundles.append(dict(path=str(p),manifest_sha256=sha(p/'manifest.json')))
        obs=pd.read_parquet(p/'observations.parquet')
        for clock in protocol['clocks']:frames.append(assemble(obs,e,v,mech,date,clock))
    matrix=pd.concat(frames,ignore_index=True);matrix.to_csv(out/'evidence_matrix.csv',index=False)
    deltas=pd.concat([changes(matrix[matrix['asof'].eq(pd.Timestamp(protocol['dates'][0]))&matrix.clock.eq(clock)],matrix[matrix['asof'].eq(pd.Timestamp(protocol['dates'][1]))&matrix.clock.eq(clock)]) for clock in protocol['clocks']],ignore_index=True)
    deltas.to_csv(out/'historical_changes.csv',index=False)
    summary=matrix.groupby(['asof','clock','level']).agg(rows=('industry_code','size'),price_ready=('price_ready','sum'),pe_known=('pe_rank504','count'),turnover_known=('turn_rank504','count'),expectation_current=('expectation_status',lambda x:int(x.eq('historical_proxy_available').sum())),expectation_older=('expectation_status',lambda x:int(x.eq('older_snapshot_not_current').sum())),with_company_facts=('facts',lambda x:int(x.gt(0).sum()))).reset_index()
    summary.to_csv(out/'summary.csv',index=False)
    js(out/'receipt.json',dict(status='HISTORICAL_EVIDENCE_ONLY',reads={str(p):sha(p) for p in paths},bundles=bundles,rows=len(matrix),changes=len(deltas),stage_probabilities=0,prospective_records=0,outputs={n:sha(out/n) for n in ['evidence_matrix.csv','historical_changes.csv','summary.csv']}))
    print(summary.to_string(index=False))

if __name__=='__main__':run()
