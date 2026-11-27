"""Compare actual net orders and requested capital, using the agents' independent ten-sleeve accounts."""
from summarize import *
from engine import load

def main():
    m=load(False)
    z=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    hits=[];decision=pd.read_parquet(RES/'decision_changes.parquet')
    decision['state']=pd.cut(decision.signal_date.map(z),[-np.inf,1/3,2/3,np.inf],labels=['low','mid','high'])
    v=decision.signal_date.map(z)
    decision.loc[v.eq(1/3)|v.eq(2/3),'state']='mid'
    decision['segment']=np.where(decision.signal_date<'2025-03-03','primary','later')
    decision['changed']=decision.seats-decision.shared
    decision.groupby(['id','arm','base','state','segment'],observed=True)[['changed','seats','base_seats']].sum().to_csv(RES/'seats_by_state.csv')
    oa={}
    def orders(arm):
        if arm not in oa:
            y=pd.read_parquet(RES/'orders'/f'{arm}.parquet')
            # Target is a sleeve-specific plan, net already reflects the stock-level crossing.
            oa[arm]=y.groupby(['segment','entry_idx','instrument'])[['target','net','fee','blocked']].sum()
        return oa[arm]
    for tag,pairs in PAIRS.items():
        for a,b in pairs:
            ax,bx=orders(a).align(orders(b),fill_value=0)
            d=pd.DataFrame({'arm_target':ax.target,'base_target':bx.target,'changed_target_amount':np.abs(ax.target-bx.target)/2,'arm_net_buys':ax.net.clip(lower=0),'base_net_buys':bx.net.clip(lower=0),'changed_broker_buy':abs(ax.net.clip(lower=0)-bx.net.clip(lower=0))/2,'arm_blocked':ax.blocked,'base_blocked':bx.blocked,'actual_fee_difference':ax.fee-bx.fee})
            day=d.groupby(['segment','entry_idx']).sum().reset_index()
            day['date']=m.days[day.entry_idx.to_numpy()]
            hits.append(day.assign(id=tag,arm=a,base=b))
    atomic_parquet(pd.concat(hits,ignore_index=True),RES/'decision_capital.parquet')
if __name__=='__main__':main()
