"""Reachable alternatives, path bands, foreknown notices and realized tail events."""
import ctypes as ct
import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score
import replay as rp
from sources import OUT,PRIVATE,OLD

def metrics(g,event,pred):
    a=g[[event,pred]].dropna()
    if not len(a):return dict(n=0,events=0,auc=np.nan,brier=np.nan,ece=np.nan)
    y=a[event];v=a[pred];b=np.digitize(v,[.02,.05,.1,.2,.5])
    auc=roc_auc_score(y,v) if y.nunique()>1 else np.nan
    return dict(n=len(y),events=int(y.sum()),auc=auc,brier=np.mean((v-y)**2),ece=sum(abs((v-y)[b==k].sum()) for k in np.unique(b))/len(y))
def main():
    rp.inputs();m=rp.M;cov=pd.read_parquet(OUT/'covariates.parquet')
    d=pd.read_parquet(OUT/'dual_scores.parquet')
    inner=pd.read_parquet(OUT/'dual_weekly.parquet')
    lookup=cov.set_index(['entry_idx','instrument'])
    holdings=[];buffers=[];support=[]; exposures=[]
    for scope,(lo,hi) in rp.SEG.items():
        for spec in rp.direct():
            key=spec[0]
            want=spec[1] in [0,2] or key in ['SellTree','N2','Safe','Announced','Combo']
            if not want:continue
            pre=np.zeros((rp.ROWS,m.n))
            rp.LIB.capture_inventory.argtypes=[ct.c_void_p];rp.LIB.capture_inventory(pre.ctypes.data)
            _,logs,values=rp.runone(spec,scope)
            rp.LIB.capture_inventory(None)
            if key=='Ridge':
                for i in range(lo,hi-9):
                    top=rp.RANK[i,:rp.DEN[i]]
                    for j in top[pre[i,top]<=0]:holdings.append((scope,i,m.symbols[j]))
            if spec[1]==2:
                for i in range(lo,hi-9):
                    rank=rp.RANK[i]; r=spec[2] or rp.DEN[i]
                    band=rank[r:spec[3]]; actual=band[pre[i,band]>0]
                    removed=set(logs[i,1:1+logs[i,0]])
                    dst=set(logs[i,130:130+logs[i,129]])
                    for j in actual:
                        excess=rp.F[rp.FIELDS.index('past_excess10'),i,j]
                        status='released' if j in removed else ('retained' if j in dst else 'other')
                        category='unknown' if not np.isfinite(excess) else ('flat' if abs(excess)<=.02 else ('up' if excess>0 else 'down'))
                        buffers.append((scope,key,i,m.symbols[j],status,category,pre[i,j],values[i,0],excess))
            if key in ['N2','Safe','Announced','Combo']:
                for i in range(lo,hi-9):
                    k=rp.DEN[i];rank=rp.RANK[i];orig=rp.ORIG[scope][i]
                    top=rank[k:k+3 if key=='Combo' else 2*k];top=top[(orig[top]==0)&(pre[i,top]==0)]
                    cap=rp.F[rp.FIELDS.index('riskcap'),i,top];adv=rp.F[rp.FIELDS.index('riskadv'),i,top]
                    announced=rp.F[rp.FIELDS.index('announced'),i,top]>.5
                    support.append((scope,key,i,len(top),(~np.isfinite(cap)|~np.isfinite(adv)).sum(),((cap<=.1)&(adv<=.1)).sum(),announced.sum()))
            if key=='SellTree':
                for i in range(lo,hi-9):
                    top=rp.RANK[i,:rp.DEN[i]];rm=logs[i,1:1+logs[i,0]]
                    support_row=pre[i,rm]
                    exposures.extend((scope,i,m.symbols[j],pre[i,j],values[i,0]) for j in rm)
    s=pd.DataFrame(support,columns='scope arm entry_idx available missing_style flagged_cap180 flagged_announced'.split());s.to_parquet(OUT/'risk_opportunities.parquet',index=False)
    ex=pd.DataFrame(exposures,columns='scope entry_idx instrument pre_position proposed_ticket'.split())
    o=pd.concat([pd.read_parquet(OUT/'books'/scope/'SellTree'/'orders.parquet').query('sleeve==(entry_idx-@lo)%10').assign(scope=scope) for scope,(lo,hi) in rp.SEG.items()])
    ex=ex.merge(o[['scope','entry_idx','instrument','net','broker','fee','blocked']],how='left')
    ex['execution']=np.select([ex.net.lt(-1e-12),ex.pre_position.le(1e-12),ex.blocked.gt(1e-12)],['sold','cancel_new_buy','blocked'],default='carry_or_netted')
    ex['actual_mass']=ex.broker.abs()
    ex.to_parquet(OUT/'seller_execution.parquet',index=False)
    b=pd.DataFrame(buffers,columns='scope arm entry_idx instrument status category pre_mark ticket trailing_excess'.split())
    b=b.merge(lookup[['h10']].reset_index(),on=['entry_idx','instrument'])
    b['ticket_gross_opportunity']=b.ticket*b.h10;b['available_h10_capital']=b.ticket.where(b.h10.notna())
    b.to_parquet(OUT/'buffer_paths.parquet',index=False)
    b.groupby(['scope','arm','category','status']).agg(seats=('instrument','size'),pre=('pre_mark','sum'),gross_opportunity=('ticket_gross_opportunity','sum'),known_capital=('available_h10_capital','sum')).to_csv(OUT/'buffer_path_summary.csv')
    n=pd.DataFrame(holdings,columns='scope entry_idx instrument'.split());test=n.merge(d,on=['entry_idx','instrument'],validate='1:1');test['q']=test.signal_date.dt.to_period('Q').astype(str)
    flags=test[['signal_date','instrument','q']]
    mature=inner.merge(flags[['signal_date','instrument']],on=['signal_date','instrument'])
    calib=[]
    for quarter,g in test.groupby('q'):
        for sample,obs in [('outer_realized',g),('inner_known_since_first_account',mature[mature.m10.lt(pd.Period(quarter,'Q').start_time)])]:
            for event,pred in [('event','risk' if sample=='outer_realized' else 'tail'),('right','rtail')]:
                calib.append(dict(quarter=quarter,sample=sample,tail=event,**metrics(obs,event,pred)))
    pd.DataFrame(calib).to_csv(OUT/'natural_tail_calibration.csv',index=False)
    mem=pd.read_parquet(PRIVATE/'daily_members.parquet').astype(bool)
    ch=mem.shift(fill_value=False)&~mem
    dep=pd.read_csv(OUT/'known_departures.csv',dtype={'code':str},parse_dates=['effective'])
    dr=[]
    for dt,z in ch.loc['2021-01-11':'2026-09-30'].iterrows():
        names=set(x[2:] for x in z[z].index)
        for name in names:
            u=dep[dep.code.eq(name)]
            dr.append((dt,name,(u.effective==dt).any(),(u.effective.sub(dt).abs().dt.days<=7).any()))
    pd.DataFrame(dr,columns='observed_date code exact_notice within_week'.split()).to_csv(OUT/'member_notice_audit.csv',index=False)
    print('natural scored',len(test),'index changes',len(dr),'matched',sum(r[2] for r in dr),flush=True)
if __name__=='__main__':main()
