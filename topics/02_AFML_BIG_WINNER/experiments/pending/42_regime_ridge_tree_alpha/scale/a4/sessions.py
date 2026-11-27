"""Reconcile real position session P&L, legacy holding ages and historical factor projections."""
from scores import *
import hashlib
sys.path.insert(0,str(EP42/'state'))
import core42 as core
from matching import covariates
from engine import LOCAL,STORE

def reference_value(m):
    folder=Path.home()/'.cache/a_share/ep32'
    path=folder/'joint_pe_v35/stock_pe_panel.parquet'
    receipt=next(EP42.parent.glob('32_*/extensions/v35_pe_activity_joint/outputs/feature_receipt.json'))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==json.loads(receipt.read_text())['stock_panel_sha256']
    mapping=pd.read_parquet(folder/'extension_v2/products/panel.parquet',columns=['instrument','security_id']).drop_duplicates()
    assert mapping.instrument.is_unique
    key=mapping.set_index('instrument').security_id.reindex(m.symbols)
    import pyarrow.parquet as pq
    present=set(pq.ParquetFile(path).schema.names)
    pe=pd.read_parquet(path,columns=[k for k in key.dropna() if k in present]).reindex(index=m.days,columns=key)
    pe.columns=m.symbols
    return (1/pe.where(pe.ne(0))).replace([np.inf,-np.inf],np.nan)

def factors(m,wide):
    cap,adv,_,industry,_=covariates(m)
    close=pd.read_parquet((LOCAL if wide else ep.PRIVATE)/'qfq_close.parquet').reindex(index=m.days,columns=m.symbols)
    ret=close.pct_change(fill_method=None)
    ix=pd.read_parquet(ep.PRIVATE/'market.parquet').close.reindex(m.days).pct_change(fill_method=None)
    # Pairwise market variance on the stock's observed sessions.
    valid=ret.notna() & np.isfinite(ix).to_numpy()[:,None]
    r=ret.where(valid);rm=pd.DataFrame(np.broadcast_to(ix.to_numpy()[:,None],ret.shape),index=ret.index,columns=ret.columns).where(valid)
    def roll(x):return x.rolling(120,min_periods=60).mean()
    cov=roll(r*rm)-roll(r)*roll(rm)
    vm=roll(rm**2)-roll(rm)**2
    beta=cov/vm.where(vm>1e-15)
    resid=(roll(r*r)-roll(r)**2-beta*cov).clip(lower=0)**.5
    ep_yield=reference_value(m)
    return np.log(np.where(cap>0,cap,np.nan)),beta.to_numpy(),resid.to_numpy(),ep_yield.to_numpy(),industry

def design(m,fac,eligible,day,all_ids):
    cap,beta,resid,ep_yield,industry=fac
    ix=day-1;sector=industry(ix)
    fv=np.column_stack([x[ix] for x in [cap,beta,resid,ep_yield]])
    base=(eligible[ix] & np.isfinite(fv).all(axis=1) & (sector!='未知'))
    if base.sum()<30:return None
    industries=sorted(set(sector[base]))
    mean=fv[base].mean(axis=0);sigma=fv[base].std(axis=0);sigma[sigma<1e-12]=1.
    # Extra intercept would be collinear with full sector dummy set.
    fx=(fv-mean)/sigma
    mat=np.column_stack([fx]+[(sector==s).astype(float) for s in industries])
    identified=np.isin(sector,industries) & np.isfinite(fx).all(axis=1)
    return base,identified,mat,fx,sector

def assign_ages(trace,m,start):
    eidx={};prevage=np.zeros(len(trace),int);newage=np.zeros(len(trace),int)
    for ix,(day,p,stk,old,new,target) in enumerate(trace[['day','phase','stock','old_units','new_units','target']].itertuples(index=False,name=None)):
        key=(p,stk);entry=eidx.get(key)
        if old>0:
            assert entry is not None,(day,key)
            prevage[ix]=day-entry
        if new>0:
            if old<=0 or (target>0 and (day-start)%10==p and day-entry>=10 and m.sell[day,stk]):entry=day
            assert entry is not None
            eidx[key]=entry;newage[ix]=day-entry+1
        else:eidx.pop(key,None)
    return prevage,newage

def summarize():
    d=pd.read_parquet(OUT/'daily.parquet')
    z=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    age_rec=[];factor_rec=[];style_rec=[];sector_rec=[];sessions=[];fit_rec=[]
    for pool in ['300','800']:
        wide=pool=='800';m=core.market(wide);fac=factors(m,wide);op,cl=m.planes[:2]
        if wide:
            sw=pd.read_parquet(FROZEN/'scores.parquet',columns=KEY+['entry_idx'])
        else:sw=pd.read_parquet(SCORES,columns=KEY+['entry_idx'])
        eligible=np.zeros_like(m.members,dtype=bool)
        eligible[sw.entry_idx.to_numpy()-1,m.symbols.get_indexer(sw.instrument)]=True
        for n,span in enumerate(core.SEG800 if wide else core.SEG300,1):
            ts={}
            for arm in ['R','T']:
                f=OUT/f'trace_{pool}_{arm}_{n}.parquet' if wide else EP42/'state/results/main'/f'trace_{arm}_{n}.parquet'
                trace=pd.read_parquet(f)
                ages=assign_ages(trace,m,m.days.get_loc(span[0]))
                onage,dayage=ages
                for typ,col,age in [('overnight','overnight',onage),('intraday','intraday',dayage)]:
                    ag=np.where(age>10,11,age)
                    agdf=trace.assign(age=ag,year=m.days[trace.day].year).groupby(['year','age'])[col].sum()
                    for (yr,a),amt in agdf.items():age_rec.append((pool,n,arm,typ,yr,a,amt))
                end=d[(d.pool==pool)&(d.arm==arm)&(d.segment==n)&d.fee_multiple.eq(1)].date.max()
                nav=d[(d.pool==pool)&(d.arm==arm)&(d.segment==n)&d.fee_multiple.eq(1)].set_index('date')
                ts[arm]=(trace.groupby('day'),nav,end)
                g=trace.groupby('day')[['overnight','intraday','fee']].sum()
                for day,rec in g.iterrows():
                    dt=m.days[day];prev=nav.loc[dt,'prev']
                    sessions.append((pool,n,arm,dt,prev,rec.overnight,rec.intraday,rec.fee,(rec.overnight+rec.intraday-rec.fee)/prev))
            index_days=sorted(set(ts['R'][0].indices)|set(ts['T'][0].indices))
            for day in index_days:
                dt=m.days[day]; prevcl=cl[day-1]; opnow=op[day]; clnow=cl[day]
                both=day in ts['R'][0].indices and day in ts['T'][0].indices
                if not both:continue
                shape=design(m,fac,eligible,day,None)
                for typ in ['overnight','intraday']:
                    price=prevcl if typ=='overnight' else opnow
                    final=opnow if typ=='overnight' or day==m.days.get_loc(span[1]) else clnow
                    realized=np.divide(final,price,out=np.full(m.n,np.nan),where=price>0)-1
                    if shape is None:base=np.zeros(m.n,bool)
                    else:base=shape[0] & np.isfinite(realized)
                    fitted=None
                    if base.sum()>=30 and shape is not None:
                        _,identified,mat,fx,sec=shape
                        sub=mat[base]
                        used=(sub!=0).any(axis=0)
                        if len(sub)>used.sum() and np.linalg.matrix_rank(sub[:,used])==used.sum():
                            b=np.zeros(mat.shape[1]);b[used]=np.linalg.lstsq(sub[:,used],realized[base],rcond=None)[0]
                            fitted=(b,identified & ((mat[:,4:]@used[4:].astype(float))>0),mat,fx,sec)
                    fit_rec.append((pool,n,dt,typ,int(base.sum()),0 if fitted is None else int(used.sum()),bool(fitted is not None)))
                    for arm,(groups,nav,end) in ts.items():
                        g=groups.get_group(day);ids=g.stock.to_numpy()
                        units=g.old_units.to_numpy() if typ=='overnight' else g.new_units.to_numpy()
                        value=np.where(units>0,units*np.nan_to_num(price[ids]),0.)
                        actual=g[typ].to_numpy(); capital=nav.loc[dt,'prev']
                        actual_total=actual.sum();terms=np.zeros(5);covered=0.;actual_support=0.
                        if fitted is not None:
                            b,identified,mat,fx,sec=fitted
                            ok=identified[ids]&np.isfinite(realized[ids])&(value>0)
                            vv=value[ok];ss=ids[ok];covered=vv.sum();actual_support=actual[ok].sum()
                            terms[:4]=(vv@mat[ss,:4])*b[:4]
                            terms[4]=vv@(mat[ss,4:]@b[4:])
                            for fi,field in enumerate(['logcap','beta120','idio_vol120','earnings_yield']):
                                style_rec.append((pool,n,dt,arm,typ,field,capital,covered,(vv@fx[ss,fi]) if len(ss) else 0.))
                        sec=fac[-1](day-1)[ids]
                        sectors=pd.Series(value).groupby(sec).sum()
                        for s,amt in sectors.items():
                            if amt:sector_rec.append((pool,n,dt,arm,typ,s,capital,amt))
                        gap=actual_total-actual_support
                        row=(pool,n,dt,arm,typ,capital,value.sum(),covered,*terms,actual_support-terms.sum(),gap,actual_total)
                        factor_rec.append(row)
    pd.DataFrame(age_rec,columns='pool segment arm session year age amount'.split()).to_csv(OUT/'age.csv',index=False)
    width='pool segment date arm session initial_nav held_amount covered_amount size beta idio_vol earnings_yield industry unexplained_on_support unsupported actual_gross'.split()
    ff=pd.DataFrame(factor_rec,columns=width)
    assert abs(ff.iloc[:,8:15].sum(axis=1)-ff.actual_gross).max()<1e-12
    ff['Z1']=ff.date.map(z.shift(1))
    atomic_parquet(ff,OUT/'factors.parquet')
    atomic_parquet(pd.DataFrame(sector_rec,columns='pool segment date arm session sector initial_nav holding_value'.split()),OUT/'sector_exposure.parquet')
    atomic_parquet(pd.DataFrame(style_rec,columns='pool segment date arm session factor initial_nav covered_value standardized_exposure_amount'.split()),OUT/'style_exposure.parquet')
    pd.DataFrame(fit_rec,columns='pool segment date session stock_count parameter_count identified'.split()).to_csv(OUT/'risk_design.csv',index=False)
    atomic_parquet(pd.DataFrame(sessions,columns='pool segment arm date prev_nav overnight intraday fee net_return'.split()),OUT/'sessions.parquet')
if __name__=='__main__':summarize()
