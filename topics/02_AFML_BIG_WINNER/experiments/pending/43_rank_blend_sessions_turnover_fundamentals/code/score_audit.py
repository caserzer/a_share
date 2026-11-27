from accounts43 import *
def labels_daily(x,wide):
    raw=LOCAL if wide else PRIVATE
    oi=pd.read_parquet(raw/'qfq_open.parquet');ci_=pd.read_parquet(raw/'qfq_close.parquet')
    a=oi.to_numpy();c=ci_.to_numpy();i=x.entry_idx.to_numpy();j=oi.columns.get_indexer(x.instrument)
    good=i+10<len(a);ii=i[good];jj=j[good];I=np.zeros(good.sum());V=I.copy()
    for k in range(10):I+=np.log(c[ii+k,jj]/a[ii+k,jj]);V+=np.log(a[ii+k+1,jj]/c[ii+k,jj])
    for name,val in [('I',I),('V',V),('IV',np.log(a[ii+10,jj]/a[ii,jj]))]:
        x[name]=np.nan;x.loc[good,name]=val
    ok=np.isfinite(x[['I','V','IV']]).all(axis=1)
    x.loc[~ok,['I','V','IV']]=np.nan
    return x
def run(pool):
    wide=pool==800;m=book(wide);out=O/f'diagnostics_{pool}';out.mkdir(exist_ok=True)
    tr,_=market_labels(weekly(wide),wide)
    cols=[];pred=[]
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        base=pd.read_parquet(O/'models'/f'{q}.parquet',filters=[('pool','=',pool)])
        x=base.merge(read_features(q,wide),on=KEY,validate='1:1')
        tt=tr[(tr.mature<q.start_time)&tr.ytotal.notna()]
        for label in ['total','intra','over']:
            model=ci.ridge(tt,COL,'y'+label)
            cols.extend((str(q),label,col,b) for col,b in zip(COL,model['coef']))
        med=tt[COL].median().fillna(0);tree=ci.lgb.train(dict(ci.PARAMS,objective='regression',num_threads=2),ci.lgb.Dataset(tt[COL].fillna(med),label=tt.ytotal),num_boost_round=80)
        base['tree_total']=tree.predict(x[COL].fillna(med),num_threads=2);pred.append(base)
    x=labels_daily(pd.concat(pred,ignore_index=True),wide)
    pd.DataFrame(cols,columns='quarter leg feature standardized_coef'.split()).to_csv(out/'L2_coefficients.csv',index=False)
    x[KEY+['tree_total','I','V','IV']].to_parquet(out/'daily_labels_and_tree.parquet',index=False)
    account(m,pack(m,x,x.tree_total),pool,'L','tree_total')
    x['eq']=x.intra+x.over;x['eq_tree']=x.intra+x.treeover
    rows=[];bins=[];corr=[]
    for date,g in x.groupby('signal_date'):
        labels=['I','V','IV'];names='R T69 T69d T60 T60d intra over total treeover tree_total eq eq_tree'.split()
        n=len(g);k=n//10;actual=g[labels];base=g.R.nlargest(k).index
        ranks=g[names].rank(ascending=False,method='average')
        for name in names:
            y=g[name];head=y.nlargest(k).index;tail=y.nsmallest(k).index
            boundary=ranks[name].between(max(1,k-5),k+5)
            ic=actual.rank().corrwith(y.rank());bic=actual.loc[boundary,'IV'].corr(y[boundary],method='spearman')
            rows.append((date,name,n,len(g.IV.dropna()),len(set(base)&set(head))/k,*ic,bic,*actual.loc[head].mean(),*actual.loc[tail].mean()))
        for name in ['over','treeover']:
            bucket=1+np.minimum(4,np.floor(5*(ranks[name]-1)/n)).astype(int)
            for b,h in g.groupby(bucket):bins.append((date,name,b,len(h),h.I.mean(),h.V.mean(),h.IV.mean()))
        corr.append((date,g.intra.corr(g.over),g.total.corr(g['eq']),g.over.corr(g.treeover)))
    pd.DataFrame(rows,columns='date arm names valid topK_overlap_R IC_I IC_V IC_IV boundary_IC_IV top_I top_V top_IV bottom_I bottom_V bottom_IV'.split()).to_parquet(out/'B1_L2_daily.parquet',index=False)
    pd.DataFrame(bins,columns='date score quintile names I V total'.split()).to_csv(out/'L4_quintiles.csv',index=False)
    pd.DataFrame(corr,columns='date intra_over total_eq over_treeover'.split()).to_csv(out/'L2_pred_corr.csv',index=False)
if __name__=='__main__':run(int(sys.argv[1]))
