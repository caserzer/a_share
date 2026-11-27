from pathlib import Path
import ctypes as ct
import hashlib
import subprocess
import sys
import tempfile
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
OLD = next(BASE.glob('40_*')) / 'lightgbm/followup/csi800_69'
sys.path.insert(0, str(OLD))
from inputs import LOCAL, OUT800, DEST, PRIVATE, STORE, ledger, membership
import account

RESULT = HERE/'results'
COLS = 'nav cash fee crossed buy sell planned blocked_budget preopen gross_pnl hhi max_weight positions'.split()
RANGES = [('2021-01-11','2025-03-03','2023-06-15'),('2023-06-19','2025-03-03','2025-03-03'),('2025-03-03','2026-10-12','2026-10-12')]

def load(csi800=True):
    source=HERE/'book.cpp'
    lib=Path(tempfile.gettempdir())/('ep41-'+hashlib.sha256(source.read_bytes()).hexdigest()[:16]+'.so')
    if not lib.exists():
        subprocess.run(['g++','-O2','-std=c++17','-shared','-fPIC',str(source),'-o',str(lib)],check=True)
    fn=ct.CDLL(str(lib)).replay
    fn.argtypes=[ct.c_int]*5+[ct.c_void_p]*7+[ct.c_int]*3+[ct.c_double]*2+[ct.c_void_p,ct.c_char_p]
    account.PRIVATE=LOCAL if csi800 else PRIVATE; ledger.accounts.PRIVATE=account.PRIVATE
    with tempfile.TemporaryDirectory() as tmp:
        ledger.accounts.OUT=Path(tmp)
        market,actions=ledger.setup('flat')
    if csi800:market.members=membership(market.days,market.symbols).to_numpy()
    op,cl=market.marks['flat']
    market.planes=[np.ascontiguousarray(a) for a in (op,cl,market.buy & np.roll(market.members,1,axis=0),market.sell,np.asarray(actions,dtype=np.int32))]
    market.kernel=fn
    return market

def selections(m):
    scores=pd.read_parquet(OUT800/'scores.parquet',columns=['signal_date','instrument','entry_idx','refit_R','transfer_R'])
    assert not scores.duplicated(['signal_date','instrument']).any()
    k300=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx']).groupby('entry_idx').size()//10
    plans={};grades={}
    for (e,dt),g in scores.groupby(['entry_idx','signal_date']):
        assert dt==m.days[e-1]
        ids=m.symbols.get_indexer(g.instrument)
        assert min(ids)>=0 and m.members[e-1,ids].all()
        k,l=int(k300.at[e]),len(g)//10
        for model in ['transfer','refit']:
            rank=ids[np.lexsort((ids,g[model+'_R']))[::-1]]
            for name,selected in [('head',rank[:k]),('runner',rank[k:l]),('decile',rank[:l])]:
                plans.setdefault((model,name),{})[e]=selected
            if model=='refit':
                plans.setdefault(('refit','pool'),{})[e]=ids
                cat=np.zeros(m.n,np.int8)
                cat[rank]=1;cat[rank[k:l]]=2;cat[rank[:k]]=3
                grades[e]=cat
    return plans,grades

def pack(m,plan,denominator=None):
    width=max(1,max(map(len,plan.values())))
    ids=np.full((len(m.days),width),-1,dtype=np.int32)
    den=np.zeros(len(m.days),np.int32)
    for i,g in plan.items():
        ids[i,:len(g)]=g
        den[i]=len(g) if denominator is None else denominator[i]
    return ids,den

def simulate(m,packed,interval,phase=-1,netting=True,multiplier=1.,orderfile=None):
    start,end,stop=m.days.get_indexer(pd.to_datetime(interval))
    tar,den=packed
    out=np.full((stop-start+1,len(COLS)),np.nan)
    arrays=[tar,den,*m.planes]
    cut=m.kernel(m.n,start,end,stop,tar.shape[1],*[a.ctypes.data for a in arrays],
                 len(m.planes[-1]),phase,netting,multiplier*.001,multiplier*.002,
                 out.ctypes.data,str(orderfile or '').encode())
    assert cut>=start
    return pd.DataFrame(out[:cut-start],columns=COLS,index=m.days[start:cut].rename('date'))
