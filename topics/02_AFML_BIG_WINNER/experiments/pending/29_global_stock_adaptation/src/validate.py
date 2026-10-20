"""Post-registration reconstruction and provenance audit; no new fitted candidates."""
import argparse
from catboost import CatBoostClassifier
from common import *
from global_model import freeze
from hierarchical_model import one_origin
from issuer_adaptation import nonoverlap_count,merged_event_stages
from peer_prior import peer_sets
from audit import select_cohort
from evaluate import weighted_intervals


def validate_baselines():
    panel=pd.read_parquet(CACHE/'panel.parquet');replayed=reused=0
    for r in json.loads((AUDIT/'global_fit_audit.json').read_text()):
        q=pd.Period(r['quarter']);tr=panel[(panel.date<q.start_time)&(panel.end_6<q.start_time)&panel.y_6.notna()]
        te=panel[panel.date.dt.to_period('Q')==q].reset_index(drop=True)
        assert keyhash(tr)==r['train_keys_sha256'] and keyhash(te)==r['test_keys_sha256']
        assert tr.end_6.max()<q.start_time
        path=CACHE/f"global_{q}_{r['foundation']}.parquet";assert digest(path)==r['sha256'];z=pd.read_parquet(path)
        if r['fitted']:
            model=CatBoostClassifier();model.load_model(str(CACHE/f"global_{q}_{r['foundation']}.cbm"))
            p=model.predict_proba(te[C['global_features'][r['foundation']]])[:,1];replayed+=1
        else:
            old=pd.read_parquet(EP28/f'outputs/local_cache/{q}_predictions.parquet')
            p=old[old.model.eq(r['foundation'])].probability.to_numpy();reused+=1
        np.testing.assert_allclose(p,z.G,atol=1e-14,rtol=0)
        np.testing.assert_allclose(z.actual,te.y_6,atol=0,rtol=0,equal_nan=True)
    assert replayed==16 and reused==44
    return dict(new_global_models_replayed=replayed,inherited_quarter_foundations_reused=reused)


def replay_adaptation(foundation):
    source=pd.read_parquet(CACHE/f'global_oos_{foundation}.parquet').sort_values(['date','instrument']).reset_index(drop=True)
    full=pd.read_parquet(CACHE/f'real_{foundation}_all.parquet')
    previous=pd.DataFrame(columns=list(source.columns)+['GP']);origins=rows=0
    for date,current in source.groupby('date',sort=True):
        saved=full[full.date==date].reset_index(drop=True)
        expected,peers,audit=one_origin(current.reset_index(drop=True),previous)
        pd.testing.assert_frame_equal(saved,expected,check_exact=False,atol=1e-13,rtol=1e-13)
        path=CACHE/f'real_{foundation}_{date.date()}_peers.parquet';stored=pd.read_parquet(path)
        if peers.shape==(0,0):
            # Parquet changes the inferred type of a zero-column empty Index.
            assert stored.shape==(0,0)
        else:pd.testing.assert_frame_equal(stored,peers,check_exact=True)
        assert not len(saved) or (saved.history_max_label.dropna()<date).all()
        previous=pd.concat([previous,saved],ignore_index=True);origins+=1;rows+=len(saved)
        if date.month==1:print('Replay',foundation,date.date(),flush=True)
    known=full[full.date>=C['prediction_start']]
    zero=known[known.nonoverlap_events<2]
    assert zero.individual_offset_G.eq(0).all() and zero.individual_offset_GP.eq(0).all()
    fallback=known[known.adaptability_group=='global_fallback']
    np.testing.assert_allclose(fallback.GPI,fallback.G,atol=1e-14,rtol=0)
    assert ((known[C['formal_models']]>0)&(known[C['formal_models']]<1)).all().all()
    assert known.GPI.between(known.GPI_lower,known.GPI_upper).all()
    return dict(foundation=foundation,origins=origins,rows=rows,rare_event_rows_forced_zero=len(zero),global_fallback_rows=len(fallback))


def validate_scores():
    monthly=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date'])
    cohort=json.loads((EP/'configs/target_cohort.yaml').read_text());stocks=[r['instrument'] for r in cohort['companies']]
    checks=0;weighting_checks=[]
    for foundation in ['M_R','L2']:
        f=pd.read_parquet(CACHE/f'evaluation_{foundation}.parquet');assert not f.duplicated(['date','instrument']).any()
        names=C['formal_models']+(C['diagnostic_models'] if foundation=='M_R' else [])
        for population,g in [('D0',f),('cohort40',f[f.instrument.isin(stocks)])]:
            for date,z in g[g.actual.notna()].groupby('date'):
                y=(z.actual.to_numpy()<-.2).astype(float)
                for name in names:
                    r=monthly[(monthly.foundation==foundation)&(monthly.population==population)&(monthly.model==name)&(monthly.date==date)].iloc[0]
                    assert len(z)==r.rows and int(y.sum())==r.events
                    assert abs(float(np.mean((z[name].to_numpy()-y)**2))-r.brier)<1e-14;checks+=1
            for block in [6,12]:
                weighting_checks+= [dict(foundation=foundation,population=population,**r) for r in weighted_intervals(g,'GPI','G',block,True)]
    intervals=pd.read_csv(OUT/'paired_intervals.csv')
    for r in weighting_checks:
        row=intervals[(intervals.foundation==r['foundation'])&(intervals.population==r['population'])&(intervals.candidate=='GPI')&
            (intervals.baseline=='G')&(intervals.weighting==r['weighting'])&(intervals.block==r['block'])].iloc[0]
        for field in ['estimate','low95','high95','low_secondary','high_secondary']:assert abs(row[field]-r[field])<1e-13
    return dict(monthly_Brier_reconstructions=checks,primary_weighted_intervals_reconstructed=len(weighting_checks))


def main():
    freeze();base=validate_baselines();replays=[]
    for name in ['M_R','L2']:
        receipt=AUDIT/f'replay_{name}.json'
        if receipt.exists():
            r=json.loads(receipt.read_text())
            for path,h in r['files'].items():assert digest(EP/path)==h
            replays.append(r['result'])
        else:replays.append(replay_adaptation(name))
    scores=validate_scores()
    p=pd.read_parquet(CACHE/'panel.parquet');meta=pd.read_csv(TOPIC/'data/raw/akshare/status/instrument_metadata_target_universe.csv',parse_dates=['listing_date','delist_date'])
    original=pd.read_parquet(EP28/'outputs/local_cache/panel.parquet').sort_values(['date','instrument']).reset_index(drop=True)
    pd.testing.assert_frame_equal(p[original.columns].reset_index(drop=True),original,check_exact=True)
    single,cohort=select_cohort(p[p.date==C['cohort']['origin']],meta)
    registered=json.loads((EP/'configs/target_cohort.yaml').read_text())
    assert single==registered['single_stock'] and cohort.instrument.tolist()==[r['instrument'] for r in registered['companies']]
    prior=json.loads((MANIFEST/'prior_preservation.json').read_text())
    for path,h in prior.items():assert digest(EP.parent/path)==h,path
    inputs=pd.read_csv(MANIFEST/'input_sources.csv')
    for r in inputs.itertuples():assert digest(TOPIC/r.path)==r.sha256
    assert json.loads((AUDIT/'synthetic_controls.json').read_text())['all_passed']
    identity=json.loads((AUDIT/'identity_control.json').read_text())
    result=dict(passed=True,**base,**scores,adaptation_replays=replays,prior_files_preserved=len(prior),input_files_verified=len(inputs),
        selection_reconstructed=True,identity_control_suspicious_gain=identity['suspicious_individual_gain'],
        independent_validation=False,posterior_intervals_conditional_approximation=True)
    write_json(AUDIT/'validation.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--foundation',choices=['M_R','L2']);args=parser.parse_args()
    if args.foundation:
        freeze();result=replay_adaptation(args.foundation)
        paths=[CACHE/f'global_oos_{args.foundation}.parquet',CACHE/f'real_{args.foundation}_all.parquet']
        paths+=sorted(CACHE.glob(f'real_{args.foundation}_*_peers.parquet'))
        paths+=[EP/'src'/f'{name}.py' for name in ['common','global_model','hierarchical_model','issuer_adaptation','peer_prior','local_baseline','validate']]
        write_json(AUDIT/f'replay_{args.foundation}.json',dict(result=result,files={str(p.relative_to(EP)):digest(p) for p in paths}))
    else:main()
