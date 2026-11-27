"""Shared account, paired-month and score-ranking routines for the EP42 state experiments."""
from pathlib import Path
import ctypes as ct
import hashlib
import tempfile
import subprocess
import sys
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
EP42=HERE.parent
EP41=next(EP42.parent.glob('41_*'))
OUT=HERE/'results'
sys.path.insert(0,str(EP41/'p1'))
import engine as original

SEG300=[('2021-01-11','2025-03-03','2025-03-03'),('2025-03-03','2026-10-12','2026-10-12')]
SEG800=original.RANGES
FIELDS=original.COLS
TRACE=np.dtype([(f,'i4') for f in ['day','phase','stock']]+[(f,'f8') for f in ['old_units','new_units','overnight','intraday','fee','target','flow']])

def market(wide=False):
    m=original.load(csi800=wide)
    source=HERE/'weighted.cpp'
    lib=Path(tempfile.gettempdir())/('ep42-'+hashlib.sha256(source.read_bytes()).hexdigest()[:16]+'.so')
    if not lib.exists():
        with tempfile.NamedTemporaryFile(dir=lib.parent,suffix='.so') as temp:
            subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(source),'-o',temp.name],check=True)
            import shutil,os
            stage=lib.with_suffix('.'+str(os.getpid()))
            shutil.copyfile(temp.name,stage)
            stage.replace(lib)
    m.weighted=ct.CDLL(str(lib)).replay
    m.weighted.argtypes=(
        [ct.c_int]*5+[ct.c_void_p]*7+[ct.c_int]*3+[ct.c_double]*2+[ct.c_void_p,ct.c_char_p,ct.c_void_p,ct.c_char_p])
    return m

def replay(m,packed,span,fee=1,phase=-1,trace=None):
    start,end,stop=[m.days.get_loc(pd.Timestamp(t)) if not isinstance(t,(int,np.integer)) else int(t) for t in span]
    ids,den=packed[:2];w=packed[2] if len(packed)>2 else None
    values=np.full((stop-start+1,len(FIELDS)),np.nan)
    cut=m.weighted(m.n,start,end,stop,ids.shape[1],*[a.ctypes.data for a in (ids,den,*m.planes)],
                   len(m.planes[-1]),phase,1,fee*.001,fee*.002,values.ctypes.data,b'',None if w is None else w.ctypes.data,
                   b'' if trace is None else str(trace).encode())
    if cut<start: raise ArithmeticError(('negative_cash',start,cut))
    return pd.DataFrame(values[:cut-start],index=m.days[start:cut].rename('date'),columns=FIELDS)

def monthly(frame,days):
    ends=pd.Series(days,index=days).groupby(days.to_period('M')).last()
    out=[]
    for dt,g in frame.groupby(frame.index.to_period('M')):
        if dt-1 not in ends or ends.at[dt-1] not in frame.index or g.index[-1]!=ends.at[dt]:continue
        initial=frame.at[ends.at[dt-1],'nav']
        net=g.nav.iloc[-1]/initial-1
        fees=g.fee.sum()/initial
        out.append((str(dt),net,fees,net+fees,(g.buy+g.sell).sum()/initial,g.crossed.sum()/initial))
    return pd.DataFrame(out,columns=['month','net','fee','gross','turnover','crossed']).set_index('month')

class Board:
    def __init__(self,m,frame,k_override=None):
        self.m=m
        self.rows=[]
        frame=frame.sort_values(['entry_idx','instrument'],ascending=[True,False]).copy()
        for name in ['R','T']:
            frame[name+'_rank']=frame.groupby('entry_idx')[name].rank().div(frame.groupby('entry_idx')[name].transform('count')+1)
        frame['T_rank']=frame.T_rank.fillna(frame.R_rank)
        for e,g in frame.groupby('entry_idx',sort=False):
            assert (g.signal_date==m.days[e-1]).all()
            ids=m.symbols.get_indexer(g.instrument)
            assert ids.min()>=0 and len(ids)==len(np.unique(ids))
            k=int(k_override[e]) if k_override is not None else len(g)//10
            self.rows.append((int(e),ids,g.R_rank.to_numpy(),g.T_rank.to_numpy(),k))
        self.entries=np.array([r[0] for r in self.rows])
        self.dates=m.days[self.entries-1]
        self.ks=np.zeros(len(m.days),dtype='int32')
        self.ks[self.entries]=[r[-1] for r in self.rows]
        self.width=int(self.ks.max())

    def pack(self,weights,budget=False,truncate=False):
        size=self.width*(2 if budget and not truncate else 1)
        ids=np.full((len(self.m.days),size),-1,np.int32)
        shares=np.zeros(ids.shape) if budget else None
        weights=np.broadcast_to(np.array(weights,dtype=float),(len(self.rows),))
        for w,(e,stocks,r,t,k) in zip(weights,self.rows):
            if not budget:
                rank=np.argsort(-((1-w)*r+w*t),kind='stable')[:k]
                ids[e,:k]=stocks[rank]
            else:
                ar=np.argsort(-r,kind='stable')[:k]
                at=np.argsort(-t,kind='stable')[:k]
                allocation=np.zeros(len(r))
                allocation[ar]+=(1-w)/k
                allocation[at]+=w/k
                picks=np.flatnonzero(allocation>0)
                if truncate:
                    picks=picks[np.argsort(-allocation[picks],kind='stable')[:k]]
                ids[e,:len(picks)]=stocks[picks]
                shares[e,:len(picks)]=allocation[picks]/allocation[picks].sum()
        return (ids,self.ks,shares) if budget else (ids,self.ks)

def intervals(parts):
    values=[np.asarray(x,float) for x in parts if len(x)]
    if not values:return (float('nan'),)*3
    rng=np.random.default_rng(4201)
    samples=np.zeros(10000)
    for x in values:
        n=len(x); block=min(3,n)
        start=rng.integers(n-block+1,size=(len(samples),(n+block-1)//block))
        draw=x[(start[:,:,None]+np.arange(block)).reshape(len(samples),-1)[:,:n]]
        samples+=draw.sum(axis=1)
    return (np.concatenate(values).mean(),*np.percentile(samples/sum(map(len,values)),[2.5,97.5]))

def contrast(months,arm,base):
    m=months[months.arm.isin([arm,base])].pivot(index=['segment','month'],columns='arm',values=['net','gross','fee','turnover'])
    d=(m.xs(arm,axis=1,level=1)-m.xs(base,axis=1,level=1)).dropna()
    parts=[];rows=[]
    for seg,g in d.groupby(level=0):
        vals=g.net.to_numpy()*10000
        parts.append(vals)
        mean,lo,hi=intervals([vals])
        rows.append(dict(segment=str(seg),months=len(vals),net_bp=mean,lo=lo,hi=hi,gross_bp=g.gross.mean()*1e4,fee_bp=g.fee.mean()*1e4,
                         drop_best3=np.sort(vals)[:-3].mean() if len(vals)>3 else np.nan))
    mean,lo,hi=intervals(parts)
    rows.append(dict(segment='all',months=len(d),net_bp=mean,lo=lo,hi=hi,gross_bp=d.gross.mean()*1e4,fee_bp=d.fee.mean()*1e4,
                     drop_best3=np.mean(np.concatenate([np.sort(v)[:-3] for v in parts if len(v)>3])) if any(len(v)>3 for v in parts) else np.nan))
    return pd.DataFrame(rows).assign(arm=arm,base=base)

def read_trace(binary):
    return pd.DataFrame(np.fromfile(binary,dtype=TRACE))

