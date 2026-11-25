from common_inputs import *
sys.path.append(str(PRIVATE.parent/'src'))
from features import compute

def main():
    ref=pd.read_parquet(SEAL)
    print(ref.columns,flush=True)
    fields='qfq_close qfq_open qfq_high qfq_low volume money turnover_rate daily_members'.split()
    raw=[pd.read_parquet(PRIVATE/(f+'.parquet')) for f in fields]
    days=raw[0].index
    features=compute(*raw,pd.read_parquet(PRIVATE/'market.parquet').close)
    # Include the nine dates that straddle the historical split for H5 calendars.
    c=raw[0]
    eligible=raw[-1] & (c.gt(0)&np.isfinite(c)).rolling(61).sum().eq(61) & (c.shift(5)/c.shift(60)).ne(1) & (c/c.shift(5)).ne(1)
    frames=[]
    for i in range(days.get_loc(ref.signal_date.min()),days.get_loc('2026-10-12')-1):
        names=c.columns[eligible.iloc[i]]
        f=pd.DataFrame({k:features[k].iloc[i].reindex(names) for k in COLS})
        f=f.loc[f.notna().mean(axis=1)>=.8]
        frames.append(f.rename_axis('instrument').reset_index().assign(signal_date=days[i],entry_idx=i+1))
    full=pd.concat(frames,ignore_index=True)
    rows=[]
    for q,g in full.groupby(full.signal_date.dt.to_period('Q').astype(str)):
        if not (OUT/'models'/q).is_dir():continue
        tree=lgb.Booster(model_file=str(OUT/'models'/q/'tree_rank.txt'))
        med=pd.Series(json.loads((OUT/'models'/q/'medians.json').read_text()))
        r=json.loads((LINEAR/'models'/(q+'.json')).read_text())['baseline']
        efile=next((TRACK.parent.parent).glob('37_*/extensions/original78*/local_cache/models/'+q+'_E1*.json'))
        x=g[COLS]
        cols=KEY+['entry_idx','vol20','amp20','mom5','dd60','mom60','market_mom20','market_vol20']
        rows.append(g[cols].assign(R=predict(x,r),E=predict(x,json.loads(efile.read_text())),T=tree.predict(x.fillna(med),num_threads=3),T20=tree.predict(x.fillna(med),num_iteration=20,num_threads=3)))
    data=pd.concat(rows).sort_values(KEY)
    ref0=pd.read_parquet(OUT/'scores.parquet').set_index(KEY)
    d=data.set_index(KEY)
    for a,b in [('R','baseline'),('T','tree_rank')]:
        np.testing.assert_allclose(d.loc[ref0.index,a],ref0[b],atol=1e-10,rtol=0)
    check=d.loc[d.index.get_level_values(0).isin(ref.signal_date)].sort_index()
    ref=ref.set_index(KEY).sort_index()
    pd.testing.assert_index_equal(check.index,ref.index)
    np.testing.assert_allclose(check.R,ref.RANK_MSE_78,atol=1e-10,rtol=0)
    data.to_parquet(DEST/'daily_scores.parquet',index=False)
if __name__=='__main__':main()
