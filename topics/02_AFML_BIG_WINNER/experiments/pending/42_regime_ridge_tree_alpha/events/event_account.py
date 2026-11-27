"""CSI800 fixed-lot paired replays and complete-month summaries for EP42 external sources."""
from pathlib import Path
import ctypes as ct
import hashlib, subprocess, sys, tempfile
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
BASE=HERE.parents[1]
EP41=next(BASE.glob('41_*'))
sys.path.insert(0,str(EP41/'p1'))
import engine
import matching

def kernel20(m):
    original=(EP41/'p1/book.cpp').read_text()
    src=original.replace('[10]','[20]').replace('p<10','p<20').replace('%10','%20').replace('i+10','i+20').replace('? .1 :','? .05 :')
    assert src.count('i+20')==2
    file=Path(tempfile.gettempdir())/('ep42-h20-'+hashlib.sha256(src.encode()).hexdigest()[:16])
    lib=file.with_suffix('.so')
    if not lib.exists():
        file.with_suffix('.cpp').write_text(src)
        subprocess.run(['g++','-O2','-std=c++17','-shared','-fPIC',str(file.with_suffix('.cpp')),'-o',str(lib)],check=True)
    fn=ct.CDLL(str(lib)).replay;fn.argtypes=m.kernel.argtypes
    return fn

class Study:
    def __init__(self,style=True):
        self.m=m=engine.load()
        p,_=engine.selections(m); self.pool=p['refit','pool'];self.top=p['refit','head']
        g=pd.read_parquet(engine.OUT800/'scores.parquet',columns=['entry_idx','instrument','refit_R'])
        self.r={}
        for e,d in g.groupby('entry_idx'):
            r=np.full(m.n,np.nan);r[m.symbols.get_indexer(d.instrument)]=d.refit_R;self.r[e]=r
        self.k10=m.kernel;self.k20=kernel20(m)
        if style:
            cap,self.adv,_,self.sector,_=matching.covariates(m)
            self.cap={}
            for e,pool in self.pool.items():
                rank=np.full(m.n,np.nan);rank[pool]=pd.Series(cap[e-1,pool]).rank(pct=True)
                self.cap[e]=rank

    def pair(self,e,events):
        p=self.pool[e];a=np.intersect1d(events,p);b=np.setdiff1d(p,a)
        if not len(a) or not len(b):return np.array([],int),np.array([],int)
        delta=np.abs(self.cap[e][a,None]-self.cap[e][b]);s=self.sector(e-1)
        mask=(s[a,None]==s[b])&(s[a,None]!='未知')&(delta<=.10)
        weight=np.nan_to_num(delta)+1e-10*pd.Series(-self.r[e][b]).rank(pct=True).to_numpy()
        x,y=matching.assign(mask,weight)
        return a[x],b[y]

    def run(self,folder,plans,comparisons,h=10,den=None):
        folder=OUT/folder;folder.mkdir(parents=True,exist_ok=True)
        m=self.m;m.kernel=self.k10 if h==10 else self.k20
        receipts=[]; months=[]; paths=[]; targets=[]
        (folder/'orders').mkdir(exist_ok=True)
        for name,plan in plans.items():
            denominator=(den or {}).get(name)
            packed=engine.pack(m,plan,denominator)
            for e,ids in plan.items():
                if len(ids):
                    targets.extend((name,e,int(j),int(packed[1][e])) for j in ids)
            for stage,interval in enumerate(engine.RANGES,1):
                with tempfile.NamedTemporaryFile() as log:
                    d=engine.simulate(m,packed,interval,orderfile=log.name)
                    if Path(log.name).stat().st_size:
                        o=pd.read_csv(log.name,header=None,names='entry_idx sleeve security_idx target local net fee blocked'.split())
                        o.to_parquet(folder/'orders'/f'{name}_s{stage}.parquet',index=False,compression='zstd')
                if d.index[-1]!=pd.Timestamp(interval[2]):
                    print('unknown mark stops account',name,stage,d.index[-1],flush=True)
                dd=engine.simulate(m,packed,interval,multiplier=2)
                assert dd.index.equals(d.index)
                d['double_nav']=dd.nav
                nav=d[['nav','double_nav']].groupby(d.index.to_period('M')).last().pct_change().iloc[1:-1]
                for t,row in nav.iterrows():months.append((name,stage,str(t),*row.to_numpy()))
                paths.append(d.reset_index().assign(arm=name,stage=stage))
                receipts.append((name,stage,len(d),len(nav),d.nav.iloc[-1]-1, (d.nav/d.nav.cummax().clip(lower=1)-1).min(),d.fee.sum(),d.buy.sum(),d.sell.sum(),d.cash.mean(),d.blocked_budget.sum(),dd.nav.iloc[-1]-1))
        pd.DataFrame(targets,columns=['arm','entry_idx','security_idx','denominator']).to_parquet(folder/'targets.parquet',compression='zstd',index=False)
        md=pd.DataFrame(months,columns='arm stage month net double_net'.split())
        md.to_csv(folder/'months.csv',index=False)
        pd.DataFrame(receipts,columns='arm stage days full_months compounded max_drawdown fee buy sell mean_cash blocked double_fee_compounded'.split()).to_csv(folder/'stages.csv',index=False)
        pd.concat(paths,ignore_index=True).to_parquet(folder/'daily.parquet',compression='zstd',index=False)
        m.kernel=self.k10
        summarize_months(folder,md,comparisons)
        print(folder,h,len(plans),len(comparisons),flush=True)

def summarize_months(folder,md,comparisons):
    rows=[]
    for a,b in comparisons:
        diffs=[];boots=[];rng=np.random.default_rng(4201)
        for stage,g in md.groupby('stage'):
            tbl=g.pivot(index='month',columns='arm',values='net');v=(tbl[a]-tbl[b]).dropna().to_numpy()*1e4
            dbl=g.pivot(index='month',columns='arm',values='double_net')
            i=rng.integers(0,len(v)-2,size=(10000,(len(v)+2)//3))
            bs=v[(i[:,:,None]+np.arange(3)).reshape((10000,-1))[:,:len(v)]].mean(axis=1)
            diffs.append(v);boots.append(bs)
            rows.append((a,b,str(stage),len(v),v.mean(),*np.quantile(bs,[.025,.975]),np.sort(v)[:-3].mean(),((dbl[a]-dbl[b])*1e4).mean()))
        v=np.concatenate(diffs);bs=np.average(boots,axis=0,weights=list(map(len,diffs)))
        rows.append((a,b,'all',len(v),v.mean(),*np.quantile(bs,[.025,.975]),np.concatenate([np.sort(v0)[:-3] for v0 in diffs]).mean(),np.average([r[-1] for r in rows[-len(diffs):]],weights=list(map(len,diffs)))))
    pd.DataFrame(rows,columns='arm comparator stage n bp low high drop_best3 double_fee_bp'.split()).to_csv(folder/'comparisons.csv',index=False)
