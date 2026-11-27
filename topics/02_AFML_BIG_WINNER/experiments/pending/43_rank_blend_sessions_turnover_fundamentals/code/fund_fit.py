from fund_panel import *
from accounts43 import account,book,pack
from scipy.stats import rankdata
N=['n_'+a for a in A];H=['has_'+a for a in A];V=['raw_'+a for a in A];D=['res_'+a for a in A]
def residuals(g,need_corr):
    inp=g[COL].to_numpy(float);cap=g.capital.to_numpy()
    observed=np.isfinite(inp).any(axis=0);x=inp[:,observed]
    x=np.where(np.isfinite(x),x,np.nanmedian(x,axis=0));x=np.column_stack([x,np.log(np.where(cap>0,cap,np.nan))])
    valid=np.isfinite(x).all(axis=1);res=np.full((len(g),6),np.nan)
    y=g[N].to_numpy();cs=[]
    for c in range(6):
        mask=np.isfinite(y[:,c])&valid
        if mask.sum()<3:continue
        a=x[mask];a-=a.mean(axis=0);sd=a.std(axis=0);a=a[:,sd>1e-12]/sd[sd>1e-12]
        a=np.column_stack([np.ones(len(a)),a])
        b,_,r,_=np.linalg.lstsq(a,y[mask,c],rcond=1e-10)
        if len(a)>r:res[mask,c]=y[mask,c]-a@b
    if need_corr:
        for c in range(6):
            obs=g[g[N[c]].notna()];use=obs[COL+['R']].rank().corrwith(obs[N[c]].rank())
            cs.append(use.to_numpy())
    return res,cs
def enhance(f,panel,ref=None):
    keys=KEY[:2]
    cols=keys+['capital','industry']+N+V
    f=f.merge(panel[cols],on=keys,how='left',validate='1:1').reset_index(drop=True)
    if ref is not None:f=f.merge(ref[keys+['refit_R']].rename(columns={'refit_R':'R'}),on=keys,validate='1:1').reset_index(drop=True)
    rr=np.full((len(f),6),np.nan);cs=[]
    for date,ix in f.groupby('signal_date').indices.items():
        rr[ix],v=residuals(f.iloc[ix],ref is not None)
        if v:cs.extend([(date,A[j],*s) for j,s in enumerate(v)])
    f[D]=rr
    f[H]=f[N].isna().astype(float).to_numpy()
    f['support']=f[N].notna().all(axis=1)
    for cols in [D,V,N]:f[cols]=f[cols].fillna(0)
    return f,cs
def run():
    import warnings
    warnings.filterwarnings('ignore',category=RuntimeWarning)
    panel=pd.read_parquet(F/'scoring_panel.parquet')
    raw=pd.read_parquet(LOCAL/'wide_features.parquet',columns=KEY[:2]+COL+['weekly_ok'])
    core=weekly(True);raw=raw[raw.weekly_ok & raw.signal_date.isin(core.signal_date.unique())]
    ext,_=enhance(raw,pd.read_parquet(F/'training_panel.parquet'))
    f=core.merge(ext[KEY[:2]+N+V+D+H],on=KEY[:2],validate='1:1')
    days=pd.read_parquet(LOCAL/'qfq_open.parquet',columns=[]).index;refs=frozen(True);rows=[];correls=[]
    groups={'neutral':N,'raw':V,'residual':D,'missing':H,'value':N[:2],'quality':N[2:],**{a:[c] for a,c in zip(A,N)}}
    for q in pd.period_range('2021Q1','2026Q3',freq='Q'):
        dest=F/('scores_'+str(q)+'.parquet')
        if dest.exists():continue
        ref=refs[refs.signal_date.dt.to_period('Q')==q]
        x,c=enhance(read_features(q,True).merge(ref[KEY],on=KEY,validate='1:1'),panel,ref)
        tr=f[f.exit_idx<days.searchsorted(q.start_time)]
        out=x[KEY+['R','support','industry','pos60','dd60']+N+H].copy()
        # The full model's preprocessor is column-wise, allowing exact submodel fits from shared sufficient statistics.
        cols=COL+N+V+D+H
        a=tr[cols].to_numpy(float);med=np.nan_to_num(np.nanmedian(a,axis=0));a=np.where(np.isnan(a),med,a);mean=a.mean(axis=0);sd=a.std(axis=0);sd[sd<1e-12]=1.
        a=(a-mean)/sd;z=x[cols].to_numpy(float);z=(np.where(np.isnan(z),med,z)-mean)/sd
        y=tr.target_rank.to_numpy();yc=y-y.mean();gram=a.T@a+10*np.eye(len(cols));cross=a.T@yc
        for arm,extra in {'baseline':[],**groups}.items():
            use=[cols.index(c) for c in COL+extra];coef=np.linalg.solve(gram[np.ix_(use,use)],cross[use]);out[arm]=z[:,use]@coef+y.mean()
        err=np.max(np.abs(out.baseline-out.R));assert err<1e-8,(q,err)
        out.to_parquet(dest,index=False)
        pd.DataFrame(c,columns=['date','anchor']+COL+['R']).to_parquet(F/f'corr_{q}.parquet',index=False)
        print(q,len(tr),len(out),err,flush=True)
def gates(g,col,rule):
    # Independent, deterministic no-replacement pools; one original seat per successful replacement.
    base=g.sort_values(['R','instrument'],ascending=[False,False]).copy();n=len(base);k=n//10
    pc=base[col].rank(pct=True) if col!='both' else (base.pos60.rank(pct=True)+base.dd60.rank(pct=True))/2
    low=pc.rank(pct=True)<=.2
    qa=base[N[2:]].mask(base[H[2:]].to_numpy().astype(bool)).mean(axis=1).where(base[H[2:]].sum(axis=1)<=1)
    bad=qa.rank(pct=True)<=.2;head=base.iloc[:k]
    selected=list(head.index);repl=[]
    for ix in head.index[::-1]:
        if not low[ix] or (rule!='price' and not bad[ix]):continue
        sec=base.at[ix,'industry']
        if sec in ('未知','冲突'):continue
        allowed=low&(base.industry==sec)&~base.index.isin(head.index)&~base.index.isin(repl)
        if rule=='quality':allowed&=qa.notna()&~bad
        if rule=='random':
            # Match the quality gate's exits and industry counts, without filtering the replacement by quality.
            allowed&=qa.notna()
        choices=base[allowed]
        if choices.empty:continue
        if rule=='random':
            pick=min(choices.index,key=lambda j:hashlib.sha256((str(base.signal_date.iloc[0].date())+base.at[j,'instrument']).encode()).digest())
        else:pick=choices.index[0]
        selected.remove(ix);selected.append(pick);repl.append(pick)
    return selected,len(repl)
def accounts():
    ff=pd.concat(pd.read_parquet(f) for f in sorted(F.glob('scores_*.parquet'))).reset_index(drop=True)
    m=book(True)
    for arm in ['neutral','raw','residual','missing','value','quality']+A:
        account(m,pack(m,ff,ff[arm]),800,'Fproxy',arm,trace=arm in ['neutral','residual'])
    sub=ff[ff.support]
    for arm in ['R','neutral']:account(m,pack(m,sub,sub[arm]),800,'Fcommon',arm)
    # Frozen unsupported original seats; remaining budget can only select supported names.
    score=pd.Series(-1e6,index=ff.index,dtype=float)
    rr=[];gg={x:score.copy() for x in ['gate','hash','price','pos','dd']}
    for date,g in ff.groupby('signal_date'):
        k=len(g)//10;hh=g.sort_values(['R','instrument'],ascending=[False,False]).head(k)
        lock=hh.index[~hh.support];score.loc[lock]=1e6+hh.loc[lock,'R'];score.loc[g.index[g.support]]=g.loc[g.support,'neutral']
        for name,col,rule in [('gate','both','quality'),('hash','both','random'),('price','both','price'),('pos','pos60','quality'),('dd','dd60','quality')]:
            if name=='hash':
                original=list(hh.index);exits=[j for j in original if j not in quality_ids]
                low=((g.pos60.rank(pct=True)+g.dd60.rank(pct=True))/2).rank(pct=True)<=.2
                ids=original.copy()
                for j in exits:
                    choices=g[low & (g.industry==g.at[j,'industry']) & ~g.index.isin(original) & ~g.index.isin(ids) & (g[H[2:]].sum(axis=1)<=1)]
                    best=min(choices.index,key=lambda ix:hashlib.sha256((str(date.date())+g.at[ix,'instrument']).encode()).digest())
                    ids.remove(j);ids.append(best)
                n=len(exits)
            else:ids,n=gates(g,col,rule)
            if name=='gate':quality_ids=set(ids)
            gg[name].loc[ids]=1+g.loc[ids,'R'];rr.append((date,name,n,k))
    account(m,pack(m,ff,score),800,'Fproxy','lock')
    for name,s in gg.items():account(m,pack(m,ff,s),800,'Fgate',name,trace=True)
    pd.DataFrame(rr,columns=['date','arm','replacements','K']).to_csv(F/'gate_changes.csv',index=False)
if __name__=='__main__':run() if sys.argv[1]=='fit' else accounts()
