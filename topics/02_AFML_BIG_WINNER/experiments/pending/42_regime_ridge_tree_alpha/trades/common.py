"""Rebuild common-origin H10 trials with the reconciled broker code and real historical states."""
from pathlib import Path
import ctypes as ct
import hashlib, subprocess, tempfile
import numpy as np, pandas as pd
import replay as rp
from sources import HERE,OUT,OLD
FIELDS='whole0 whole1 sleeve0 sleeve1 fee gross net'.split()
def kernel():
    src=(OLD/'p1/book.cpp').read_text()
    inserts=[
        ('extern "C" int replay', '''struct Snapshot { std::map<int,Lot> lots[10]; double cash[10]; };
static std::map<int,Snapshot> snapshots;
static int entry=-1, origin=0, seatden=0, width0=0;
static const int *selected; static double *stat,*stock,*paid,*filled; static bool reserve;
extern "C" void options(int e,int origin0,int den,int width,int capped,const int *plan,double *stats,double *pnl,double *fees,double *buys){
    entry=e;origin=origin0;seatden=den;width0=width;selected=plan;stat=stats;stock=pnl;paid=fees;filled=buys;reserve=capped;
    if(e<0)snapshots.clear();
}
extern "C" int replay'''),
        ('double lastnav=1;', '''int focal=entry<0?0:(entry-origin)%10;
    double cap=1.e100;
    if(entry>=0){
        auto &s=snapshots.at(entry);
        for(int p=0;p<10;++p){
            lots[p]=s.lots[p];cash[p]=s.cash[p]; double v=cash[p];
            for(auto [j,lot]:lots[p]){
                double val=lot.units*op[size_t(entry)*n+j];v+=val;
                if(p==focal)stock[j]-=val;
            }
            stat[0]+=v;if(p==focal)stat[2]=v;
        }
        if(reserve)cap=stat[2]*(1-sf)/(1+bf)/seatden;
    }
    double lastnav=1;'''),
        ('int active=(i-start)%10;', '''int active=(i-origin)%10;
        if(entry<0 && i+10<=end){auto &s=snapshots[i];for(int p=0;p<10;++p){s.lots[p]=lots[p];s.cash[p]=cash[p];}}
        if(entry>=0 && i==entry+10 && i!=end) break;'''),
        ('const int *picks=target+size_t(i)*width;','const int *picks=(i==entry?selected:target+size_t(i)*width);'),
        ('for(;count<width && picks[count]>=0;++count)', 'for(;count<(i==entry?width0:width) && picks[count]>=0;++count)'),
        ('planned+=allocation*count;', 'if(i==entry)allocation=std::min(allocation,cap); planned+=allocation*count;'),
        ('flow[p][j]+=allocation;', 'flow[p][j]+=allocation; if(i==entry && p==focal)filled[j]+=allocation;'),
        ('cash[p]-=f.second+fee;fees+=fee;', '''cash[p]-=f.second+fee;fees+=fee;
                    if(entry>=0 && p==focal){ stock[j]-=f.second;paid[j]+=fee;stat[4]+=fee;}'''),
        ('finish:\n', '''finish:
    if(entry>=0 && until==stop+1){
        for(int p=0;p<10;++p){
            double v=cash[p];for(auto [j,lot]:lots[p]){double amount=lot.units*op[size_t(entry+10)*n+j];v+=amount;if(p==focal)stock[j]+=amount;}
            stat[1]+=v;if(p==focal)stat[3]=v;
        }
        for(int j=0;j<n;++j)stat[5]+=stock[j];stat[6]=stat[3]/stat[2]-1;
    }
''')]
    for old,new in inserts:
        assert src.count(old)==1,old
        src=src.replace(old,new)
    f=Path('/tmp')/('ep42-common-'+hashlib.sha256(src.encode()).hexdigest()[:15]+'.cpp')
    lib=f.with_suffix('.so')
    if not lib.exists():
        f.write_text(src);subprocess.run(['g++','-O2','-std=c++17','-shared','-fPIC',str(f),'-o',str(lib)],check=True)
    dll=ct.CDLL(str(lib));dll.options.argtypes=[ct.c_int]*5+[ct.c_void_p]*5
    dll.replay.argtypes=[ct.c_int]*5+[ct.c_void_p]*7+[ct.c_int]*3+[ct.c_double]*2+[ct.c_void_p,ct.c_char_p]
    return dll
def trial_call(lib, packed, lo, hi, e=-1, selected=None, cap=True):
    tar,den=packed;m=rp.M
    start=lo if e<0 else e;stop=hi if e<0 else e+10
    if selected is None:selected=np.array([-1],'i')
    stat=np.zeros(7); stocks=np.zeros((3,m.n));d=np.zeros((stop-start+1,13))
    lib.options(e,lo,den[e] if e>=0 else 0,len(selected),int(cap),selected.ctypes.data,stat.ctypes.data,*[x.ctypes.data for x in stocks])
    arr=[tar,den,*m.planes]
    rc=lib.replay(m.n,start,hi,stop,tar.shape[1],*[a.ctypes.data for a in arr],len(m.planes[-1]),-1,1,.001,.002,d.ctypes.data,b'')
    assert rc==stop+1
    if e>=0:assert abs((stat[5]-stat[4])/stat[2]-stat[6])<1e-10
    return stat,stocks
def main():
    rp.inputs();lib=kernel();m=rp.M; allrows=[];attributions=[];corners=[];a3=HERE/'a3'
    for scope,(lo,hi) in rp.SEG.items():
        ids=range(lo,hi-9)
        packed=(np.ascontiguousarray(rp.RANK[:,:64]),rp.DEN)
        orig=rp.direct()[0]
        name=orig[0]
        rp.runone(orig,scope)
        # The independent copies share the original decision-date incumbent holdings.
        rp.LIB.same_start_mode(1)
        trial_call(lib,packed,lo,hi)
        for spec in rp.direct()+[x for x in rp.random_specs()]:
            z,log,val=rp.runone(spec,scope,seed=1)
            rp.set_reference(scope,spec[0],1,log,val)
            for e in ids:
                sel=np.ascontiguousarray(log[e,130:130+log[e,129]],dtype='i')
                stat,data=trial_call(lib,packed,lo,hi,e,sel)
                allrows.append((scope,spec[0],e,(e-lo)%10,*stat))
                if spec[0] in {'SellTree','SellRidge','Diff','DiffLeft','ScreenDiff','ScreenDiffLeft','Intersection','IntersectionLeft','N2','N2Boundary','B0_40Path','B0_40'}:
                    original=set(rp.RANK[e,:rp.DEN[e]]); target=set(sel)
                    baseline_label=data[0]; left=rp.F[rp.FIELDS.index('risk'),e]; right=rp.F[rp.FIELDS.index('rtail'),e]
                    for j in original.symmetric_difference(target):
                        attributions.append((scope,spec[0],e,m.symbols[j],'excluded' if j in original else 'added',stat[2],data[0,j],data[1,j],data[2,j],left[j],right[j],val[e,0]))
        rp.LIB.same_start_mode(0)
        # Use the EP41 frozen rank and tree purchase plans, including other sleeves' schedule.
        allplans={'hold':{},'rank':{},'tree':{}}
        for e in ids:
            n=rp.NV[e];k=rp.DEN[e];count=k//5; ordered=rp.RANK[e,:n]
            ts=rp.F[0,e]; tt=ordered[np.lexsort((ordered,ts[ordered]))[::-1]]
            core=ordered[:k];pool=ordered[k:2*k];removed=tt[np.isin(tt,core)][-count:];base=core[~np.isin(core,removed)]
            allplans['hold'][e]=core
            allplans['tree'][e]=np.r_[base,tt[np.isin(tt,pool)][:count]]
            allplans['rank'][e]=np.r_[base,pool[:count]]
        for state in ['hold','tree','rank']:
            src=rp.engine.pack(m,allplans[state]);trial_call(lib,src,lo,hi)
            for rule in ['tree','rank']:
                for e in ids:
                    st,_=trial_call(lib,src,lo,hi,e,np.array(allplans[rule][e],dtype='i'),cap=state=='hold')
                    corners.append((scope,state,rule,e,(e-lo)%10,*st))
    pd.DataFrame(allrows,columns='scope arm entry_idx phase'.split()+FIELDS).to_parquet(OUT/'common_h10.parquet',index=False)
    pd.DataFrame(attributions,columns='scope arm entry_idx instrument role sleeve0 gross fee bought p_left p_right ticket'.split()).to_parquet(OUT/'common_tickets.parquet',index=False)
    co=pd.DataFrame(corners,columns='scope state rule entry_idx phase'.split()+FIELDS)
    co.to_parquet(a3/'corners.parquet',index=False)
    direct=pd.read_parquet(OLD/'p2/results/corners.parquet')
    cs=co.query("phase==0 and state!='hold'").merge(direct,on=['scope','state','rule','entry_idx'])
    assert len(cs)==len(direct)
    for a,b in [('whole0','whole_open'),('whole1','whole_end')]:assert (cs[a]-cs[b]).abs().max()<1.e-10
    old=pd.read_parquet(OLD/'p2/results/common_start.parquet')
    cs=co.query("phase==0 and state=='hold'").merge(old.rename(columns={'arm':'rule','net':'orig_net'}),on=['scope','rule','entry_idx'])
    assert len(cs)==len(old) and (cs.net-cs.orig_net).abs().max()<1.e-10
    print('common_origin rows',len(allrows),'phase0 validated and corners',len(co),flush=True)
if __name__=='__main__':main()
