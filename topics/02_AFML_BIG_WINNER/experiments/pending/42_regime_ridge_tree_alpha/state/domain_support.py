"""D6 matched-stock sensitivity with both models conditioned on identical scored rows."""
from domains import *
def main():
    m=market(True)
    narrow=pd.read_csv(OUT/'d6/coverage.csv').set_index('entry_idx')
    all_scores=pd.read_parquet(OUT/'wide_scores.parquet',columns=['entry_idx','instrument','signal_date','in300','refit_R'])
    local=pd.read_parquet(OUT/'domain_scores.parquet',columns=['entry_idx','instrument','domain_R']).dropna(subset=['domain_R'])
    scored=all_scores.merge(local,on=['entry_idx','instrument'],how='inner',validate='1:1').sort_values(['entry_idx','instrument'],ascending=[True,False])
    rows={'B_common':{},'C_common':{}};shares={};audit=[]
    for e,g in scored.groupby('entry_idx'):
        k=int(narrow.at[e,'K']);splits=[k//2,k-k//2];weights=[]
        for n in splits:weights.extend([.5/n]*n)
        shares[e]=np.array(weights)
        for arm,col in [('B_common','refit_R'),('C_common','domain_R')]:
            ids=[]
            for isin,n in zip([True,False],splits):
                x=g[g.in300==isin]
                assert len(x)>=n
                ids.extend(m.symbols.get_indexer(x.nlargest(n,col,keep='first').instrument))
            rows[arm][e]=ids
        audit.append((e,narrow.at[e,'inside']-(g.in300).sum(),narrow.at[e,'outside']-(~g.in300).sum()))
    plans={}
    for a,v in rows.items():
        ids,den=original.pack(m,v);w=np.zeros(ids.shape)
        for e,d in shares.items():w[e,:len(d)]=d
        plans[a]=(ids,den,w)
    dest=OUT/'d6_common';dest.mkdir(exist_ok=True)
    board=Board(m,scored.rename(columns={'refit_R':'R','domain_R':'T'}))
    finish(board,plans,[('C_common','B_common')],dest)
    pd.DataFrame(audit,columns=['entry_idx','inside_removed','outside_removed']).to_csv(dest/'coverage.csv',index=False)
if __name__=='__main__':main()

