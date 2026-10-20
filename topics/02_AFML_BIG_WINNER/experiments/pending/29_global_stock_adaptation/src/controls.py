"""Prespecified synthetic and identity controls; no seed or specification search."""
import argparse
from common import *
from walk_forward import walk
from global_model import freeze


def synthetic(world):
    rng=np.random.default_rng(C['controls']['seed']+(world=='zero'))
    nstocks=C['controls']['stocks'];nmonths=C['controls']['months'];warm=C['controls']['warmup_months']
    dates=pd.date_range('1985-01-31',periods=nmonths,freq='ME')
    sector=np.arange(nstocks)%10;sparse=np.arange(nstocks)%4==0
    persistent=rng.choice([-.8,.8],nstocks);persistent[np.arange(nstocks)%3==0]=0.
    effect=np.where(sector%2==0,.6,-.6)
    if world=='zero':persistent*=0;effect*=0
    risk=rng.normal(0,.3,nstocks);market=rng.choice([-.5,.5],int(np.ceil(nmonths/6)));rows=[]
    for b in range(len(market)):
        pg=expit(-1.+market[b]+risk);truth=expit(logodds(pg)+effect+persistent)
        event=rng.random(nstocks)<truth
        for t in range(b*6,min((b+1)*6,nmonths)):
            for j in range(nstocks):
                if sparse[j] and t<warm-12:continue
                d=dates[t];listing=dates[warm-12]-pd.DateOffset(years=1) if sparse[j] else dates[0]-pd.DateOffset(years=10)
                rows.append(dict(date=d,instrument=f'S{j:04}',log_cap=24.+risk[j],vol63=.2+np.exp(risk[j])*.1,
                    market_beta63=1+risk[j],industry_beta63=.8+risk[j]*.3,idiosyncratic_vol63=.15+np.exp(risk[j])*.03,
                    industry_id=f'SYN:{sector[j]}',industry_sector=f'S{sector[j]//2}',industry_stale=0.,
                    industry_published=d-pd.Timedelta(days=30),listing_date=listing,regime='high' if market[b]>0 else 'low',
                    board=0,G=float(pg[j]),actual=-.3 if event[j] else .05,label_end=d+pd.DateOffset(months=6),
                    true_probability=float(truth[j]),true_individual=float(persistent[j]),true_peer=float(effect[j]),sparse=bool(sparse[j])))
    return pd.DataFrame(rows),dates[warm]


def monthly_brier(f,models):
    rows=[]
    for date,g in f.groupby('date'):
        g=g[g.actual.notna()]
        if not len(g):continue
        y=labels(g.actual)
        for model in models:rows.append(dict(date=date,model=model,brier=float(np.mean((g[model]-y)**2))))
    return pd.DataFrame(rows)


def sparse_evaluation_rows(test,start):
    return test[test['sparse']&(test.date<start+pd.DateOffset(months=12))]


def synthetic_checks():
    results=[]
    for world in ['positive','zero']:
        source,start=synthetic(world);source.to_parquet(CACHE/f'synthetic_{world}_source.parquet',index=False)
        pred=walk(source,'synthetic_'+world,save_peers=False);test=pred[pred.date>=start].copy()
        m=monthly_brier(test,C['formal_models']+C['diagnostic_models']);m.to_csv(OUT/f'synthetic_{world}_monthly.csv',index=False)
        wide=m.pivot(index='date',columns='model',values='brier')
        contrasts={f'{a}-{b}':ci(wide[a]-wide[b],6) for a,b in [('GPI','G'),('GI','G'),('GP','G'),('GPI','GP')]}
        adapted=test[test.individual_reason.eq('adapted')]
        corr=float(adapted[['individual_offset_GP','true_individual']].corr().iloc[0,1]) if len(adapted) and world=='positive' else None
        if corr is not None and not np.isfinite(corr):corr=None
        sparse=sparse_evaluation_rows(test,start)
        peer_gain=float(np.mean((sparse.GP-sparse.true_probability)**2-(sparse.G-sparse.true_probability)**2))
        shrink_gain=float(np.mean((sparse.GPI-sparse.true_probability)**2-(sparse.L_unshrunk-sparse.true_probability)**2))
        zero=test[test.individual_events.eq(0)]
        safe=bool(((zero.GPI>0)&(zero.GPI<1)).all() and zero.individual_offset_GP.eq(0).all())
        if world=='positive':
            passed=(contrasts['GPI-G']['high95']<-C['controls']['synthetic_min_brier_gain'] and
                contrasts['GI-G']['estimate']<0 and corr is not None and corr>C['controls']['synthetic_min_correlation'] and peer_gain<0 and shrink_gain<0 and safe)
        else:
            passed=all(contrasts[k]['high95']>=-C['controls']['zero_effect_tolerance'] for k in ['GPI-G','GI-G','GPI-GP']) and safe and shrink_gain<0
        result=dict(world=world,passed=bool(passed),contrasts=contrasts,individual_signal_correlation=corr,
            adapted_rows=len(adapted),sparse_rows=len(sparse),peer_oracle_MSE_delta_sparse=peer_gain,
            shrinkage_vs_weak_local_oracle_MSE_delta_sparse=shrink_gain,zero_event_rows=len(zero),zero_event_no_false_zero_risk=safe)
        results.append(result);print(world,json.dumps(result),flush=True)
    write_json(AUDIT/'synthetic_controls.json',dict(all_passed=all(x['passed'] for x in results),results=results,no_seed_search=True))
    assert all(x['passed'] for x in results),'Synthetic control failure: stop corresponding real branch, no favorable retuning'


def permute_identity(source):
    result=source.copy();result['source_instrument']=result.instrument
    audit=[]
    for date,g in source.groupby('date'):
        z=g.copy()
        z['size_bin']=np.searchsorted(z.log_cap.quantile([.5]),z.log_cap)
        z['vol_bin']=np.searchsorted(z.vol63.quantile([.5]),z.vol63)
        for key,h in z.groupby(['industry_id','size_bin','vol_bin']):
            seed=int(hashlib.sha256(f"{C['controls']['permutation_seed']}:{date}:{key}".encode()).hexdigest()[:12],16)
            shuffled=np.random.default_rng(seed).permutation(h.instrument.to_numpy())
            result.loc[h.index,'instrument']=shuffled
            audit.append(dict(date=date,industry=key[0],size_bin=key[1],vol_bin=key[2],rows=len(h),changed=int((shuffled!=h.instrument).sum()),
                events=int(np.nansum(labels(h.actual))),missing=int(h.actual.isna().sum())))
    assert not result.duplicated(['date','instrument']).any()
    for col in source:
        if col!='instrument':pd.testing.assert_series_equal(result[col],source[col])
    return result,pd.DataFrame(audit)


def identity():
    source=pd.read_parquet(CACHE/'global_oos_M_R.parquet');shuffled,audit=permute_identity(source)
    shuffled.to_parquet(CACHE/'identity_source.parquet',index=False);audit.to_csv(AUDIT/'identity_permutation.csv',index=False)
    pred=walk(shuffled,'identity',save_peers=False);test=pred[pred.date>=C['prediction_start']]
    m=monthly_brier(test,C['formal_models']);m.to_csv(OUT/'identity_monthly.csv',index=False)
    wide=m.pivot(index='date',columns='model',values='brier')
    checks=[dict(comparison=f'{a}-{b}',**ci(wide[a]-wide[b],block)) for a,b in [('GI','G'),('GPI','GP'),('GPI','G')] for block in C['bootstrap']['blocks']]
    write_json(AUDIT/'identity_control.json',dict(comparisons=checks,identity_changed_fraction=float(audit.changed.sum()/audit.rows.sum()),
        row_features_probabilities_outcomes_kept_together=True,events_and_missingness_per_condition_preserved=True,
        interpretation='descriptive identity-persistence control; preserved common/industry effects can still be predictive',
        suspicious_individual_gain=any(r['high95']<-C['controls']['zero_effect_tolerance'] for r in checks if r['comparison'] in ['GI-G','GPI-GP'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['synthetic','identity']);args=parser.parse_args()
    freeze()
    if args.mode=='synthetic':synthetic_checks()
    else:identity()
