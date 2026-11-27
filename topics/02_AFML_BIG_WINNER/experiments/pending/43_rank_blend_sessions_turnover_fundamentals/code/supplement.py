from bl import *
from fund_fit import F,A,N
import json
def add(pool):
    m=book(pool==800)
    f=pd.read_parquet(O/f'diagnostics_{pool}/daily_labels_and_tree.parquet')
    account(m,pack(m,f,f.tree_total),pool,'L','tree_total')
    if pool==800:
        k=frozen(False).groupby('entry_idx').size()//10
        ff=pd.concat(pd.read_parquet(p,columns=KEY+['T','T_mask_trading']) for p in sorted((E/'scale/a4/results/scores_800').glob('*.parquet')))
        for a in ['T','T_mask_trading']:account(m,pack(m,ff,ff[a],k),pool,'B_A4_head',a)
def fi():
    z=frozen(True);px=pd.read_parquet(F/'scoring_panel.parquet',columns=KEY[:2]+N+['industry'])
    rows=[];bysector=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        ref=z[z.signal_date.dt.to_period('Q')==q]
        f=read_features(q,True).merge(ref[KEY+['refit_R']],on=KEY,validate='1:1').rename(columns={'refit_R':'R'}).merge(px,on=KEY[:2],validate='1:1')
        for dt,g in f.groupby('signal_date'):
            for a,n in zip(A,N):
                obs=g[g[n].notna()];r=obs[COL+['R']].rank().corrwith(obs[n].rank())
                rows.append((dt,a,*r))
                rank=obs.groupby('industry')[['R','pos60','dd60',n]].rank()
                mu=rank.groupby(obs.industry).transform('mean');v=rank-mu
                xy=v[['R','pos60','dd60']].mul(v[n],axis=0).groupby(obs.industry).sum()
                xx=(v**2).groupby(obs.industry).sum()
                rr=xy.div(np.sqrt(xx[['R','pos60','dd60']].mul(xx[n],axis=0)))
                for sector,vals in rr.iterrows():bysector.append((dt,sector,a,len(obs[obs.industry==sector]),*vals))
    corr=pd.DataFrame(rows,columns=['date','anchor']+COL+['R'])
    corr.to_parquet(F/'F3_pairwise.parquet',index=False)
    avg=corr.groupby('anchor')[COL+['R']].mean();avg.to_csv(F/'F3_price_corr.csv')
    groups=[]
    for (a,yr),g in corr.groupby(['anchor',corr.date.dt.year]):
        v=g[COL].mean().dropna();groups.append((a,yr,v.abs().idxmax(),v.abs().max(),g.R.mean(),g.pos60.mean(),g.dd60.mean()))
    pd.DataFrame(groups,columns='anchor year most_correlated abs_mean corr_R corr_pos60 corr_dd60'.split()).to_csv(F/'F3_by_year.csv',index=False)
    pd.DataFrame(bysector,columns='date industry anchor rows R pos60 dd60'.split()).to_parquet(F/'F3_industry_corr.parquet',index=False)
if __name__=='__main__':fi() if sys.argv[1]=='F' else add(int(sys.argv[1]))
