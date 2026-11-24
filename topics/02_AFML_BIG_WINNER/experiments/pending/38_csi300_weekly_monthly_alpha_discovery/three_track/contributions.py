from shared import *

def group(c):
    if c.startswith(('ret_lag','xsret_lag')): return 0
    if c.startswith(('mom','seg')): return 1
    if c.startswith('pos'): return 2
    if c.startswith(('vol5','vol20','vol60','amp','dd')): return 3
    if c.startswith(('volume','turnover','money')): return 4
    assert c.startswith('market_')
    return 5

def main():
    sys.path.insert(0,str(PRIVATE.parent/'src'))
    from features import compute
    mats=[pd.read_parquet(PRIVATE/(k+'.parquet')) for k in ['qfq_close','qfq_open','qfq_high','qfq_low','volume','money','turnover_rate','daily_members']]
    c=mats[0]; days=c.index; anchor=days.get_loc('2021-01-08')
    eligible=mats[-1] & (c.gt(0)&np.isfinite(c)).rolling(61).sum().eq(61) & (c.shift(5)/c.shift(60)).ne(1) & (c/c.shift(5)).ne(1)
    feats=compute(*mats,pd.read_parquet(PRIVATE/'market.parquet').close)
    rows=[]
    for i in range(anchor%10,anchor,10):
        if days[i].year<2019: continue
        j=np.flatnonzero(eligible.iloc[i])
        g=pd.DataFrame({col:feats[col].to_numpy()[i,j] for col in COLS},index=c.columns[j])
        g=g[g.notna().mean(axis=1)>=.8]
        rows.append(g.rename_axis('instrument').reset_index().assign(signal_date=days[i],entry_idx=i+1,exit_idx=i+11))
    h=pd.concat(rows+[outer()],ignore_index=True)
    oldmodels=json.loads((ROUNDS/'51_earlier_replication/results/models.json').read_text())
    frozen=pd.read_parquet(OLD/'local_cache/predictions.parquet')[KEY+[BASE]]
    groups=np.array([group(c) for c in COLS])
    result=[]
    for q,g in h.groupby(h.signal_date.dt.to_period('Q')):
        key=f'{q}_{BASE}'
        fit=oldmodels[key] if key in oldmodels else json.loads((OLD/'local_cache/models'/(key+'.json')).read_text())
        assert fit['columns']==COLS
        v=g[COLS].to_numpy()
        v=(np.where(np.isnan(v),fit['median'],v)-fit['mean'])/fit['sd']*fit['coef']
        res=g[KEY+['entry_idx','exit_idx']].copy()
        for k in range(6): res[f'g{k}']=v[:,groups==k].sum(axis=1)
        res['g5']+=fit['intercept']
        result.append(res)
    panel=pd.concat(result).merge(labels(),on=KEY,how='left',validate='1:1')
    check=panel.merge(frozen,on=KEY,validate='1:1')
    np.testing.assert_allclose(check[[f'g{k}' for k in range(6)]].sum(axis=1),check[BASE],atol=1e-12)
    panel.merge(pd.read_parquet(OUT/'pruned_scores.parquet'),on=KEY,how='left',validate='1:1').to_parquet(OUT/'contributions.parquet',index=False)

if __name__=='__main__': main()
