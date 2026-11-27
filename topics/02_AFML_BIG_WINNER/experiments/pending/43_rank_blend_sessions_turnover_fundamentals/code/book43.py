from ep43lib import *
import os
def book(wide):
    m=market(wide)
    src=(E/'state/weighted.cpp').read_text()
    inc=ROOT/'code/decision.hpp'
    src=src.replace('extern "C" int replay','#include "'+str(inc)+'"\nextern "C" int replay')
    src=src.replace('bool expired=', '''std::vector<int> chosen; std::vector<double> allocation;
            bool custom=decision && conf.mode;
            if(custom){
                choose43(width,denom[i],picks,weights+size_t(i)*width,lots[p],cash[p],cl+size_t(i-1)*n,
                         sell+size_t(i-1)*n,chosen,allocation);picks=chosen.data();}
            bool expired=''')
    src=src.replace('return weights?','return custom?allocation[k]:weights?').replace('count<width &&','count<(custom?(int)chosen.size():width) &&')
    ext=ROOT/'code/forks.hpp'
    src=src.replace('extern "C" int replay','#include "'+str(ext)+'"\nextern "C" int replay')
    src=src.replace('int active=(i-start)%10;', '''int origin=base43>=0?base43:start;
        int active=(i-origin)%10;
        if(record43){
            Snapshot &snap=snapshots[i];for(int p=0;p<10;++p){snap.lots[p]=lots[p];snap.cash[p]=cash[p];}
        } else if(fork43>=0 && i==start){
            const auto &snap=snapshots.at(i);for(int p=0;p<10;++p){lots[p]=snap.lots[p];cash[p]=snap.cash[p];}
        }
        if(fork43>=0 && (i==fork43+10 || i==start)){
            int p=(fork43-origin)%10;wealth43=cash[p];
            for(const auto &h:lots[p])wealth43+=h.second.units*op[size_t(i)*n+h.first];if(i==start)start43=wealth43;
        }''')
    src=src.replace('choose43(width','audit_day=i;measure_L1_43=(i==fork43);int saved_mode=conf.mode;if(i==fork43)conf.mode=alternate43;choose43(width').replace('picks=chosen.data();','picks=chosen.data();conf.mode=saved_mode;')
    src=src.replace('requested+=weight(count);','''if(goals43){
                        int key[]={i,p,j};double frac43=weight(count);
                        std::fwrite(key,sizeof(int),3,goals43);std::fwrite(&frac43,sizeof(double),1,goals43);}
                    requested+=weight(count);''')
    name='book43-'+hashlib.sha256(src.encode()+inc.read_bytes()+ext.read_bytes()).hexdigest()[:16]
    path=Path('/tmp')/(name+'.so')
    if not path.exists():
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'engine.cpp';p.write_text(src)
            subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(p),'-o',str(p.with_suffix('.so'))],check=True)
            os.replace(p.with_suffix('.so'),path)
    m.lib=ct.CDLL(str(path));m.lib.setup43.argtypes=[ct.c_int,ct.c_double,ct.c_double]
    fn=m.lib.replay;fn.argtypes=m.weighted.argtypes;m.weighted=fn
    return m
def pack(m,f,score,kmap=None):
    # order descending by instrument on score ties, average ranks in the objective
    f=f[['instrument','entry_idx']].assign(score=np.asarray(score)).dropna(subset=['score'])
    f=f.sort_values(['entry_idx','score','instrument'],ascending=[True,False,False])
    g=f.groupby('entry_idx',sort=False); size=g.size()
    shape=(len(m.days),size.max());idx=f.entry_idx.to_numpy();j=g.cumcount().to_numpy()
    ids=np.full(shape,-1,np.int32);ids[idx,j]=m.symbols.get_indexer(f.instrument)
    w=np.zeros(shape);w[idx,j]=g.score.rank()/(g.score.transform('size')+1)-.5
    ks=np.zeros(len(m.days),np.int32);ks[size.index]=(size//10 if kmap is None else kmap.reindex(size.index)).values
    return ids,ks,w
def sliced(p):
    ids,k,_=p
    v=ids[:,:k.max()].copy();v[np.arange(v.shape[1])[None,:]>=k[:,None]]=-1
    return v,k
def mode_run(m,p,span,mode=0,cap=.05,tau=.01,fee=1,trace=None):
    m.lib.setup43(mode,cap,tau)
    return replay(m,p if mode else (sliced(p) if len(p)==3 else p),span,fee=fee,trace=trace)
