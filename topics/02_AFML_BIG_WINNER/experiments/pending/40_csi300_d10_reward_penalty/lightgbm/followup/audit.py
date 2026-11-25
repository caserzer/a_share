from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save,interval
from attribution import original
from hashlib import sha256
import subprocess
def main():
    w=read('windows');keys=['scope','arm','h','phase','delay','mul']
    assert not w.duplicated(keys+['entry_idx']).any()
    assert len(w[keys].drop_duplicates())==600
    assert pd.read_csv(DEST/'failures.csv').empty
    p=pd.concat([read('positions'),read('supplementary_positions')],ignore_index=True)
    pnl=p.assign(earned=p.gross-p.fee).groupby(keys+['entry_idx']).earned.sum()
    target=w.set_index(keys+['entry_idx']).net
    err=(pnl-target).abs()
    assert err.notna().all() and err.max()<1e-9
    d=read('daily')
    assert not d.duplicated(keys+['idx']).any()
    wealth=d.groupby(keys).nav.last()
    np.testing.assert_allclose(w.groupby(keys).net.apply(lambda s:np.prod(1+s)),wealth,atol=1e-9)
    ordered=pd.concat([read('orders'),read('supplementary_orders')])
    assert not ordered.duplicated(keys+['idx','instrument']).any()
    gross=ordered.assign(buy=ordered.net_amount.clip(lower=0),sell=-ordered.net_amount.clip(upper=0)).groupby(keys+['idx'])[['buy','sell']].sum()
    np.testing.assert_allclose(gross,d.set_index(keys+['idx']).loc[gross.index,['buy','sell']],atol=1e-10)
    s=read('daily_scores');ref=pd.read_parquet(SEAL).set_index(KEY)
    np.testing.assert_allclose(s.set_index(KEY).loc[ref.index,'E'],ref.E1_78,atol=1e-10,rtol=0)
    orig=outer();ref=pd.read_parquet(OUT/'scores.parquet')
    assert len(ref)==40756 and not ref.duplicated(KEY).any()
    # Audit fold-local signal generation, missing-feature dependence, fill coverage.
    g=orig[KEY+['entry_idx']].assign(n_missing=orig[COLS].isna().sum(axis=1)).merge(ref[KEY+['tree_rank']],on=KEY)
    f=pd.concat([pd.read_parquet(path) for path in (DEST/'folds').glob('*.parquet')])
    g=g.merge(f,on=KEY,validate='1:1')
    g['scope']=np.where(g.signal_date.ge('2025-02-28'),'later','primary')
    cols=['tree_rank','F00','F01','F10']
    for c in cols:g[c]=g.groupby('signal_date')[c].rank(pct=True)
    g['difference']=(g.tree_rank-g.F01).abs()
    g['disagreement_mass']=g.difference
    missing=g.groupby(['scope','n_missing']).agg(rows=('difference','size'),mean_disagreement=('difference','mean'),mass=('difference','sum')).reset_index()
    save('missing_features',missing)
    coverage=original(p).groupby(['scope','arm','entry_idx']).agg(seats=('target','sum'),actual=('weight',lambda x:x.gt(1e-10).sum()),unfilled=('weight',lambda x:0))
    q=original(p);q['unfilled']=q.target&q.weight.lt(1e-10)
    coverage['unfilled']=q.groupby(['scope','arm','entry_idx']).unfilled.sum()
    save('coverage',coverage.reset_index())
    fills=[]
    for e,g in s[s.entry_idx.isin(ref.entry_idx)].groupby('entry_idx'):
        g=g.sort_values(['R','instrument'],ascending=False);k=len(g)//10
        for a,col in [('V','vol20'),('J','mom5')]:fills.append(dict(entry_idx=e,arm=a,missing_in_pool=g.iloc[:2*k][col].isna().sum(),fallback=max(0,k-g.iloc[:2*k][col].count())))
    save('style_fill',fills)
    idx=orig.signal_date.dt.to_period('Q')
    folds=pd.read_csv(OUT/'folds.csv').query('arm=="tree_rank"')
    assert len(folds)==23 and (folds.latest_maturity<folds.first_signal).all()
    inputs=[ROOT.parent/'FOLLOWUP_EXPERIMENT_PLAN.md',OUT/'verification.json',LINEAR/'verification.json',SEAL,ROOT/'candidate.json',
            TRACK/'results/index800.parquet',TRACK/'results/effective800.parquet',
            Path.home()/'.cache/a_share/ep38_three_track/market/wide_features.parquet',
            *PRIVATE.glob('models/expanding/*_E2_seed*.txt'),*(TRACK.parent.glob('rounds/51_*/results/scores.parquet')),
            *(PRIVATE/(n+'.parquet') for n in 'features labels qfq_open qfq_high qfq_low qfq_close volume money turnover_rate daily_members industry market open close opening_trade_status_v2'.split()),PRIVATE/'net_excess_20261116/H00300.CSI.json',
            *(OUT/'models').glob('*/tree_rank.txt'),*(OUT/'models').glob('*/medians.json'),*(LINEAR/'models').glob('*.json')]
    def digest(path):
        h=sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(1<<20),b''):h.update(block)
        return h.hexdigest()
    receipt=dict(parent_git=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),lightgbm=lgb.__version__,folds=len(folds),sealed_rows=len(ref),all_daily_rows=len(s),account_variants=len(wealth),windows=len(w),max_pnl_error=err.max(),positions=len(p),net_orders=len(ordered),raw_inputs={str(path):digest(path) for path in inputs},scripts={path.name:digest(path) for path in ROOT.glob('*.py')},outputs={str(path.relative_to(DEST)):digest(path) for path in DEST.rglob('*') if path.is_file() and path.name!='verification.json'})
    (DEST/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print({k:v for k,v in receipt.items() if not isinstance(v,dict)})
if __name__=='__main__':main()
