from score_audit import *
def main(pool):
    wide=pool==800
    orig=pd.read_parquet(O/f'diagnostics_{pool}/daily_labels_and_tree.parquet')
    f=pd.concat(pd.read_parquet(p,filters=[('pool','=',pool)]) for p in sorted((O/'models').glob('*.parquet')))
    f=orig.merge(f,on=KEY,validate='1:1')
    mask=pd.concat(pd.read_parquet(p,columns=KEY+['T','T_mask_trading']) for p in (E/f'scale/a4/results/scores_{pool}').glob('*.parquet'))
    f=f.merge(mask,on=KEY,how='left',validate='1:1')
    f=f.sort_values(['signal_date','instrument'],ascending=[True,False]);f['eq']=f.intra+f.over;f['eq_tree']=f.intra+f.treeover
    arms='R T69 T69d T60 T60d T T_mask_trading intra over total treeover tree_total eq eq_tree'.split()
    names=['I','V','IV'];matches=[];rows=[]
    for date,g in f.groupby('signal_date'):
        k=len(g)//10;rank=g[arms].rank(ascending=False,method='first');returns=g[names]
        for a in arms:
            if not rank[a].notna().any():continue
            head=rank[a]<=k;tail=rank[a]>len(g)-k
            ic=returns.corrwith(g[a],method='spearman')
            boundary=rank[a].between(k-5,k+5);bic=returns.IV[boundary].corr(g.loc[boundary,a],method='spearman')
            rows.append((date,a,len(g),g.IV.notna().sum(),(head&(rank.R<=k)).sum()/k,*ic,bic,*returns[head].mean(),*returns[tail].mean()))
            for b in ['R','T69','T69d','T60','T60d','T','T_mask_trading','total','eq']:
                if rank[b].notna().any():matches.append((date,a,b,k,int((head&(rank[b]<=k)).sum())))
    out=O/f'diagnostics_{pool}'
    pd.DataFrame(matches,columns='date arm base K overlap'.split()).to_parquet(out/'topK_overlap.parquet',index=False)
    pd.DataFrame(rows,columns='date arm names valid topK_overlap_R IC_I IC_V IC_IV boundary_IC_IV top_I top_V top_IV bottom_I bottom_V bottom_IV'.split()).to_parquet(out/'B1_L2_daily.parquet',index=False)
if __name__=='__main__':main(int(sys.argv[1]))
