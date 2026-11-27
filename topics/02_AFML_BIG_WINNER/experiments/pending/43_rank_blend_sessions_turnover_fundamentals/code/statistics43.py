from accounts43 import *
from engine import STORE
import json
SUM=O/'summary';SUM.mkdir(exist_ok=True)
def bootstrap(parts):
    rng=np.random.default_rng(4301);draw=np.zeros(10000);center=np.zeros(10000);n=sum(map(len,parts))
    for v in parts:
        l=len(v);b=min(3,l);start=rng.integers(l-b+1,size=(10000,(l+b-1)//b));xx=v[(start[:,:,None]+np.arange(b)).reshape(10000,-1)[:,:l]]
        draw+=xx.sum(axis=1);center+=(xx-v.mean()).sum(axis=1)
    total=np.concatenate(parts).mean();lo,hi=np.percentile(draw/n,[2.5,97.5])
    return total,lo,hi,(1+sum(center/n>=total))/(10001)
def summarize():
    ms=[];details=[];annual=[]
    ix=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data'];z=pd.DataFrame(ix['items'],columns=ix['fields'])
    idx300=z.set_index(pd.to_datetime(z.trade_date)).close;z=pd.read_parquet(STORE/'index800.parquet');idx800=z.set_index(pd.to_datetime(z.trade_date)).close
    eq300=pd.read_parquet(EP41/'p2/results/funded_daily.parquet',filters=[('arm','=','equal'),('mul','=',1)]);eq300['segment']=eq300.scope.map({'primary':1,'later':2})
    eq800=pd.read_parquet(EP41/'p1/results/daily.parquet',filters=[('kind','=','strict'),('phase','=',-1),('model','=','refit'),('bucket','=','pool')])
    for marker in sorted((O/'accounts').glob('*/*/*/done')):
        dest=marker.parent;pool=int(dest.parents[1].name);arm=dest.parent.name+'/'+dest.name
        mo=pd.read_csv(dest/'monthly.csv');ms.append(mo.assign(pool=pool,arm=arm))
        dt=pd.read_csv(dest/'detail.csv');details.append(dt.assign(pool=pool,arm=arm))
        daily=pd.read_parquet(dest/'daily.parquet')
        idx=idx300 if pool==300 else idx800;eq=eq300 if pool==300 else eq800
        for (sg,fee),g in daily.groupby(['segment','multiple']):
            g=g.set_index('date');prior=g.nav.shift(fill_value=1.)
            equal=eq[eq.segment==sg].set_index('date').nav
            for scope,df in [('whole',g),('equal_common',g.loc[:equal.index.max()])]:
                for y,sub in [('all',df),*df.groupby(df.index.year)]:
                    start,end=sub.index[[0,-1]];t=g.index.get_loc(start);prior_day=g.index[t-1] if t else start
                    ret=sub.nav.iloc[-1]/prior.at[start]-1;idxret=idx.at[end]/idx.at[prior_day]-1
                    eqret=(equal.at[end]/(equal.at[prior_day] if t else 1)-1) if end in equal.index and prior_day in equal.index else np.nan
                    dd=(sub.nav/sub.nav.cummax().clip(lower=prior.at[start])-1).min()
                    annual.append((pool,arm,sg,fee,scope,y,start,end,ret,idxret,eqret,ret-idxret,ret-eqret,dd,sub.fee.sum()/prior.at[start],(sub.buy+sub.sell).sum()/prior.at[start]))
    pd.DataFrame(annual,columns='pool arm segment multiple window year start end net index equal_1fee excess_index excess_equal_1fee drawdown fee turnover'.split()).to_csv(SUM/'annual.csv',index=False)
    pd.concat(details,ignore_index=True).to_csv(SUM/'details.csv',index=False)
    m=pd.concat(ms,ignore_index=True);m.to_parquet(SUM/'monthly.parquet',index=False)
    stats=[]
    def run(pool,tags,label,coef):
        nonlocal m
        ss=m[m.pool.eq(pool)&m.arm.isin(tags)]
        if len(set(ss.arm))!=len(tags):return
        for fee,group in ss.groupby('multiple'):
            cols=['net','gross','fee','turnover'];pv=group.pivot(index=['segment','month'],columns='arm',values=cols)
            pairs=sum(v*pv.xs(tag,axis=1,level=1) for tag,v in zip(tags,coef)).dropna()*1e4
            for seg,g in [('all',pairs),*pairs.groupby(level=0)]:
                parts=[h.net.to_numpy() for _,h in g.groupby(level=0)]
                if not parts:continue
                point,lo,hi,p=bootstrap(parts)
                drop=np.concatenate([np.sort(v)[:-3] for v in parts if len(v)>3]).mean() if any(len(v)>3 for v in parts) else np.nan
                stats.append((pool,label,' | '.join(tags),str(seg),fee,len(g),point,lo,hi,p,drop,g.gross.mean(),g.fee.mean(),g.turnover.mean()))
    for pool in [300,800]:
        for family,arms,base in [('B',['B','D','T','T_mask_trading','T69','T60','T69d','T60d','fixed175','fixed175_buf'],'W/R'),('W',['buf','K40','LP','QP','mechanical','capK','cap5','cap6','LP6','tau005','tau02','head','buf_head','LP_head'],'W/R'),('L',['cal_over','eq_over','over','intra','total','eq_treeover','cal_treeover','tree_total','treeover'],'W/R'),('Fproxy',['neutral','raw','residual','missing','value','quality','EP','BM','ROE','stable','cashprofit','gmchange','lock'],'W/R'),('Fgate',['gate','price','hash','dd','pos'],'W/R'),('Fstrict_raw',['raw','EP','BM','ROE','stable','cashprofit','gmchange'],'W/R'),('Fstrict',['neutral','raw','residual','missing','gate','EP','BM','ROE','stable','cashprofit','gmchange'],'W/R')]:
            for a in arms:run(pool,[family+'/'+a,base],family+'/'+a+' minus '+base,[1,-1])
        for a,b in [('B_A4_head/T_mask_trading','B_A4_head/T'),('B/D','W/buf'),('B/D','B/B'),('B/T60d','B/T69'),('B/T69d','B/T69'),('B/T60','B/T69'),('B/T_mask_trading','B/T'),('L/cal_over','L/total'),('L/cal_over','L/eq_over'),('L/eq_over','L/total'),('L/cal_treeover','L/cal_over'),('L/eq_treeover','L/eq_over'),('W/LP','W/buf'),('W/LP','W/cap5'),('W/QP','W/LP'),('W/mechanical','W/LP'),('W/LP','W/K40'),('Fcommon/neutral','Fcommon/R'),('Fgate/gate','Fgate/hash'),('Fgate/gate','Fgate/price')]:
            run(pool,[a,b],a+' minus '+b,[1,-1])
        run(pool,['B/D','W/buf','B/B','W/R'],'B interaction',[1,-1,-1,1])
        run(pool,['B/T60d','B/T69d','B/T60','B/T69'],'B tree interaction',[1,-1,-1,1])
        for fam in ['transfer','transfer_head','native300b']:
            for a,b in [('D','A'),('B','A'),('C','A'),('D','C'),('D','B')]:run(pool,[fam+'/'+a,fam+'/'+b],fam+' '+a+'-'+b,[1,-1])
            run(pool,[fam+'/'+a for a in 'DCBA'],fam+' interaction',[1,-1,-1,1])
    ret=pd.DataFrame(stats,columns='pool comparison arms segment multiple months net_bp lo hi p_one drop3 gross_bp delta_fee_bp turnover_bp'.split());ret.to_csv(SUM/'contrasts.csv',index=False)
    primary=[]
    for name,pool,tag in [('B2',300,'B/D minus W/R'),('L3',300,'L/cal_over minus L/total'),('W3',800,'W/LP minus W/buf'),('F4',800,'Fstrict/neutral minus W/R')]:
        row=ret[(ret.pool==pool)&(ret.comparison==tag)&(ret.segment=='all')&(ret.multiple==1)]
        primary.append(dict(item=name,pool=pool,comparison=tag,**(row[['months','net_bp','lo','hi','p_one','drop3']].iloc[0].to_dict() if len(row) else dict(p_one=1.))))
    primary=pd.DataFrame(primary);ix=primary.sort_values('p_one').index
    primary.loc[ix,'p_holm']=np.minimum(1,np.maximum.accumulate(primary.loc[ix,'p_one'].values*np.arange(4,0,-1)))
    primary.to_csv(SUM/'primary.csv',index=False)
if __name__=='__main__':summarize()
