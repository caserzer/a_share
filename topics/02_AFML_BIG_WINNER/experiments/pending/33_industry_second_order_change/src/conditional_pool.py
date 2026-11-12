"""R10: predeclared finite decomposition, no threshold fitting."""
import json
import numpy as np
import pandas as pd
from pool_evaluation import EP,KEY,HORIZONS,sha,evaluate,calendar_dates,block_ci

def main():
    out=EP/'outputs/r10';p=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet').sort_values(KEY+['date'])
    p['negative']=p.rate20.lt(0);p['nonnegative']=p.rate20.ge(0);p['all_eligible']=p.eligible
    p['market_up']=p.market126.gt(0);p['market_nonup']=p.market126.le(0)
    selection={};turns=[]
    for regime in ['up','nonup']:
        for cond in ['all_eligible','negative','slowdown','pressure_easing','nonnegative','improvement_acceleration']:
            name=regime+'__'+cond;p[name]=p.eligible&p['market_'+regime]&p[cond]
            prev=p.groupby(KEY)[name].shift();cont=p.week_i.sub(p.groupby(KEY).week_i.shift()).eq(1)
            # True branch boundary on a change in unavailable source is not a known entry.
            entry=p[name]&prev.eq(False)&cont
            p[name+'_boundary']=p[name]&~cont
            selection[name,'state']=p.index[p[name]];selection[name,'entry']=p.index[entry]
            market_changed=p['market_'+regime]&p.groupby(KEY)['market_'+regime].shift().eq(False)&cont
            turns.append(dict(method=name,entries=int(entry.sum()),market_change_entries=int((entry&market_changed).sum())))
    s=evaluate(p,selection,out);pd.DataFrame(turns).to_csv(out/'entry_triggers.csv',index=False)
    q=p[p.eligible].copy();q['sign']=np.where(q.rate20.lt(0),'negative','nonnegative')
    q['bin']=np.minimum(4,((q.groupby(['date','sign']).rate20.rank(method='average')-1)/q.groupby(['date','sign']).rate20.transform('size')*5).astype(int))
    conditional=[];annual=[];rows=[];dates=calendar_dates()
    for h in HORIZONS:
        col=f'win{h}';q['peer']=q.groupby(['date','sign','bin'])[col].transform('mean')
        for (method,unit),ids in selection.items():
            z=q.loc[q.index.intersection(ids)].copy();z['delta']=z[col]-z.peer
            weekly=z.groupby('date').delta.mean().reindex(dates);lo,hi=block_ci(weekly,round(h/5),3310)
            conditional.append(dict(method=method,unit=unit,horizon=h,total=len(z),known=z[col].count(),paired=z.delta.count(),delta=weekly.mean(),lo=lo,hi=hi))
            for year,g in z.groupby(z.date.dt.year):
                annual.append(dict(method=method,unit=unit,horizon=h,year=int(year),known=g.delta.count(),delta=g.groupby('date').delta.mean().mean()))
            rows.append(pd.DataFrame({'row_id':z.index,'method':method,'unit':unit,'horizon':h,'peer_rate':z.peer,'delta':z.delta}))
    pd.DataFrame(conditional).to_csv(out/'conditional_summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'conditional_annual.csv',index=False)
    pd.concat(rows,ignore_index=True).to_csv(out/'conditional_pairs.csv.gz',index=False)
    inputs=[EP/'outputs/r09/evaluation_panel.parquet',EP/'rounds/r09_reflection.md',EP/'rounds/r10_conditional_pool_plan.md',EP/'src/pool_evaluation.py',__file__]
    (out/'receipt.json').write_text(json.dumps({'status':'EXECUTED_EXPLORATORY','inputs':{str(f):sha(f) for f in inputs},'no_parameter_search':True,'rules':12,'units':['state','entry'],'horizons':HORIZONS},indent=2)+'\n')
    print(s[s.unit.eq('state')&s.horizon.eq(126)][['method','total','known','pooled_win_rate','paired_all_delta','mean_pool','success_week_recall']].to_string(index=False))
    print(pd.DataFrame(conditional).query('unit=="state" and horizon==126').to_string(index=False))
if __name__=='__main__':main()
