"""Read-only frozen sources and replay with independently reconciled EP40 accounting."""
import ctypes as ct
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent
REG = HERE.parent
PENDING = REG.parent
WIDE = next(PENDING.glob("40_*/lightgbm/followup/csi800_69"))
PRIVATE36 = next(PENDING.glob("36_*/private"))
sys.path.insert(0,str(WIDE))
from inputs import LOCAL, OUT800, DEST, ledger, membership
import account

FIELDS = "nav cash fee crossed net_buy net_sell target_budget unavailable_buy_budget blocked_sell_value opening_nav".split()
PERIODS = dict(prefix=("2021-01-11","2023-06-15","2025-03-03"),
               restart=("2023-06-19","2025-03-03","2025-03-03"),
               later=("2025-03-03","2026-10-12","2026-10-12"))
PRIMARY=("2021-01-11","2025-03-03","2025-03-03")

def sha(p):
    return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()

class Study:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ep41-book-')
        scratch=Path(self.temp.name)
        account.PRIVATE=LOCAL
        ledger.accounts.PRIVATE=LOCAL
        ledger.accounts.OUT=scratch
        self.m, self.actions=ledger.setup('flat')
        m=self.m
        self.days=m.days
        self.symbols=m.symbols
        self.members=membership(m.days,m.symbols).to_numpy()
        self.narrow=pd.read_parquet(PRIVATE36/'daily_members.parquet').reindex(index=m.days,columns=m.symbols,fill_value=False).to_numpy(bool)
        def load(name):
            return pd.read_parquet(LOCAL/(name+'.parquet')).reindex(index=m.days,columns=m.symbols)
        self.raw=load('close')
        self.adv=load('money').rolling(20,min_periods=20).mean()
        self.valid_buy=np.ascontiguousarray(m.buy & np.roll(self.members,1,axis=0),np.uint8)
        self.valid_sell=np.ascontiguousarray(m.sell,np.uint8)
        self.marks={}
        op,cl=m.marks['flat']
        self.marks['strict']=tuple(np.ascontiguousarray(a) for a in [op,cl])
        prev=pd.DataFrame(cl).ffill().shift().to_numpy()
        for label,fraction in [('zero',0),('last',1)]:
            self.marks[label]=tuple(np.ascontiguousarray(np.where(np.isfinite(a),a,prev*fraction)) for a in [op,cl])
        self.ranks=pd.read_parquet(OUT800/'scores.parquet').sort_values(['entry_idx','refit_R','instrument'],ascending=[True,False,False])
        self.ks=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx']).groupby('entry_idx').size()//10
        so=scratch/'book.so'
        subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(HERE/'book.cpp'),'-o',str(so)],check=True)
        self.run=ct.CDLL(str(so)).replay
        self.run.argtypes=([ct.c_int]*11 + [ct.c_void_p]*5 + [ct.c_double]+[ct.c_void_p]*3)
        self.days_index=pd.Series(np.arange(len(m.days)),index=m.days)
    def style(self):
        m=self.m
        src=PRIVATE36/'style_caps_20261117'
        snapshots=sorted(src.glob('[0-9]'*8+'.json'))
        stamps=pd.DatetimeIndex([f.stem for f in snapshots])
        caps=[]
        for f in snapshots:
            receipt=json.loads(f.with_suffix('.receipt.json').read_text())
            assert sha(f)==receipt['sha256']
            data=json.loads(f.read_text())['data']
            x=pd.DataFrame(data['items'],columns=data['fields'])
            x.index=x.ts_code.str[-2:]+x.ts_code.str[:6]
            caps.append(x.free_share.reindex(m.symbols).to_numpy(float))
        loc=stamps.searchsorted(m.days,side='left')-1
        arr=np.array(caps)[loc]*self.raw.to_numpy()
        arr[loc<0,:]=np.nan
        self.cap=arr
        self.share_age=(m.days-stamps[loc]).days
        ind=pd.read_parquet(PRIVATE36/'industry.parquet')
        ind['symbol']=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
        codes=pd.Categorical(ind.l1_name)
        sectors=np.full((len(m.days),m.n),-1,dtype=np.int16)
        for row,sector in zip(ind.itertuples(),codes.codes):
            if row.symbol not in m.symbols:continue
            a=m.days.searchsorted(pd.Timestamp(row.in_date))
            b=len(m.days) if pd.isna(row.out_date) else m.days.searchsorted(pd.Timestamp(row.out_date))
            s=m.symbols.get_loc(row.symbol)
            region=sectors[a:b,s]
            both=(region!=-1)&(region!=sector)
            region[~both]=sector
            region[both]=-2
        self.sectors=sectors
    def blank(self,width=82):
        return np.full((len(self.days),width),-1,dtype='int32')
    def replay(self,plans,period,mark='strict',fee=1,keep_orders=False):
        start,stop,end=self.days.get_indexer(period)
        assert start>=0 and stop>=start and end>=stop
        op,cl=self.marks[mark]
        steps=stop-start+1
        d=np.zeros((steps,10))
        o=np.zeros((steps,self.m.n)) if keep_orders else None
        missing=np.full(2,-1,dtype='int32')
        ptr=lambda a:a.ctypes.data
        status=self.run(self.m.n,plans.shape[1],start,stop,end,*self.actions[0],*self.actions[1],
                        ptr(op),ptr(cl),ptr(self.valid_buy),ptr(self.valid_sell),ptr(plans),
                        fee,ptr(d),ptr(o) if o is not None else None,ptr(missing))
        assert status>=-1,(status,period)
        gap=None
        if status>=0:
            steps=status-start
            gap=dict(date=self.days[status],stock=self.symbols[missing[0]],side=['open','end_mark'][missing[1]])
        daily=pd.DataFrame(d[:steps],columns=FIELDS,index=self.days[start:start+steps]).rename_axis('date')
        orders=None
        if keep_orders:
            r,c=np.nonzero(o[:steps])
            orders=pd.DataFrame(dict(date=self.days[r+start],instrument=self.symbols[c],net_order=o[r,c],
                                     opening_nav=d[r,9],adv20_signal=self.adv.to_numpy()[r+start-1,c]))
            np.testing.assert_allclose(daily.fee, (daily.net_buy*.001+daily.net_sell*.002)*fee,atol=1e-12)
        return daily,orders,gap

def pct(a):
    return pd.Series(a).rank(pct=True).to_numpy()

def match(left,right,industry,cap,adv,rank=None):
    if not len(left) or not len(right):return np.array([],int),np.array([],int)
    cap_diff=abs(cap[left,None]-cap[right])
    adv_diff=abs(adv[left,None]-adv[right])
    ok=(industry[left,None]==industry[right])&(industry[left,None]>=0)&(cap_diff<=.1)&(adv_diff<=.1)
    dist=cap_diff+adv_diff
    if rank is not None:
        rd=abs(rank[left,None]-rank[right])
        ok &= rd<=.1
        dist+=rd
    a,b=linear_sum_assignment(np.where(ok,dist,1e4))
    keep=ok[a,b]
    return left[a[keep]],right[b[keep]]

def monthly(d,days):
    r=[]
    for month,g in d.groupby(d.index.to_period('M')):
        calendar=days[days.to_period('M')==month]
        if g.index.equals(calendar):
            r.append((str(month),g.nav.iloc[-1]/g.opening_nav.iloc[0]-1))
    return pd.Series(dict(r),dtype=float)
