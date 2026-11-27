"""Matched-budget domain training (D6) and frozen versus local regime transfer (G7)."""
import argparse
from mixture import *
from matching import covariates


def finish(board, plans, pairs, dest):
    dest.mkdir(exist_ok=True)
    pd.Series(board.m.symbols).to_csv(dest/'symbols.csv',index=False)
    outcomes=run_accounts(board,plans,SEG800,dest,set(plans))
    stats=pd.concat([contrast(outcomes,a+f,b+f) for a,b in pairs for f in ['', '_2fee']])
    stats.to_csv(dest/'comparisons.csv',index=False)
    records=[]
    for arm,pack in plans.items():
        ids,counts=pack[:2]
        for e in np.flatnonzero(counts):
            valid=ids[e]>=0
            records.append((arm,e,ids[e,valid],pack[2][e,valid] if len(pack)==3 else np.full(valid.sum(),1/counts[e])))
    pd.DataFrame(records,columns=['arm','entry_idx','stock_indices','weights']).to_parquet(dest/'targets.parquet',index=False)


def g7(m,all_scores):
    outside=all_scores.loc[~all_scores.in300]
    common=pd.read_parquet(OUT/'states.parquet').set_index('signal_date')
    local_z=pd.read_parquet(OUT/'outside_state.parquet').set_index('signal_date')
    reference=pd.read_csv(OUT/'main/weights_quarterly.csv').set_index('q')
    for kind in ['transfer','refit']:
        dest=OUT/('g7_'+kind)
        dest.mkdir(exist_ok=True)
        board=Board(m,outside.rename(columns={kind+'_R':'R',kind+'_T':'T'}))
        learner=Calibration(board,common,wide=True)
        estimates=pd.DataFrame([learner.fit(q,False) for q in pd.period_range('2021Q1','2026Q3',freq='Q')]).set_index('q')
        estimates.to_csv(dest/'local_quarters.csv')
        pd.DataFrame(learner.history).to_csv(dest/'local_objectives.csv',index=False)
        imported,_=series_for(board,common,reference)
        local,_=series_for(board,common,estimates)
        own_state=common.assign(Z1=local_z.Z1.reindex(common.index))
        changed,_=series_for(board,own_state,reference)
        weights=pd.DataFrame(dict(exported=imported.dynamic,static=imported.static,local=local.dynamic,local_static=local.static,
            outside_state=changed.dynamic,R=imported.R,T=imported['T']))
        weights.assign(Z300=common.Z1,Zoutside=local_z.Z1,stocks=[len(r[1]) for r in board.rows],K=[r[-1] for r in board.rows]).to_parquet(dest/'weights.parquet')
        plans={a:board.pack(weights[a]) for a in weights}
        finish(board,plans,[('exported','static'),('exported','R'),('exported','T'),('local','exported'),('local','local_static'),('outside_state','exported')],dest)
        print('G7',kind,flush=True)


def d6(m,wide):
    from engine import DEST
    dest=OUT/'d6'
    dest.mkdir(exist_ok=True)
    ds=pd.read_parquet(OUT/'domain_scores.parquet').drop(columns='in300')
    df=wide.merge(ds,on=['signal_date','instrument','entry_idx'],how='outer',validate='1:1')
    # Local eligibility can admit a stock removed by pooled feature coverage.
    from engine import PRIVATE
    members=pd.read_parquet(PRIVATE/'daily_members.parquet')
    ii=members.index.get_indexer(df.signal_date);jj=members.columns.get_indexer(df.instrument)
    assert ii.min()>=0
    reconstructed=(jj>=0)&members.to_numpy()[ii,jj]
    ok=df.in300.notna()
    assert np.array_equal(df.loc[ok,'in300'].astype(bool),reconstructed[ok])
    df['in300']=reconstructed
    ks=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx']).groupby('entry_idx').size()//10
    df=df[df.entry_idx.isin(ks.index)].sort_values(['entry_idx','instrument'],ascending=[True,False]).copy()
    df['stock']=m.symbols.get_indexer(df.instrument)
    cap,adv,vol,industry,source=covariates(m)
    arms=['A','B','C','label_only','B_float','C_float','B_top5','C_top5','B_top10','C_top10']
    rows={a:{} for a in arms};shares={a:{} for a in arms};audit=[];styles=[]
    for e,g in df.groupby('entry_idx'):
        k=int(ks[e]);i=e-1
        groups=[g[g.in300],g[~g.in300]]
        covs=[cap[i,x[x.refit_R.notna()].stock.to_numpy()] for x in groups]
        seen=[int(np.isfinite(c).sum()) for c in covs]
        total=[len(c) for c in covs]
        # A population share with undisclosed capital has no exact denominator.
        float_ok=all(n and n==t for n,t in zip(seen,total))
        ratio=np.nansum(covs[0])/sum(np.nansum(c) for c in covs) if float_ok else np.nan
        audit.append((e,g.signal_date.iloc[0],k,*total,*seen,ratio,*(x.domain_R.notna().sum() for x in groups)))
        for arm in arms:
            col='domain_R' if arm.startswith('C') else 'label_only' if arm=='label_only' else 'refit_R'
            if arm=='A':
                selected=g.dropna(subset=[col]).sort_values(col,ascending=False,kind='stable').stock.to_numpy()[:k]
                weight=np.full(len(selected),1/k)
            else:
                seats=[k//2,k-k//2]
                for tag,p in [('top5',20),('top10',10)]:
                    if arm.endswith(tag):seats=[int(x[col].count()//p) for x in groups]
                split=ratio if arm.endswith('float') else .5
                selected=[];weight=[]
                for x,n,amount in zip(groups,seats,[split,1-split]):
                    ids=x.dropna(subset=[col]).sort_values(col,ascending=False,kind='stable').stock.to_numpy()[:n]
                    selected.extend(ids);weight.extend(np.full(len(ids),amount/n if np.isfinite(amount) and n else 0))
                selected=np.asarray(selected,int);weight=np.array(weight)
            rows[arm][e]=selected;shares[arm][e]=weight
            si=industry(i)[selected]
            for label in np.unique(si):styles.append((e,arm,label,weight[si==label].sum()))
    board=Board(m,wide[wide.entry_idx.isin(ks.index)].rename(columns={'refit_R':'R','refit_T':'T'}))
    plans={}
    for arm in arms:
        ids,den=original.pack(m,rows[arm]);weights=np.zeros(ids.shape,dtype=float)
        for e,w in shares[arm].items():weights[e,:len(w)]=w
        plans[arm]=(ids,den,weights)
    pd.DataFrame(audit,columns=['entry_idx','signal_date','K','inside','outside','cap_inside_seen','cap_outside_seen','inside_share','local_inside','local_outside']).to_csv(dest/'coverage.csv',index=False)
    pd.DataFrame(styles,columns=['entry_idx','arm','industry','target_weight']).to_parquet(dest/'industry_weights.parquet',index=False)
    finish(board,plans,[('B','A'),('C','B'),('C','A'),('label_only','B'),('C_float','B_float'),('B_float','B'),('C_top5','B_top5'),('C_top10','B_top10'),('C_top5','C'),('C_top10','C')],dest)
    check_original(dest)


def check_original(dest):
    old=pd.read_parquet(EP41/'p1/results/daily.parquet')
    ref=old.query('model=="refit" and bucket=="head" and kind=="strict" and phase==-1')
    new=pd.read_parquet(dest/'daily.parquet').query('arm=="A"')
    results=[]
    for s,h in new.groupby('segment'):
        o=ref[ref.segment.eq(s)].set_index('date')
        h=h.set_index('date')
        assert len(o) and h.index.equals(o.index),(s,old.kind.unique())
        err=(h[FIELDS]-o[FIELDS]).abs().max().max();assert err<1e-9,err
        results.append((s,len(o),err))
    pd.DataFrame(results,columns=['segment','rows','max_daily_account_error']).to_csv(dest/'baseline_parity.csv',index=False)
    print('D6',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('group',choices=['g7','d6']);args=p.parse_args()
    m=market(True);x=pd.read_parquet(OUT/'wide_scores.parquet')
    (g7 if args.group=='g7' else d6)(m,x)

