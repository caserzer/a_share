from accounts_followup import *
sys.path.insert(0,str(ROOT))
from summarize import read,save,interval
from attribution import original
from hashlib import sha256
import subprocess

def main():
    w=original(read('windows'));p=original(read('positions'))
    s=read('daily_scores')
    old=pd.read_parquet(OUT/'rankings.parquet')
    o=original(read('orders'));old_o=pd.read_parquet(OUT/'orders.parquet')
    maxerr=0.
    for a,b in [('R','baseline'),('T','tree_rank')]:
        x=p[p.arm.eq(a)&p.target][['entry_idx','instrument']].sort_values(['entry_idx','instrument']).reset_index(drop=True)
        y=old[old.arm.eq(b)&old.selected][x.columns].sort_values(list(x.columns)).reset_index(drop=True)
        pd.testing.assert_frame_equal(x,y)
        keys=['scope','idx','instrument'];x=o[o.arm==a].set_index(keys).sort_index()
        y=old_o.query('arm==@b and cost=="base"').set_index(keys).sort_index()
        pd.testing.assert_index_equal(x.index,y.index)
        maxerr=max(maxerr,(x.net_amount-y.net_amount).abs().max())
    w=w.sort_values(['scope','arm','entry_idx'])
    w['opening']=w.groupby(['scope','arm']).net.transform(lambda v:(1+v).cumprod().shift(fill_value=1.))
    pos=p.merge(w[['scope','arm','entry_idx','opening']],on=['scope','arm','entry_idx'],validate='m:1')
    hist=industries(s[s.entry_idx.isin(w.entry_idx)].signal_date.unique())
    dmap=s.groupby('entry_idx').signal_date.first()
    pos['day']=pos.entry_idx.map(dmap)
    pos['industry']=pd.concat([g.instrument.map(hist[date]) for date,g in pos.groupby('day')]).fillna('未知')
    for c in ['gross','fee']:pos[c]=100*pos.opening*pos[c]
    pos['net']=pos.gross-pos.fee
    amount=pos.groupby(['scope','arm','instrument','industry'])[['gross','fee','net']].sum().reset_index()
    save('pnl_per_100',amount)
    nav=w.groupby(['scope','arm']).net.apply(lambda v:np.prod(1+v))
    total=amount.groupby(['scope','arm']).net.sum()
    np.testing.assert_allclose(total,100*(nav.loc[total.index]-1),atol=1e-8)
    # Historical monthly contribution of stocks and their contemporary industries.
    deltas=read('calendar_month_stock_delta').reset_index()
    industry_rows=[]
    for (scope,month),g in deltas.groupby(['scope','month']):
        dt=s.loc[s.signal_date.dt.strftime('%Y-%m').eq(month),'signal_date']
        dt=dt.min() if len(dt) else pd.Timestamp(month+'-01')
        names=industries([dt])[dt]
        industry_rows.append(g.assign(industry=g.instrument.map(names).fillna('未知')))
    delta=pd.concat(industry_rows)
    rows=[]
    for (scope,month),g in delta.groupby(['scope','month']):
        for arm in ['X11','B','T','A']:
            for category in ['instrument','industry']:
                v=g.groupby(category)[arm].sum()
                for sign,key in [('positive',v.idxmax()),('negative',v.idxmin())]:
                    rows.append(dict(scope=scope,month=month,arm=arm,level=category,sign=sign,name=key,net_delta_bp=v[key]*1e4))
    save('monthly_extremes',rows)
    matched=[];overlap=[]
    ind=industries(dmap.loc[w.entry_idx.unique()].unique())
    f=s[s.entry_idx.isin(w.entry_idx)]
    for e,g in f.groupby('entry_idx'):
        g=g.assign(industry=g.instrument.map(ind[g.signal_date.iloc[0]]).fillna('未知')).set_index('instrument')
        r=g.R.nlargest(2*(len(g)//10)).index
        for a in ['B','T']:
            pool=r if a=='B' else g.index
            chosen=p[(p.entry_idx==e)&(p.arm==a)&p.target].instrument
            for vol in [True,False]:
                group=g.industry if not vol else g.industry+'|'+np.ceil(g.vol20.rank(pct=True)*3).astype(str)
                for cat,k in group[chosen].value_counts().items():
                    n=group[pool].eq(cat).sum()
                    matched.append(dict(entry_idx=e,arm=a,vol=vol,cell=cat,candidates=n,seats=k,forced=max(0,2*k-n),no_alternative=k if n==k else 0))
        top=p[(p.entry_idx==e)&p.target].groupby('arm').instrument.apply(set)
        for a in ['no_dd','no_amp','no_path','T69','T20','G2']:
            overlap.append(dict(entry_idx=e,arm=a,overlap=len(top[a]&top['T']),seats=len(top[a])))
    save('replica_capacity',matched);save('ablation_overlap',overlap)
    complete=read('months').query('complete and mul==1 and delay==0 and phase==0')
    rows=[]
    for scope,g in complete.groupby('scope'):
        for a in ['B','T','A','X11']:
            allh=g[g.arm.isin([a,'R'])].pivot(index='month',columns=['h','arm'],values='net').dropna()
            for h in [5,10,20]:
                d=(allh[h,a]-allh[h,'R'])*1e4;lo,hi,_=interval(d,3)
                rows.append(dict(scope=scope,arm=a,h=h,n=len(d),bp_month=d.mean(),lo=lo,hi=hi))
    save('horizon_common_months',rows)
    index_raw=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    idx=pd.DataFrame(index_raw['items'],columns=index_raw['fields'])
    sr=idx.set_index(pd.to_datetime(idx.trade_date)).close.sort_index()
    index=sr.groupby(sr.index.to_period('M')).last().pct_change();index.index=index.index.astype(str)
    ci=[]
    for scope,g in complete[complete.h==10].groupby('scope'):
        v=g.pivot(index='month',columns='arm',values='net')
        market=index[v.index].values
        n=len(v);rng=np.random.default_rng(4001)
        boot=(rng.integers(n,size=(10000,(n+2)//3,1))+np.arange(3))%n
        boot=boot.reshape(10000,-1)[:,:n]
        for a in ['T','B','A','X11']:
            y=(v[a]-v.R).values[boot];x=market[boot]
            xm=x.mean(1);ym=y.mean(1)
            beta=((x-xm[:,None])*(y-ym[:,None])).sum(1)/((x-xm[:,None])**2).sum(1)
            alpha=ym-beta*xm
            ci.append(dict(scope=scope,arm=a,n=n,alpha_low=np.quantile(alpha,.025),alpha_high=np.quantile(alpha,.975),beta_low=np.quantile(beta,.025),beta_high=np.quantile(beta,.975)))
    save('regression_ci',ci)
    print('order_max_error',maxerr)
if __name__=='__main__':main()
