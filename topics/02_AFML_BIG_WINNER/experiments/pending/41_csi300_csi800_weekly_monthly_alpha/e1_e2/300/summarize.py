from run import *
from runpy import run_path
monthly=run_path(str(HERE.parents[1]/'p2/summarize.py'))['monthly']

def make():
    d=pd.read_parquet(DEST/'daily.parquet');ords=pd.read_parquet(DEST/'orders.parquet')
    check=d.groupby(['scope','arm','idx']).fee.sum()
    verified=ords.groupby(['scope','arm','idx']).fee.sum().reindex(check.index,fill_value=0)
    np.testing.assert_allclose(check,verified,atol=1e-12)
    ref=pd.read_parquet(OUT/'funded_daily.parquet').query('mul==1 and arm in ["tree","hold"]').copy()
    ref['arm']='baseline_'+ref.arm
    z=d.merge(ref,on=['arm','scope','idx'],validate='1:1')
    assert len(z)==len(ref)
    np.testing.assert_allclose(z.nav_x,z.nav_y,atol=1e-11)
    mo=pd.concat([monthly(v).assign(scope=scope,arm=arm) for (scope,arm),v in d.groupby(['scope','arm'])])
    mo.to_csv(DEST/'full_months.csv',index=False)
    rows=[]
    for scope,g in mo.groupby('scope'):
        z=g.pivot(index='month',columns='arm',values=['net','gross','fee','buy','sell'])
        for arm in z.net:
            if arm.startswith('baseline') or arm.endswith('mechanical'):continue
            for baseline in (['baseline_hold','baseline_tree',arm+'_mechanical'] if arm.startswith('E2') else ['baseline_'+arm.split('_')[1],arm+'_mechanical']):
                gap=z.net[arm]-z.net[baseline]
                rng=np.random.default_rng(4101)
                ix=rng.integers(0,len(gap)-2,size=(10000,(len(gap)+2)//3,1))+np.arange(3)
                boot=gap.to_numpy()[ix.reshape(10000,-1)[:,:len(gap)]].mean(axis=1)
                lo,hi=np.quantile(boot*1e4,[.025,.975])
                rows.append(dict(scope=scope,arm=arm,base=baseline,n=len(gap),gap_bp=gap.mean()*1e4,lo=lo,hi=hi,
                     gross_bp=(z.gross[arm]-z.gross[baseline]).mean()*1e4,fee_bp=(z.fee[arm]-z.fee[baseline]).mean()*1e4,
                     rest_bp=gap.drop(gap.nlargest(3).index).mean()*1e4,
                     delta_turnover=(z.buy[arm]+z.sell[arm]-z.buy[baseline]-z.sell[baseline]).mean()))
    pd.DataFrame(rows).to_csv(DEST/'comparisons.csv',index=False)
    dec=pd.read_parquet(DEST/'decisions.parquet')
    dec.groupby(['scope','arm']).agg(decisions=('entry_idx','size'),selected=('n','sum'),natural=('natural_buys','sum'),nominal=('turnover_budget','sum')).to_csv(DEST/'decision_counts.csv')
if __name__=='__main__':make()
