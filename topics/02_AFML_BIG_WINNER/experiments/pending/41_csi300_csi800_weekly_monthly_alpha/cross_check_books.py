"""Cross-check both primary tests with U2's independently implemented funded book."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'u2'))
from common import Study, PERIODS, PRIMARY, REG, monthly, np, pd
checks=[]
s=Study()
p1={b:s.blank() for b in ['head','runner']}
for e,g in s.ranks.groupby('entry_idx'):
    ids=s.symbols.get_indexer(g.instrument);k=s.ks[e];l=len(g)//10
    for arm,ids2 in [('head',ids[:k]),('runner',ids[k:l])]:p1[arm][e,:len(ids2)]=ids2
p2={b:s.blank() for b in ['tree','rank']}
for e,g in pd.read_parquet(REG/'p2/results/scores.parquet').groupby('entry_idx'):
    z=g.sort_values(['R','instrument'],ascending=False)
    ids=s.symbols.get_indexer(z.instrument)
    tree=ids[np.lexsort((-ids,-z['T'].to_numpy()))];k=len(g)//10;n=k//5
    head=ids[:k];pool=ids[k:2*k];tr=head[~np.isin(head,tree[np.isin(tree,head)][-n:])]
    p2['tree'][e,:k]=np.r_[tr,tree[np.isin(tree,pool)][:n]]
    p2['rank'][e,:k]=np.r_[tr,pool[:n]]
for test,plans,periods in [('P1',p1,PERIODS),('P2',p2,{'primary':PRIMARY,'later':PERIODS['later']})]:
    if test=='P1':
        ref=pd.read_parquet(REG/'p1/results/daily.parquet').query('model=="refit" and kind=="strict" and phase==-1').rename(columns={'bucket':'arm'})
        ref.segment=ref.segment.map({1:'prefix',2:'restart',3:'later'})
        o=pd.read_parquet(REG/'p1/results/broker_orders.parquet');o.segment=o.segment.map({1:'prefix',2:'restart',3:'later'});o=o.rename(columns={'bucket':'arm'})
    else:
        ref=pd.read_parquet(REG/'p2/results/funded_daily.parquet').query('mul==1').rename(columns={'scope':'segment'})
        o=pd.read_parquet(REG/'p2/results/orders.parquet').rename(columns={'scope':'segment','order':'net'});o['date']=s.days[o.idx]
        o=o.groupby(['segment','arm','date','instrument'],as_index=False).net.sum()
        s.valid_buy=np.ascontiguousarray(s.m.buy&np.roll(s.narrow,1,axis=0),np.uint8)
    paid=np.maximum(o.net,0)*.001+np.maximum(-o.net,0)*.002
    ob=paid.groupby([o.segment,o.arm,o.date]).sum()
    months=[]
    for stage,period in periods.items():
        for arm,plan in plans.items():
            daily,_,gap=s.replay(plan,period)
            assert not gap
            src=ref[(ref.arm==arm)&(ref.segment==stage)].set_index('date').loc[daily.index]
            eps=(src[['nav','cash','fee','crossed']]-daily[['nav','cash','fee','crossed']]).abs().to_numpy().max()
            assert eps<1e-10,(test,stage,arm,eps)
            err=(ob.loc[(stage,arm)].reindex(daily.index,fill_value=0)-daily.fee).abs().max()
            assert err<1e-10,err
            mx=monthly(daily,s.days)
            mx=mx[mx.index>str(daily.index[0].to_period('M'))]
            for month,v in mx.items():months.append((stage,arm,month,v))
            checks.append(dict(test=test,segment=stage,arm=arm,days=len(daily),start=daily.index[0],end=daily.index[-1],max_state_error=eps,max_fee_error=err))
    mo=pd.DataFrame(months,columns=['segment','arm','month','net']).pivot(index=['segment','month'],columns='arm',values='net')
    a,b=list(plans);print(test,len(mo), (mo[a]-mo[b]).mean()*1e4,flush=True)

pd.DataFrame(checks).to_csv(REG/'primary_book_parity.csv',index=False)
