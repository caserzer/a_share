"""EP40's funded ten-sleeve account with per-security orders and opening-state replay."""
from dataclasses import dataclass
from inputs import np, pd

@dataclass
class State:
    units: np.ndarray
    due: np.ndarray
    cash: np.ndarray

    @classmethod
    def empty(cls, n):
        return cls(np.zeros((10,n)),np.full((10,n),-1),np.full(10,0.1))

    def copy(self):
        return State(self.units.copy(), self.due.copy(), self.cash.copy())

def step(m, actions, state, start, end, i, plan, mul, detail=False, fixed_ticket=None):
    u,due,cash = state.units,state.due,state.cash
    op,cl = m.marks['flat']
    phase = (i-start)%10
    held = u>0
    if not np.isfinite(op[i,held.any(axis=0)]).all():
        raise ValueError(('missing held open',m.days[i]))
    price = np.nan_to_num(op[i])
    pre = cash + u@price
    orders = np.zeros_like(u)
    expired = held & (due<=i)
    gross_ticket = np.zeros(m.n)
    planned_seat = 0.
    for ph in np.union1d(np.flatnonzero(expired.any(axis=1)),np.array([phase] if plan is not None else [],dtype=int)):
        sold = expired[ph] & m.sell[i]
        sale = u[ph]*price*sold
        kept = held[ph] & ~sold
        purchase = np.zeros(m.n)
        if ph==phase and plan is not None:
            allowed = plan[m.buy[i,plan] & m.members[i-1,plan] & ~kept[plan]]
            fraction = len(allowed)/len(plan)
            available = cash[ph] + sale.sum()*(1-.002*mul)
            scale = min((available+u[ph,kept]@price[kept])/(1+.001*mul*fraction),
                        available/(max(fraction,1e-30)*(1+.001*mul)))
            planned_seat = pre[ph]/len(plan)
            seat = scale/len(plan)
            if fixed_ticket is not None:
                seat = min(seat,fixed_ticket)
                planned_seat = fixed_ticket
            purchase[allowed] = seat
            gross_ticket = purchase
        for old,new,listing in actions:
            if i>=listing and sale[old]:
                sale[new]+=sale[old]
                sale[old]=0.
        orders[ph] = purchase-sale
        u[ph,sold]=0
        due[ph,sold]=-1
        bought = purchase>0
        u[ph,bought]=purchase[bought]/price[bought]
        due[ph,bought]=i+10
    buys=orders.clip(min=0)
    sells=(-orders).clip(min=0)
    bs,ss=buys.sum(axis=0),sells.sum(axis=0)
    crossed=np.minimum(bs,ss)
    fees=mul*(.001*buys*(1-crossed/np.maximum(bs,1e-30))+
              .002*sells*(1-crossed/np.maximum(ss,1e-30)))
    cash -= orders.sum(axis=1)+fees.sum(axis=1)
    assert cash.min()>=-1e-10
    mark=op[i] if i==end else cl[i]
    if not np.isfinite(mark[(u>0).any(axis=0)]).all():
        raise ValueError(('missing held mark',m.days[i]))
    nav = cash.sum()+u.sum(axis=0)@np.nan_to_num(mark)
    row=dict(date=m.days[i],idx=i,nav=nav,pre=pre.sum(),cash=cash.sum(),
             buy=(bs-crossed).sum(),sell=(ss-crossed).sum(),
             fee=fees.sum(),crossed=crossed.sum())
    return row, (orders,fees,gross_ticket,planned_seat,pre[phase]) if detail else None

def funded(m,actions,plans,start,end,mul=1,arm=None,books=None,snapshots=False,policy=None,observer=None):
    state = State.empty(m.n)
    daily,orders,legs,states=[],[],[],{}
    stocks=m.symbols.to_numpy()
    for i in range(start,end+1):
        ph=(i-start)%10
        plan=plans[i] if i+10<=end else None
        if policy is not None and plan is not None:
            plan=policy(i,ph,plan,state)
        if snapshots and ph==0:
            states[i]=state.copy()
        track=books is not None or observer is not None
        if track:
            before=state.units[ph].copy()
        row,info=step(m,actions,state,start,end,i,plan,mul,detail=track)
        daily.append(row)
        if not track:continue
        od,fees,purchases,planned,sleeve=info
        if observer is not None and plan is not None:
            observer(i,ph,plan,state,before,info)
        phases,ids=np.nonzero(od)
        orders.extend((i,p,stocks[j],od[p,j],fees[p,j]) for p,j in zip(phases,ids))
        if plan is not None and arm in ['tree','rank']:
            rank,r,pool,removed,adds,_=books[i]
            candidates=adds if arm=='tree' else pool[:len(adds)]
            for j in candidates:
                legs.append(dict(entry_idx=i,sleeve=ph,instrument=stocks[j],j=j,
                    entry_rank=int(np.flatnonzero(rank==j)[0])+1,
                    planned=planned,bought=purchases[j],net_order=od[ph,j],
                    held_after=state.units[ph,j]*m.marks['flat'][0][i,j]))
        if i-10>=start and arm in ['tree','rank']:
            for a in reversed(legs):
                if a['entry_idx']>i-10:continue
                if a['entry_idx']<i-10:break
                j=a['j']
                if plan is None:
                    a['next_status']='end'
                    continue
                ids,r,*_=books[i]
                a.update(next_status=('eligible' if j in ids else 'ineligible'),
                         promoted=j in r,target_kept=j in plan,held_before=before[j]>0,
                         next_pre_value=before[j]*np.nan_to_num(m.marks['flat'][0][i,j]),
                         next_target_value=planned*(j in plan),
                         actual_continued_value=min(before[j],state.units[ph,j])*np.nan_to_num(m.marks['flat'][0][i,j]),
                         forced_legacy=before[j]>0 and j not in plan and not m.sell[i,j],
                         next_net_order=od[ph,j], next_fee=fees[ph,j])
    return pd.DataFrame(daily),orders,legs,states
