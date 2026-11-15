"""New L1 baskets from verified stocks, not averaging lower-level index returns.
Engineering source: EP32 extensions/v5_rdagent_onset_forecast/src/data.py.
"""
import pandas as pd
from common import *
from build_panel import price_features, delayed_labels
from evaluate_r01 import scores,bootstrap


def run():
    out=ROOT/'outputs/r05'
    receipt_path=EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json'
    source=json.loads(receipt_path.read_text());reads={str(receipt_path):sha(receipt_path)}
    assignments=CACHE/'extension_v2/products/assignments.parquet';assert sha(assignments)==source['reads'][str(assignments)]
    m=pd.read_parquet(assignments);m=m[m.era.eq('SW2021')&m.level.eq('L2')].copy()
    l2=pd.read_parquet(CACHE/'industry_v1/L2.parquet');l1=pd.read_parquet(CACHE/'industry_v1/L1.parquet')
    parents=l2[['index_code','parent_code']].merge(l1[['industry_code','index_code','industry_name']],left_on='parent_code',right_on='industry_code',suffixes=('_l2','_l1'),validate='many_to_one')
    pmap=parents.set_index('index_code_l2').index_code_l1;names=parents.set_index('index_code_l1').industry_name.to_dict()
    m['child']=m.industry_code;m['industry_code']=m.child.map(pmap);assert m.industry_code.notna().all()
    # An absent child with no resolved members remains a separate catalog gap, never assigned an invented return.
    unresolved=m.groupby(['month','industry_code','child']).unresolved.max().groupby(['month','industry_code']).sum()
    m=m.drop(columns='unresolved').merge(unresolved.rename('unresolved').reset_index(),on=['month','industry_code'],validate='many_to_one')
    assert not m.duplicated(['month','security_id']).any()
    m['level']='L1';m['industry_name']=m.industry_code.map(names)
    m.to_parquet(ROOT/'data/l1_assignments.parquet',index=False)
    bench=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;days=pd.DatetimeIndex(bench.index);month=days.to_period('M')
    anchors=pd.Series(np.arange(len(days)),index=month).groupby(level=0).max();prev=np.array([anchors.get(p-1,-1) for p in month]);safe=np.maximum(prev,0)
    ids=sorted(m.security_id.unique());sid_i={s:i for i,s in enumerate(ids)}
    relative=np.full((len(days),len(ids)),np.nan,dtype=np.float32)
    breadth={h:np.full(relative.shape,np.nan,dtype=np.float32) for h in [21,63]}
    stock_paths={Path(k).stem:Path(k) for k in source['reads'] if '/normalized/prices_qfq/' in k}
    for j,sid in enumerate(ids):
        path=stock_paths[sid];assert sha(path)==source['reads'][str(path)];reads[str(path)]=source['reads'][str(path)]
        f=pd.read_parquet(path,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex(days)
        price=pd.to_numeric(f.qfq_close).where(f.close_conflict.eq(False)&pd.to_numeric(f.qfq_close).gt(0)).to_numpy(float)
        chain=f.factor_chain_id.fillna('__MISSING__').to_numpy();ok=(prev>=0)&(chain==chain[safe])&(chain!='__MISSING__')
        with np.errstate(divide='ignore',invalid='ignore'):
            relative[:,j]=np.where(ok,price/price[safe]-1,np.nan)
            for h in breadth:
                change=price[h:]/price[:-h]-1;valid=np.isfinite(change)&(chain[h:]==chain[:-h])&(chain[h:]!='__MISSING__')
                breadth[h][h:,j]=np.where(valid,(change>0).astype(float),np.nan)
        if (j+1)%1500==0:print('VERIFIED STOCKS',j+1,len(ids),flush=True)
    records=[]
    for code,g in m.groupby('industry_code'):
        prior_end=None;prior_nav=np.nan;pieces=[]
        for mo,mg in g.groupby('month',sort=True):
            ix=np.flatnonzero(month==mo+1)
            if not len(ix) or mo+1<pd.Period('2022-01'):continue
            ai=anchors[mo];si=[sid_i[s] for s in mg.security_id];n=len(si);den=n+int(mg.unresolved.max())
            x=relative[np.ix_(ix,si)];count=np.isfinite(x).sum(axis=1);coverage=count/den
            means=np.divide(np.nansum(x,axis=1),count,out=np.full(len(ix),np.nan),where=count>0)
            scale=prior_nav if prior_end==ai and np.isfinite(prior_nav) else 1.
            nav=scale*(1+means);nav[(coverage<.8)|(n<5)]=np.nan
            f=pd.DataFrame(dict(date=days[ix],nav=nav,coverage=coverage,members=n,membership_asof=days[ai],day_i=ix))
            for h,values in breadth.items():
                v=values[np.ix_(ix,si)];cnt=np.isfinite(v).sum(axis=1)
                f[f'breadth{h}']=np.divide(np.nansum(v,axis=1),cnt,out=np.full(len(ix),np.nan),where=(cnt>=.8*den)&(n>=5))
            if prior_end!=ai or not np.isfinite(prior_nav):
                pieces.append(pd.DataFrame([dict(date=days[ai],nav=1.,coverage=np.nan,members=n,membership_asof=days[ai],day_i=ai)]))
            pieces.append(f);prior_end=ix[-1];prior_nav=nav[-1]
        if not pieces:continue
        f=pd.concat(pieces,ignore_index=True).sort_values('date').drop_duplicates('date');f=f[f.nav.notna()].copy()
        f['block']=f.day_i.diff().ne(1).cumsum();f['era']='SW2021';f['level']='L1';f['industry_code']=code;f['industry_name']=names[code];records.append(f)
    d=pd.concat(records,ignore_index=True);d.to_parquet(ROOT/'data/l1_daily.parquet',index=False)
    ends=pd.Series(days,index=days).groupby(month).max();ends=ends[[p.end_time.normalize()<=days.max() for p in ends.index]]
    parts=[]
    for _,g in d.groupby(KEY+['block']):
        f=delayed_labels(price_features(g),bench);parts.append(f[f.date.isin(ends.values)])
    panel=pd.concat(parts,ignore_index=True);panel['price_ready']=panel[['mom20','mom60','vol20','dd60']].notna().all(axis=1)&panel.coverage.ge(.8)&panel.members.ge(5)
    panel['turn_rank504']=np.nan;panel['pe_rank504']=np.nan
    panel.to_parquet(ROOT/'data/l1_monthly_panel.parquet',index=False)
    rows=[]
    for date,g in panel[panel.price_ready].dropna(subset=['breadth21','breadth63']).groupby('date'):
        if len(g)<20:continue
        sc=scores(g)
        for h in [20,60]:
            y=g[f'excess{h}'];valid=y.notna()
            for method in ['momentum','F','FD']:
                s=sc[method];top=g.assign(score=s).sort_values(['score','industry_code'],ascending=[False,True]).head(6)
                rows.append(dict(date=date,method=method,horizon=h,n_signal=len(g),n_outcome=int(valid.sum()),
                    ic=s[valid].corr(y[valid],method='spearman') if valid.sum()>=20 else np.nan,
                    top6_excess=top[f'excess{h}'].mean() if top[f'excess{h}'].notna().all() else np.nan))
    r=pd.DataFrame(rows);r.to_csv(out/'date_metrics.csv',index=False);inc=[]
    for h,g in r.groupby('horizon'):
        p=g.pivot(index='date',columns='method',values='ic').dropna();x=p.FD-p.F;lo,hi=bootstrap(x)
        yearly=x.groupby(x.index.year).mean()
        inc.append(dict(horizon=h,months=len(x),delta_ic=x.mean(),ci_low=lo,ci_high=hi,
            result='historical_increment_supported' if h==20 and len(x)>=24 and lo>0 and (yearly>0).mean()>=2/3 else 'not_established'))
    pd.DataFrame(inc).to_csv(out/'paired_increments.csv',index=False)
    for path in [assignments,CACHE/'industry_v1/L1.parquet',CACHE/'industry_v1/L2.parquet',ROOT/'src/build_panel.py',EP32/'extensions/v5_rdagent_onset_forecast/src/data.py']:reads[str(path)]=sha(path)
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r05.json'),reads=reads,code_sha256=sha(__file__),stock_partitions=len(ids),
        industries=d.industry_code.nunique(),daily_rows=len(d),panel_rows=len(panel),daily_sha256=sha(ROOT/'data/l1_daily.parquet'),quality='Historical-proxy'))
    print('L1 COMPLETE',len(d),len(panel),inc,flush=True)

if __name__=='__main__':run()
