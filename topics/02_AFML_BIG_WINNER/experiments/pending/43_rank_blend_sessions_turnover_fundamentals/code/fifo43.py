from collections import defaultdict,deque
import numpy as np
import pandas as pd
def allocate(c,m,span):
    op=m.planes[0];buy,sell=m.planes[2:4];lo,hi,stop=m.days.get_indexer(pd.to_datetime(span))
    actions={int(s):(int(d),int(day)) for s,d,day in m.planes[-1]};fifo=defaultdict(deque)
    records=[];due={};purchases=defaultdict(list)
    for i,g in c.groupby('day',sort=True):
        order={(int(r.phase),int(r.stock)):[r.old_units,r.new_units,r.fee,r.target] for r in g.itertuples(index=False)}
        for (p,j),z in list(order.items()):
            if j not in actions or i<actions[j][1] or not(z[0]>0 and z[1]==0):continue
            dest=actions[j][0];ratio=op[i,j]/op[i,dest]
            queue=fifo.pop((p,j),[]);fifo[p,dest].extend((d,n*ratio,px/ratio,bf/ratio) for d,n,px,bf in queue)
            fifo[p,dest]=deque(sorted(fifo[p,dest],key=lambda lot:lot[0]))
            if (p,j) in due:due[p,dest]=min(due.get((p,dest),i),due.pop((p,j)))
            state=order.setdefault((p,dest),[0.,0.,0.,0.]);state[0]+=z[0]*ratio;z[0]=0
        for (p,j),(old,new,fee,target) in order.items():
            dq=new-old;price=op[i,j];q=fifo[p,j];was_due=due.get((p,j),i)
            if dq>0:
                q.append((i,dq,price,fee/dq));purchases[p,j].append(i)
            elif dq<0:
                left=-dq;sf=fee/left
                while left>1e-21 and q:
                    born,n,px,bf=q.popleft();a=min(n,left);left-=a
                    records.append((born,i,p,j,i-born,px*a,price*a,bf*a,sf*a,i>hi-10,False,was_due<i,a,px,price))
                    if n>a:q.appendleft((born,n-a,px,bf))
                assert left*price<2e-9,(i,p,j,left,price)
            elif fee>1e-12:raise ValueError(('fee_without_change',i,j,fee))
            if new==0:due.pop((p,j),None)
            elif target>0 and buy[i,j] and (old==0 or (was_due<=i and sell[i,j])):due[p,j]=i+10
    for (p,j),q in fifo.items():
        for born,n,px,bf in q:records.append((born,stop,p,j,stop-born,n*px,0.,n*bf,0.,False,True,False,n,px,np.nan))
    out=pd.DataFrame(records,columns='born exit sleeve stock age principal proceeds buy_fee sell_fee settlement still_open delayed_exit shares adjusted_buy_price adjusted_sell_price'.split())
    out['rebought_next_H10']=False
    for k,ix in out.groupby(['sleeve','stock']).indices.items():
        days=np.asarray(purchases[k]+[10**8]);ex=out.exit.values[ix];out.loc[ix,'rebought_next_H10']=days[np.searchsorted(days,ex,side='right')]-ex<=10
    return out
