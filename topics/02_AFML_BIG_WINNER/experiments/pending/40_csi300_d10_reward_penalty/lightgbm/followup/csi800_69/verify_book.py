from inputs import *
from stagger import simulate as archived_simulate
import account

def main():
    account.PRIVATE=LOCAL;ledger.accounts.PRIVATE=LOCAL;ledger.accounts.OUT=OUT800
    m,actions=ledger.setup('flat')
    m.members=membership(m.days,m.symbols).to_numpy()
    target=pd.read_parquet(OUT800/'targets.parquet')
    strict=pd.read_parquet(OUT800/'strict_daily.parquet').query('scope=="later" and path=="original"')
    i,j=m.days.get_indexer(['2025-03-03','2026-10-12'])
    checked=[]
    for (size,mode),g in target.groupby(['size','mode']):
        for a,c in [('R','ridge_target'),('swap','swap_target')]:
            selected=g[g[c] & g.entry_idx.between(i,j-10)]
            assert not selected.duplicated(['entry_idx','instrument']).any()
            plan={e:m.symbols.get_indexer(f.instrument) for e,f in selected.groupby('entry_idx')}
            ref=archived_simulate(m,actions,plan,i,j,True).set_index('date')
            z=strict.query('mode==@mode and size==@size and arm==@a').set_index('date')
            delta=(ref.nav-z.nav).abs().max()
            np.testing.assert_allclose(ref[['nav','cash','fee','crossed']],z.loc[ref.index,['nav','cash','fee','crossed']],rtol=0,atol=1e-10)
            checked.append(dict(size=size,mode=mode,arm=a,days=len(z),max_nav_error=delta))
    pd.DataFrame(checked).to_csv(OUT800/'book_parity.csv',index=False)
if __name__=='__main__':main()
