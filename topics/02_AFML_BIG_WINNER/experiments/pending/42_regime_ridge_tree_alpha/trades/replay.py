"""Run close-time policies through the EP41 C++ broker book. Only the target hook changes."""
import ctypes as ct
from pathlib import Path
import sys, hashlib, tempfile, subprocess, json, os
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import numpy as np, pandas as pd
from sources import HERE,OLD,OUT,PRIVATE
sys.path.insert(0,str(OLD/'p1'))
import engine
FIELDS='tree shallow riskcap riskadv announced past_excess10 risk rtail leftq rightq enabled sector cap adv vol20 pos60 vol60 money_rel20'.split()
NEW=HERE.parent
def compile_kernel():
    code=(OLD/'p1/book.cpp').read_text()
    lines=[('extern "C" int replay', (HERE/'policy.hpp').read_text()+'\nextern "C" int replay'),
           ('double planned=0,unfilled=0,openval=0;', '''double planned=0,unfilled=0,openval=0;
             int local[64];std::fill(local,local+64,-1);
             if(i+10<=end && denom[i]>0){choose(i,denom[i],lots,cash,active,cl+size_t(i-1)*n,sell+size_t(i-1)*n,local); if(force_reference_state){std::fill(local,local+64,-1); std::copy(s.rank+size_t(i)*n,s.rank+size_t(i)*n+denom[i],local);}}'''),
           ('const int *picks=target+size_t(i)*width;','const int *picks=local;')]
    for needle,repl in lines:
        assert code.count(needle)==1
        code=code.replace(needle,repl)
    src=Path('/tmp')/('ep42-trades-'+hashlib.sha256(code.encode()).hexdigest()[:20]+'.cpp')
    lib=src.with_suffix('.so')
    if not lib.exists():
        src.write_text(code)
        temp=src.with_suffix('.'+str(os.getpid())+'.so')
        subprocess.run(['g++','-O2','-std=c++17','-shared','-fPIC',str(src),'-o',str(temp)],check=True)
        temp.replace(lib)
    dll=ct.CDLL(str(lib))
    dll.replay.argtypes=[ct.c_int]*5+[ct.c_void_p]*7+[ct.c_int]*3+[ct.c_double]*2+[ct.c_void_p,ct.c_char_p]
    dll.configure.argtypes=[ct.c_int]*8+[ct.c_void_p]*8
    return dll
def inputs():
    global M,ROWS,RANK,DEN,NV,F,LIB,ORIG,REFS,SEG,SCORES
    M=engine.load(False)
    SCORES=pd.read_parquet(OLD/'p2/results/scores.parquet')
    key=['entry_idx','signal_date','instrument']
    shallow=pd.read_parquet(NEW/'scale/results/shallow_early.parquet')
    scores=SCORES.merge(pd.read_parquet(OUT/'covariates.parquet'),on=key,validate='1:1').merge(shallow,on=key,validate='1:1')
    scores=scores.merge(pd.read_parquet(OUT/'dual_scores.parquet',columns=key+['risk','rtail','enabled','right']),on=key,validate='1:1')
    assert len(scores)==len(SCORES)
    for source,target in [('T','tree'),('risk','leftq'),('rtail','rightq')]:
        scores[target]=scores.groupby('entry_idx')[source].rank(pct=True)
    scores['shallow']=scores.shallow_early
    scores['sector']=pd.Categorical(scores.l1_name.replace({'未知':None})).codes
    meddir=next(HERE.parents[1].glob('40_*'))/'lightgbm/followup/csi800_69/results/models/transfer'
    for q,idx in scores.groupby(scores.signal_date.dt.to_period('Q')).groups.items():
        med=json.loads((meddir/str(q)/'medians.json').read_text())
        for col in ['pos60','vol60','money_rel20']:scores.loc[idx,col]=scores.loc[idx,col].fillna(med[col])
    n=M.n; rows=len(M.days)
    RANK=np.full((rows,n),-1,dtype='i'); DEN=np.zeros(rows,'i');NV=DEN.copy()
    F=np.full((len(FIELDS),rows,n),np.nan,dtype='f')
    j=M.symbols.get_indexer(scores.instrument)
    assert np.all(j>=0)
    scores['j']=j
    for i,name in enumerate(FIELDS):F[i,scores.entry_idx,j]=scores[name].astype('float32')
    for e,g in scores.groupby('entry_idx'):
        ids=g.sort_values(['R','instrument'],ascending=False).j
        RANK[e,:len(ids)]=ids; NV[e]=len(ids);DEN[e]=len(ids)//10
    ROWS=rows;LIB=compile_kernel();ORIG={};REFS={}
    SEG={'primary':M.days.get_indexer(['2021-01-11','2025-03-03']), 'later':M.days.get_indexer(['2025-03-03','2026-10-12'])}
def runone(spec,scope,seed=0,mul=1,save=False):
    name,kind,n,width,bits,control,ref=spec
    lo,hi=SEG[scope]; length=hi-lo+1
    log=np.full((ROWS,256),-1,'i'); val=np.zeros((ROWS,10))
    dummy=np.zeros((ROWS,M.n),dtype=np.uint8) if scope not in ORIG else ORIG[scope]
    reference=REFS.get((scope,ref,mul),REFS.get((scope,ref,1),(np.zeros_like(log),np.zeros_like(val))))
    data=[RANK,NV,F,dummy,*reference,log,val]
    LIB.configure(M.n,ROWS,kind,n,width,bits,control,seed,*[a.ctypes.data for a in data])
    daily=np.zeros((length,len(engine.COLS)))
    with tempfile.TemporaryDirectory() as tmp:
        file=Path(tmp)/'orders.csv'
        arr=[RANK,DEN,*M.planes]
        ret=LIB.replay(M.n,lo,hi,hi,64,*[a.ctypes.data for a in arr],len(M.planes[-1]),-1,1,.001*mul,.002*mul,daily.ctypes.data,str(file).encode() if save else b'')
        assert ret==hi+1,(name,scope,ret,hi)
        d=pd.DataFrame(daily,columns=engine.COLS);d['date']=M.days[lo:hi+1]
        if save:
            path=OUT/'books'/scope/name;path.mkdir(parents=True,exist_ok=True)
            o=pd.read_csv(file,header=None,names='entry_idx sleeve j target net broker fee blocked'.split())
            o['instrument']=M.symbols[o.j]
            o.to_parquet(path/'orders.parquet',index=False)
            d.to_parquet(path/'daily.parquet',index=False)
            ev=[]
            for e in range(lo,hi-9):
                nrm=log[e,0]
                selected=log[e,130:130+log[e,129]]
                assert len(set(selected))==len(selected) and len(selected)<=DEN[e]
                ev.append(dict(entry_idx=e,signal_date=M.days[e-1],k=int(DEN[e]),ticket=val[e,0],
                    planned_turnover=val[e,1],natural_count=val[e,2],style_pairs=val[e,3],
                    removed=M.symbols[log[e,1:1+nrm]].tolist(),added=M.symbols[[j for j in log[e,65:129] if j>=0]].tolist(),target=M.symbols[selected].tolist()))
            pd.DataFrame(ev).to_parquet(path/'decisions.parquet',index=False)
    if kind==0 and name=='Ridge':
        mask=np.zeros((ROWS,M.n),dtype=np.uint8)
        for e in range(lo,hi-9):
            assert log[e,196]<=59
            mask[e,log[e,197:197+log[e,196]]]=1
        ORIG[scope]=mask
    d['month']=d.date.dt.strftime('%Y-%m')
    d['opening']=d.nav.shift().fillna(1)
    z=d.groupby('month').agg(opening=('opening','first'),closing=('nav','last'),fee=('fee','sum'),buy=('buy','sum'),sell=('sell','sum')).iloc[1:-1].copy()
    z['net']=z.closing/z.opening-1;z['fee']/=z.opening;z['turnover']=(z.buy+z.sell)/z.opening
    z['gross']=z.net+z.fee
    z['terminal']=float(d.nav.iloc[-1]);z['drawdown']=float((d.nav/d.nav.cummax()-1).min())
    return z.reset_index()[['month','net','gross','fee','turnover','terminal','drawdown']].assign(scope=scope,arm=name,seed=seed,fees=mul),log,val
def direct():
    specs=[('Ridge',0,0,0,0,0,None),('EP38Buffer',6,0,0,0,0,None),('SellTree',4,0,0,0,0,None),('SellRidge',4,0,0,0,1,None)]
    specs += [('Sell'+s,4,0,0,i,3,None) for s,i in [('Pos',1),('Vol',2),('Money',3)]]
    for n in [1,2,3]:
        specs += [(f'N{n}',1,n,0,0,0,None),(f'N{n}Boundary',1,n,0,0,1,f'N{n}')]
    specs+= [(name,1,2,width,bits,0,None) for name,width,bits in [
        ('Narrow',3,0),('WideGate',0,1),('NarrowGate',3,1),('Shallow',0,8),('Safe',0,2),('Announced',0,4),
        ('Combo',3,3),('ComboNoCap',0,3),('ComboNoGate',3,2)]]
    specs += [('ComboBoundary',1,2,3,3,1,'Combo')]
    specs += [(f'Combo{n}',1,n,3,3,0,None) for n in [1,3]]
    for n,width in [(0,40),(24,40),(24,45)]:
        prefix=f'B{n}_{width}';specs += [(prefix,2,n,width,0,0,None),(prefix+'Path',2,n,width,64,0,None),(prefix+'Cash',5,n,width,0,0,prefix)]
    for name,bits in [('Diff',0),('ScreenDiff',16),('Intersection',32)]:
        specs += [(name,3,2,0,bits,0,None),(name+'Left',3,2,0,bits,1,name)]
    return specs
def random_specs():
    items=[('SellUniform',4,0,0,0,2,None),('SellStyle',4,0,0,0,4,None),('SellVolMatch',4,0,0,0,5,None)]
    for n in [1,2,3]:items.append((f'N{n}Random',1,n,0,0,2,f'N{n}'))
    for name,width,bits,n in [('Narrow',3,0,2),('WideGate',0,1,2),('NarrowGate',3,1,2),('Shallow',0,8,2),('Safe',0,2,2),('Announced',0,4,2),('Combo',3,3,2),('ComboNoGate',3,2,2),('ComboNoCap',0,3,2),('Combo1',3,3,1),('Combo3',3,3,3)]:items.append((name+'Random',1,n,width,bits,2,name))
    for n,width in [(0,40),(24,40),(24,45)]:
        prefix=f'B{n}_{width}Path'
        for control in [2,3]:items.append((prefix+('Random' if control==2 else 'Amount'),2,n,width,64,control,prefix))
    for name,bits in [('Diff',0),('ScreenDiff',16),('Intersection',32)]:
        items.append((name+'Random',3,2,0,bits,2,name))
    return items
def set_reference(scope,name,mul,log,vals):
    if name in {spec[-1] for spec in direct()+random_specs()}:REFS[(scope,name,mul)]=(log,vals)
def runseed(job):
    mode,seed=job
    spec=random_specs()[mode];frames=[]
    for scope in SEG:
        z,_,_=runone(spec,scope,seed,save=seed==1)
        frames.append(z)
    return pd.concat(frames,ignore_index=True)
def main():
    inputs()
    frames=[]
    for scope in SEG:
        for mul in [1,2]:
            for spec in direct():
                z,log,val=runone(spec,scope,mul=mul,save=mul==1)
                set_reference(scope,spec[0],mul,log,val)
                frames.append(z)
    pd.concat(frames).to_parquet(OUT/'direct_months.parquet',index=False)
    raw=pd.read_parquet(OLD/'p2/results/funded_daily.parquet')
    audit=[]
    for scope in SEG:
        for name,prior in [('Ridge','hold'),('SellTree','rank')]:
            ref=raw[(raw.scope==scope)&(raw.arm==prior)&(raw['mul']==1)].set_index('date')
            act=pd.read_parquet(OUT/'books'/scope/name/'daily.parquet').set_index('date')
            err=(ref[['nav','fee','cash','crossed']]-act[['nav','fee','cash','crossed']]).abs().max()
            assert err.max()<1e-10
            audit.append(dict(scope=scope,arm=name,**err.to_dict()))
    pd.DataFrame(audit).to_csv(OUT/'parity.csv',index=False)
    print('base accounts reconciled',flush=True)
    random_dir=OUT/'random';random_dir.mkdir(exist_ok=True)
    jobs=[(i,k) for i,spec in enumerate(random_specs()) for k in range(1,201)]
    with ProcessPoolExecutor(max_workers=5,mp_context=get_context('fork')) as pool:
        block=[]
        for result in pool.map(runseed,jobs,chunksize=5):
            block.append(result)
            if len(block)==200:
                tab=pd.concat(block,ignore_index=True)
                arm=tab.arm.unique().item(); tab.to_parquet(random_dir/(arm+'.parquet'),index=False)
                print('random complete',arm,flush=True);block=[]
if __name__=='__main__':main()
