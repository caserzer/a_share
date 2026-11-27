"""Run strict accounts first, then registered phase, fee and valuation sensitivities."""
import tempfile
from engine import *

def main():
    m=load();plans,grades=selections(m)
    daily=[];orders=[];parity=[];h10=[];old_phase=[]
    archived=pd.read_parquet(OUT800/'strict_daily.parquet').query('path=="common" and arm=="R"')
    archived_phase=pd.read_parquet(STORE/'wide_windows.parquet').query('cost=="base"')
    prior= pd.DataFrame(m.planes[1]).ffill().shift().to_numpy()
    original=m.planes[:2]
    for (model,group),plan in plans.items():
        print(model,group,flush=True)
        packed=pack(m,plan)
        for seg,span in enumerate(RANGES,1):
            meta=dict(model=model,bucket=group,segment=seg)
            for phase in ([-1] if group=='pool' else range(-1,10)):
                with tempfile.NamedTemporaryFile() as temp:
                    log=model=='refit' and group!='pool' and phase==-1
                    b=simulate(m,packed,span,phase=phase,orderfile=temp.name if log else None)
                    daily.append(b.assign(**meta,kind='strict',phase=phase))
                    if log:
                        o=pd.read_csv(temp.name,names='entry_idx sleeve id target within net fee blocked'.split())
                        o=o[o.entry_idx<=m.days.get_loc(b.index[-1])].copy()
                        o['instrument']=m.symbols[o.id]
                        o['date']=m.days[o.entry_idx]
                        categories=[]
                        for i,z in o.groupby('entry_idx',sort=False):
                            t=z.id.to_numpy()
                            rg=['ineligible','below_L','runner','head']
                            now=np.array(rg)[grades[i][t]] if i in grades else np.full(len(z),'end')
                            priorgrp=np.array(rg)[grades[i-10][t]] if i-10 in grades else np.full(len(z),'none')
                            same=(i-m.days.get_loc(span[0]))%10==z.sleeve
                            elig_target=(same & (i+10<=m.days.get_loc(span[1])) & (i in plan))
                            tag=np.where(~same,'overdue',np.where(~elig_target,'wind_down',
                                np.where(i-10<m.days.get_loc(span[0]),'initial',np.where((now==group)&(priorgrp==group),'resize',
                                np.where(now==group,'entry',np.char.add('exit_to_',now.astype(str)))))))
                            if group=='decile':
                                tag=np.where(elig_target,np.where(i-10<m.days.get_loc(span[0]),'initial',
                                    np.where(np.isin(now,['head','runner']),np.where(np.isin(priorgrp,['head','runner']),'resize','entry'),np.char.add('exit_to_',now.astype(str)))),tag)
                            categories.extend(tag)
                        o['event']=categories
                        orders.append(o.drop(columns='id').assign(**meta))
                    if phase>=0:
                        # Endpoints are measured before next opening orders; the last day includes liquidation fees.
                        first=m.days.get_loc(span[0])+phase
                        for i in range(first,m.days.get_loc(b.index[-1])-9,10):
                            x=i+10;end=m.days[i+10]
                            finish=b.loc[end,'nav' if end==pd.Timestamp(span[1]) else 'preopen']
                            opening=b.loc[m.days[i],'preopen']
                            h10.append(dict(**meta,phase=phase,entry_idx=i,entry=m.days[i],exit=end,net=finish/opening-1))
            if group in ('head','decile'):
                sz={'head':'same300','decile':'D10'}[group]
                scope='later' if seg==3 else 'primary'
                z=archived.query('mode==@model and size==@sz and scope==@scope').set_index('date')
                b=daily[-(11 if group!='pool' else 1)]
                z=z.reindex(b.index)
                delta=np.max(np.abs(z[['nav','cash','fee','crossed']].values-b[['nav','cash','fee','crossed']].values))
                assert delta<1e-10,(model,group,seg,delta)
                parity.append(dict(**meta,dates=len(z),max_error=delta))
            for kind,cost,netting in [('prenetted',1,False),('zero_fee',0,True),('double_fee',2,True)]:
                b=simulate(m,packed,span,netting=netting,multiplier=cost)
                daily.append(b.assign(**meta,kind=kind,phase=-1))
            if group=='decile':
                # EP38 truncated the first run at the prior complete H10 endpoint,
                # liquidating on June 5. Restart uses the next phase-0 date.
                start,end=span[0],('2023-06-05' if seg==1 else span[1])
                b=simulate(m,packed,(start,end,end),phase=0)
                scope=['primary_prefix','primary_restart','later'][seg-1]
                oldmodel={'refit':'wide_train','transfer':'transfer'}[model]
                ref=archived_phase.query('scope==@scope and model==@oldmodel').set_index('entry_idx')
                for e,r in ref.iterrows():
                    x=e+10; enddate=m.days[x]
                    value=b.loc[enddate,'nav' if enddate==b.index[-1] else 'preopen']/b.loc[m.days[e],'preopen']-1
                    old_phase.append(dict(**meta,entry_idx=e,entry=m.days[e],net=value,archived=r.net,error=value-r.net))
        for name,mul in [('zero_mark',0),('last_mark',1)]:
            m.planes[:2]=[np.ascontiguousarray(np.where(np.isfinite(a),a,prior*mul)) for a in original]
            for seg,(start,end,_) in enumerate([RANGES[0],RANGES[2]],1):
                for phase in ([-1] if group=='pool' else range(-1,10)):
                    daily.append(simulate(m,packed,(start,end,end),phase=phase).assign(model=model,bucket=group,segment=(1,3)[seg-1],kind=name,phase=phase))
            m.planes[:2]=original
    o=pd.concat(orders,ignore_index=True)
    o.to_parquet(RESULT/'orders.parquet',index=False)
    pd.concat(daily).reset_index().to_parquet(RESULT/'daily.parquet',index=False)
    pd.DataFrame(h10).to_parquet(RESULT/'h10.parquet',index=False)
    pd.DataFrame(old_phase).to_csv(RESULT/'ep38_replay.csv',index=False)
    pd.DataFrame(parity).to_csv(RESULT/'ep40_parity.csv',index=False)

if __name__=='__main__':main()
