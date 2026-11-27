"""Account and selection replay on the frozen narrow scoring universe."""
from collections import defaultdict
import json
import hashlib
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from ep41inputs import *

def industry_seats(rank,groups,budget):
    counts=defaultdict(int)
    keep=[]
    for stock in rank:
        group=groups[stock]
        if counts[group]<budget.get(group,0):
            keep.append(stock);counts[group]+=1
    return keep

def selection(d):
    plans=defaultdict(dict);diagnostics=[];stages=[];holdings=[]
    limits=[]
    hist=pd.read_csv(next(PENDING.glob('32_*/extensions/v28*/outputs/historical_alerts.csv.gz')),parse_dates=['date'])
    hist=hist.query("frequency=='W' and benchmark=='CSI_ALL' and level=='L2' and threshold==.10")
    prediction_path=Path.home()/'.cache/a_share/ep32/regime_v26/predictions/W_0.1_CSI_ALL.parquet'
    predictions=pd.read_parquet(prediction_path,filters=[('model','=','risk_diffusion_min__market126'),('level','=','L2')])
    clocks=pd.DatetimeIndex(sorted(predictions.date.unique()))
    selected=predictions[predictions.prob.ge(.11)]
    historic=selected[selected.date.le('2024-09-30')]
    assert set(historic.row_id)==set(hist.row_id)
    hist=selected
    weights={}
    for f in sorted((ep.PRIVATE/'weights').glob('????-??.json')):
        raw=json.loads(f.read_text())['data']
        z=pd.DataFrame(raw['items'],columns=raw['fields']);z['stock']=z.con_code.str[-2:]+z.con_code.str[:6]
        for dt,g in z.groupby('trade_date'):weights[pd.Timestamp(dt)]=g.set_index('stock').weight
    dates=pd.DatetimeIndex(sorted(weights))
    for day,g in d.groupby('signal_date'):
        g=g.sort_values(['R','instrument'],ascending=False).set_index('instrument')
        names=g.index;k=len(g)//10;m=k//5;core=names[:k];reserve=names[k:2*k]
        e=int(g.entry_idx.iloc[0]);sets={'R':list(core)}
        def ordered(feature,idx=None,high=True):
            sel=g if idx is None else g.loc[idx]
            return sel.assign(code=sel.index).sort_values([feature,'code'],ascending=[not high,not high]).index
        models=[c for c in g if c.startswith(('M1_','M2_','M3_')) or c=='T']
        for col in models:
            swap=core.difference(ordered(col,core)[-m:]).append(ordered(col,reserve)[:m])
            sets[col]=list(swap)
            if not col.endswith('_half'):sets['top_'+col]=list(ordered(col)[:k])
        i=dates.searchsorted(day,side='left')-1
        # At least one later signal close after the effective snapshot day.
        for tag,sector in [('industry','l1_name'),('pseudo','pseudo'),('l2','l2_code')]:
            codes=g[sector].to_dict()
            basebudget=g.loc[core,sector].value_counts().to_dict()
            rank=ordered('I_'+tag)
            sets['I_free_'+tag]=list(rank[:k])
            sets['I_fixed_'+tag]=industry_seats(rank,codes,basebudget)
            if tag=='industry' and i>=0:
                w=weights[dates[i]].reindex(names)
                supported=w.sum()/weights[dates[i]].sum()
                # Weight archive records the effective session only. The
                # registered cap requires a verified point-in-time benchmark.
                limits.append((day,dates[i],supported,'I_cap_base' in sets))
        sector=g.sector
        b=sector.loc[core].value_counts().to_dict()
        rank_peer=ordered('I2_stock')
        # Unknown-sector holdings keep the original Ridge order inside that budget.
        peer=list(rank_peer);unknown=[s for s in names if sector.at[s]=='未知']
        iterator=iter(unknown)
        peer=[next(iterator) if sector.at[s]=='未知' else s for s in peer]
        sets['I2_original_peer']=industry_seats(peer,sector.to_dict(),b)
        era='SW2014' if day<pd.Timestamp('2021-12-13') else 'SW2021'
        latest=clocks[clocks<=day].max()
        active=hist[(hist.era==era)&hist.date.eq(latest)] if day-latest<pd.Timedelta(days=7) else hist.iloc[:0]
        # No archived weekly prediction beyond archive endpoint. Historical absence after endpoint is unknown.
        ok=day>=I2_START and day<=I2_END
        alert=set(active.loc[active.date.eq(active.date.max()),'industry_code'])
        mom=g[sector.ne('未知')].groupby('sector').mom20.mean().sort_values(ascending=False)
        for tag,sectors in [('alert',alert),('momentum',set(mom.iloc[:max(1,len(mom)//10)].index))]:
            budget=b.copy();replaceable=[s for s in reversed(core) if sector.at[s] not in sectors and sector.at[s]!='未知']
            addable=[s for s in names[k:] if sector.at[s] in sectors]
            if replaceable and addable and ok:
                budget[sector.at[replaceable[0]]]-=1
                cat=sector.at[addable[0]];budget[cat]=budget.get(cat,0)+1
            for t,rnk in [('ridge',names),('peer',peer)]:
                sets['I2_'+tag+'_'+t]=industry_seats(rnk,sector.to_dict(),budget)
        for n in [5,10,20]:
            col='E_h'+str(n)
            pick=ordered(col)[:k]
            sets[col]=list(pick)
            if e+20<len(M.days):
                ids=M.symbols.get_indexer(pick)
                for a,bnd in [(0,5),(5,10),(10,20)]:
                    values=M.o[e+bnd,ids]/M.o[e+a,ids]-1
                    stages.append((day,col,a,bnd,k,np.isfinite(values).sum(),np.nanmean(values)))
        for count in [2,3]:
            for tag in ['risk','random','vol20']:
                candidates=names[:int(np.ceil(1.2*k))]
                if not g.veto_enabled.iloc[0]: pick=core
                else:
                    reject=(ordered(tag,core)[:count] if tag!='random' else sorted(core,key=lambda s:hashlib.sha256(f'{day.date()}|1|{s}'.encode()).digest())[:count])
                    pick=core.difference(reject).append(candidates[k:k+count])
                sets[f'V_{tag}_{count}']=list(pick)
        for name,ss in sets.items():
            assert len(ss)==len(set(ss))==k
            ids=M.symbols.get_indexer(ss);assert ids.min()>=0
            plans[name][e]=ids
            diagnostics.append((day,name,len(core.intersection(ss))/k,g.loc[ss,'vol20'].mean(),g.loc[ss,'l1_name'].value_counts(normalize=True).pow(2).sum(),int(g.loc[ss,'h10'].isna().sum())))
            holdings.append((day,name,list(ss)))
    pd.DataFrame(diagnostics,columns='date arm core_overlap vol20 industry_hhi censored'.split()).to_parquet(OUT/'exposures.parquet',index=False)
    pd.DataFrame(holdings,columns=['date','arm','instruments']).to_parquet(OUT/'target_lists.parquet',index=False)
    pd.DataFrame(limits,columns=['date','snapshot','weight_coverage','all_mapped']).to_csv(OUT/'i1_weight_coverage.csv',index=False)
    pd.DataFrame(stages,columns='signal_date arm from_session to_session seats known gross_mean'.split()).to_csv(OUT/'e3_stages.csv',index=False)
    return plans

def account(arm,plan,h,start,end,segment):
    op,cl=M.marks['flat'];u=np.zeros((h,M.n));cash=np.full(h,1/h);due=np.full_like(u,-1,int)
    daily=[];orders=[];last=1.
    for i in range(start,end+1):
        phase=(i-start)%h
        expired=(u>0)&(due<=i)
        sales=np.where(expired & M.sell[i],u*np.nan_to_num(op[i]),0.)
        price=np.nan_to_num(op[i]);old=u.sum(axis=0);held=old>0
        if not np.isfinite(op[i,held]).all():raise ValueError((i,'open',M.symbols[held&~np.isfinite(op[i])]))
        retained=(u>0)&~(expired & M.sell[i])
        buy=np.zeros_like(u);denied=0.;planned=0.
        if i+h<=end and i in plan:
            ids=plan[i];allowed=ids[M.buy[i,ids] & M.members[i-1,ids] & ~retained[phase,ids]]
            available=cash[phase]+sales[phase].sum()*.998
            t=len(allowed)/len(ids);cap=available+u[phase,retained[phase]]@price[retained[phase]]
            budget=min(cap/(1+.001*t),available/(max(t,1e-12)*1.001))
            buy[phase,allowed]=budget/len(ids);planned=cap;denied=cap*(1-t)
        for a,b,j in ACTIONS:
            if i>=j:sales[:,b]+=sales[:,a];sales[:,a]=0
        signals=buy-sales;purchase=signals.clip(min=0);sell=(-signals).clip(min=0)
        p=purchase.sum(axis=0);s=sell.sum(axis=0);cross=np.minimum(p,s)
        fees=.001*purchase*(1-cross/np.maximum(p,1e-30))+.002*sell*(1-cross/np.maximum(s,1e-30))
        cash-=signals.sum(axis=1)+fees.sum(axis=1)
        assert cash.min()>-1e-9
        sold=expired&M.sell[i];u[sold]=0;due[sold]=-1
        add=buy[phase]>0;u[phase,add]=buy[phase,add]/price[add];due[phase,add]=i+h
        mark=op[i] if i==end else cl[i];units=u.sum(axis=0)
        if not np.isfinite(mark[units>0]).all():raise ValueError((i,'mark',M.symbols[(units>0)&~np.isfinite(mark)]))
        nav=cash.sum()+units@np.nan_to_num(mark)
        net=p-s
        daily.append((M.days[i],nav,cash.sum(),fees.sum(),net.clip(min=0).sum(),(-net).clip(min=0).sum(),cross.sum(),denied,planned,nav-last+fees.sum()))
        for j in np.flatnonzero(net):
            orders.append((i,j,net[j],fees[:,j].sum()))
        last=nav
    d=pd.DataFrame(daily,columns='date nav cash fee buy sell crossed denied planned gross_pnl'.split())
    o=pd.DataFrame(orders,columns='entry_idx symbol_id net_amount fee'.split())
    for frame in [d,o]:frame['arm']=arm;frame['segment']=segment;frame['hold']=h
    return d,o

def run(arm):
    frames=[];trades=[];plan=PLANS[arm]
    for seg,ds,de in SEG:
        if arm.startswith('I2_'):
            ds=max(pd.Timestamp(ds),I2_START+pd.offsets.BDay());de=min(pd.Timestamp(de),I2_END)
            if ds>=de:continue
        start,end=M.days.searchsorted(ds),M.days.searchsorted(de,side='right')-1
        for h in ([5,10,20] if arm.startswith('E_h') else [10]):
            dd,oo=account(arm,plan,h,start,end,seg);frames.append(dd);trades.append(oo)
    pd.concat(frames).to_parquet(CACHE/('daily_'+arm+'.parquet'),index=False)
    pd.concat(trades).to_parquet(CACHE/('orders_'+arm+'.parquet'),index=False,compression='zstd')
    return arm

if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    ep.ledger.accounts.OUT=CACHE
    M,ACTIONS=ep.ledger.setup('flat')
    I2_START,I2_END=map(pd.Timestamp,['2021-01-08','2026-10-12'])
    paths=sorted(CACHE.glob('*_pred.parquet'));assert len(paths)==23
    d=pd.concat([pd.read_parquet(f) for f in paths],ignore_index=True)
    d=d.merge(pd.read_parquet(CACHE/'i2_scores.parquet'),on=KEY,validate='1:1')
    PLANS=selection(d)
    with ProcessPoolExecutor(3,mp_context=get_context('fork')) as pool:
        for arm in pool.map(run,PLANS):print(arm,flush=True)
    daily=pd.concat([pd.read_parquet(CACHE/('daily_'+a+'.parquet')) for a in PLANS])
    daily.to_parquet(OUT/'funded_daily.parquet',index=False)
    # Save actual stock-level net orders with named instruments and source calendar.
    import pyarrow as pa, pyarrow.parquet as pq
    with pq.ParquetWriter(OUT/'net_orders.parquet',schema=pa.schema([('entry_idx',pa.int64()),('symbol_id',pa.int64()),('net_amount',pa.float64()),('fee',pa.float64()),('arm',pa.string()),('segment',pa.string()),('hold',pa.int64())]),compression='zstd') as writer:
        for a in PLANS:writer.write_table(pq.read_table(CACHE/('orders_'+a+'.parquet')))
    pd.Series(M.symbols,name='instrument').to_csv(OUT/'order_symbols.csv',index_label='symbol_id')
    pd.Series(M.days,name='date').to_csv(OUT/'order_calendar.csv',index_label='entry_idx')
