"""Ten-sleeve books and common-cash one-H10 ledgers using the EP41 checked C++ engine."""
import tempfile
from scale_common import *
sys.path.insert(0,str(EP41/'p1'))
from engine import load, pack, simulate, COLS as BOOK_COLS

def ranked_plans(m,f,arm,mask=None):
    cols=['entry_idx','instrument',arm]+([mask] if mask else [])
    x=f[cols].copy()
    denom=(x.groupby('entry_idx').size()//10).to_dict()
    if mask:x=x[x[mask]]
    x=x.sort_values(['entry_idx',arm,'instrument'],ascending=[True,False,False])
    ix=x.groupby('entry_idx').cumcount()<x.entry_idx.map(denom)
    x=x.loc[ix].copy()
    x['id']=m.symbols.get_indexer(x.instrument)
    assert (x.id>=0).all()
    picked=x.groupby('entry_idx',sort=False).id.agg(list).to_dict()
    return {i:picked.get(i,[]) for i in denom},denom

def single_periods(m,packed,seg,start,end):
    targets,den=packed;arr=np.empty((11,len(BOOK_COLS)),np.float64)
    args=[a.ctypes.data for a in [targets,den,*m.planes]]
    records=[]
    a,b=m.days.get_indexer(pd.to_datetime([start,end]))
    for i in range(a,b-9):
        if den[i]==0:continue
        result=m.kernel(m.n,i,i+10,i+10,targets.shape[1],*args,len(m.planes[-1]),0,True,.001,.002,arr.ctypes.data,b'')
        if result!=i+11:
            records.append((m.days[i-1],i,(i-a)%10,np.nan,np.nan,np.nan,np.nan));continue
        net=arr[-1,0]-1;fee=arr[:,2].sum()
        records.append((m.days[i-1],i,(i-a)%10,net,net+fee,fee,arr[:,4].sum()))
    return pd.DataFrame(records,columns='signal_date entry_idx offset net gross fee actual_buy'.split()).assign(segment=seg)

def main():
    m=load(False)
    plans={}
    for name in ['model_scores','shallow_early','G3_scores','scale_scores']:
        f=pd.read_parquet(RES/(name+'.parquet'))
        cols=[a for a in f if a not in KEY+['entry_idx','all_support','main_support']]
        for c in cols:plans[c]=ranked_plans(m,f,c)
        if name=='scale_scores':
            for c in [c for c in cols if c.startswith('vol_')]:
                plans[c+'_supported']=ranked_plans(m,f,c,'all_support')
        del f
    styles=pd.read_parquet(RES/'S5_targets.parquet')
    for arm,g in styles.groupby('arm'):
        plans[arm]=({r.entry_idx:m.symbols.get_indexer(r.instruments) for r in g.itertuples()},g.set_index('entry_idx').denominator.to_dict())
    target_rows=[];single=[];daily=[];annual=[];summ=[];check=[]
    orders_dir=RES/'orders';orders_dir.mkdir(exist_ok=True)
    for arm,(selected,den) in plans.items():
        target_rows.extend((i,m.days[i-1],arm,den[i],m.symbols[np.asarray(ids,dtype=int)].tolist()) for i,ids in selected.items())
        packed=pack(m,selected,den)
        files=[]
        for seg,ds,de in SEG:
            for cost in [1,2]:
                with tempfile.NamedTemporaryFile() as tmp:
                    d=simulate(m,packed,(ds,de,de),multiplier=cost,orderfile=tmp.name if cost==1 else None)
                    if cost==1:
                        order=pd.read_csv(tmp.name,names='entry_idx sleeve id target within net fee blocked'.split())
                        order=order[order.entry_idx<=m.days.get_loc(d.index[-1])].copy()
                        order['instrument']=m.symbols[order.id];order['segment']=seg
                        files.append(order.drop(columns='id'))
                        assert abs(d.fee.sum()-order.fee.sum())<1e-10
                # Strict stops, if any, are recorded at their actual endpoints.
                d=d.reset_index().assign(arm=arm,segment=seg,fee_multiple=cost)
                d['prev']=d.nav.shift(fill_value=1.)
                assert abs(d.nav-d.prev-d.gross_pnl+d.fee).max()<1e-12
                daily.append(d)
                for y,chunk in d.groupby(d.date.dt.year):
                    annual.append((arm,seg,cost,y,chunk.date.iloc[0],chunk.date.iloc[-1],chunk.nav.iloc[-1]/chunk.prev.iloc[0]-1))
                for mo,chunk in d.groupby(d.date.dt.to_period('M')):
                    if mo in [d.date.iloc[0].to_period('M'),d.date.iloc[-1].to_period('M')]:continue
                    nav0=chunk.prev.iloc[0]
                    summ.append((arm,seg,cost,str(mo),chunk.nav.iloc[-1]/nav0-1,chunk.gross_pnl.sum()/nav0,
                                 chunk.fee.sum()/nav0,chunk.buy.sum()/nav0,chunk.sell.sum()/nav0,chunk.blocked_budget.sum()/nav0))
                check.append((arm,seg,cost,d.date.iloc[-1],len(d),d.nav.iloc[-1]-1,(d.nav/d.nav.cummax().clip(lower=1)-1).min()))
            if arm in ['ridge69','ridge78','S2_A','original78tree','mse69','mse78','shallow','early','shallow_early','vol_live','vol_fixed','sector_live','sector_fixed','paired_live','paired_fixed','G3_main','G3_interaction','vol_lag20']:
                single.append(single_periods(m,packed,seg,ds,de).assign(arm=arm))
        atomic_parquet(pd.concat(files),orders_dir/(arm+'.parquet'))
        print(arm,flush=True)
    atomic_parquet(pd.DataFrame(target_rows,columns='entry_idx signal_date arm denominator instruments'.split()),RES/'target_lists.parquet')
    d=pd.concat(daily,ignore_index=True);atomic_parquet(d,RES/'daily.parquet')
    ref=pd.read_parquet(EP41/'models/results/funded_daily.parquet',filters=[('hold','=',10)],columns=['segment','date','arm','nav','cash','fee','crossed'])
    errors=[]
    for arm,base in [('R','R'),('S2_A','top_M1_raw'),('original78tree','top_T')]:
        g=d.query('arm==@arm and fee_multiple==1').merge(ref.query('arm==@base'),on=['segment','date'],validate='1:1',suffixes=('','_ref'))
        assert len(g)==len(ref.query('arm==@base'))
        for f in ['nav','cash','fee','crossed']:
            delta=abs(g[f]-g[f+'_ref']).max();assert delta<1e-10,(arm,f,delta)
            errors.append((arm,f,delta))
    pd.DataFrame(errors,columns='arm field max_absolute_error'.split()).to_csv(RES/'book_parity.csv',index=False)
    pd.DataFrame(annual,columns='arm segment fee_multiple year start end net'.split()).to_csv(RES/'annual.csv',index=False)
    pd.DataFrame(summ,columns='arm segment fee_multiple month net gross fee buy sell denied'.split()).to_csv(RES/'months.csv',index=False)
    pd.DataFrame(check,columns='arm segment fee_multiple actual_end sessions cumulative maxdd'.split()).to_csv(RES/'paths.csv',index=False)
    atomic_parquet(pd.concat(single),RES/'common_h10.parquet')
if __name__=='__main__':main()
