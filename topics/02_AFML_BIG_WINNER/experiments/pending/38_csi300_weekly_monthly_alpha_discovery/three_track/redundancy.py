from shared import *
import warnings

f = pd.read_parquet(PRIVATE/'features.parquet', columns=KEY+['score_eligible']+COLS)
y = pd.read_parquet(PRIVATE/'labels.parquet', columns=KEY+['target_z','h10','h10_mature'])
eligible = f[f.score_eligible].merge(y,on=KEY,validate='1:1')
h = outer()
training = eligible.dropna(subset=['target_z','h10']).copy()
dates, correlations, covers, both, sizes, ics, exact = [], [], [], [], [], [], []
a,b = np.triu_indices(len(COLS),1)
for d,g in eligible.groupby('signal_date'):
    z = g[COLS]
    valid = z.notna().to_numpy(dtype='int32')
    common = (valid.T @ valid)[a,b]
    corr = z.corr('spearman').to_numpy()[a,b]
    # Group identical columns including missing positions before any imputation.
    vals = z.to_numpy().T.copy()
    vals[np.isnan(vals)] = np.nan
    keys = [v.tobytes() for v in vals]
    exact.append([keys[i]==keys[j] for i,j in zip(a,b)])
    dates.append(d); correlations.append(corr); covers.append(valid.sum(axis=0))
    sizes.append(len(z)); both.append(common)
    ics.append(g[COLS+['h10']].corr('spearman').h10.iloc[:-1].to_numpy())
dates=pd.DatetimeIndex(dates)
correlations,covers,both,sizes,ics,exact=map(np.asarray,(correlations,covers,both,sizes,ics,exact))
pairs=[]; factors=[]; scores=[]; fits={}
for q,g in h.groupby(h.signal_date.dt.to_period('Q')):
    tr=training[training.h10_mature.lt(q.start_time)].copy()
    tr['target_rank']=tr.groupby('signal_date').h10.transform(lambda x:x.rank()/(len(x)+1)-.5)
    used=dates.isin(tr.signal_date)
    # All instruments on a given training date share the scheduled H10 maturity.
    assert eligible.loc[eligible.signal_date.isin(dates[used]),'h10_mature'].dropna().max()<q.start_time
    r=correlations[used]; enough=both[used]*2>=sizes[used,None]
    pos=((r>=.95)&enough).sum(axis=0); neg=((r<=-.95)&enough).sum(axis=0)
    duplicate=exact[used].all(axis=0)
    passed=(np.maximum(pos,neg)>=.8*used.sum())|duplicate
    links={tuple(sorted((i,j))) for i,j,p in zip(a,b,passed) if p}
    coverage=covers[used].sum(axis=0)/sizes[used].sum()
    kept=[]; reasons={}
    for i in np.argsort(-coverage,kind='stable'):
        rep=next((j for j in kept if not COLS[j].startswith('market_') and tuple(sorted((i,j))) in links),None)
        if rep is None or COLS[i].startswith('market_'): kept.append(i)
        else: reasons[i]=rep
    cols=[c for i,c in enumerate(COLS) if i in kept]
    assert ('mom1' in cols) != ('ret_lag0' in cols)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        pairs.append(pd.DataFrame(dict(quarter=str(q),first=np.array(COLS)[a],second=np.array(COLS)[b],days=used.sum(),valid=np.isfinite(r).sum(0),median=np.nanmedian(r,axis=0),positive_days=(r>0).sum(0),negative_days=(r<0).sum(0),positive_hits=pos,negative_hits=neg,exact=duplicate,passed=passed)))
        factors.append(pd.DataFrame(dict(quarter=str(q),feature=COLS,coverage=coverage,mean_ic=np.nanmean(ics[used],axis=0),sd_ic=np.nanstd(ics[used],axis=0),kept=[i in kept for i in range(78)],representative=[COLS[reasons[i]] if i in reasons else None for i in range(78)],market_constant=[c.startswith('market_') for c in COLS])))
    fit=ridge(tr,cols,'target_rank'); fits[str(q)]=fit
    scores.append(g[KEY].assign(pruned=predict(g,fit)))
pd.concat(pairs).to_parquet(OUT/'fold_pairs.parquet',index=False)
pd.concat(factors).to_csv(OUT/'fold_factors.csv',index=False)
pd.concat(scores).to_parquet(OUT/'pruned_scores.parquet',index=False)
(OUT/'pruned_models.json').write_text(json.dumps(fits))
