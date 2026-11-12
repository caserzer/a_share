"""R11 independent information domain, same-coverage controls."""
import json
import numpy as np
import pandas as pd
from pool_evaluation import EP,KEY,HORIZONS,sha,evaluate,calendar_dates,block_ci

def main():
    root=EP/'outputs/r11';root.mkdir(parents=True,exist_ok=True)
    p=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet')
    f=pd.read_csv(EP/'outputs/r04/industry_coverage.csv.gz',parse_dates=['date'])
    p=p.reset_index().merge(f,on=['date','era','industry_code'],how='left',validate='one_to_one').set_index('row_id').sort_values(KEY+['date'])
    p['price_eligible']=p.eligible
    coverage=[];conditional=[];annual=[];pairinfo=[];entries=[]
    for minimum in [.3,.5]:
        threshold=f'coverage{int(minimum*100)}';out=root/threshold;q=p.copy()
        q['eligible']=q.price_eligible&q.finance_count.ge(3)&q.finance_coverage.ge(minimum)&q.growth.notna()&q.finance_acceleration.notna()
        for date,g in q.groupby('date'):
            coverage.append(dict(threshold=threshold,date=date,price_eligible=int(g.price_eligible.sum()),finance_eligible=int(g.eligible.sum())))
        conditions={'all_finance':q.eligible,'fin_accel_pos':q.finance_acceleration.gt(0),'fin_accel_nonpos':q.finance_acceleration.le(0),
            'fin_nonneg_growth':q.growth.ge(0),'fin_neg_growth':q.growth.lt(0),
            'fin_improving':q.growth.ge(0)&q.finance_acceleration.gt(0),'fin_slowing':q.growth.lt(0)&q.finance_acceleration.gt(0)}
        selection={};cont=q.week_i.sub(q.groupby(KEY).week_i.shift()).eq(1)
        prev_available=q.groupby(KEY).eligible.shift().eq(True)
        for name,flag in conditions.items():
            q[name]=q.eligible&flag;prev=q.groupby(KEY)[name].shift()
            entry=q[name]&prev.eq(False)&cont&prev_available
            boundary=q[name]&(~cont|~prev_available)
            q[name+'_boundary']=boundary
            selection[name,'state']=q.index[q[name]];selection[name,'entry']=q.index[entry]
            entries.append(dict(threshold=threshold,method=name,entries=int(entry.sum()),unknown_boundary=int(boundary.sum())))
        evaluate(q,selection,out)
        peers=q[q.eligible].copy();peers['growth_sign']=peers.growth.ge(0);peers['price_sign']=peers.rate20.ge(0)
        groups=['date','growth_sign','price_sign'];b=(peers.groupby(groups).rate20.rank(method='average')-1)/peers.groupby(groups).rate20.transform('size')
        peers['bin']=np.minimum(4,(b*5).astype(int));groups+=['bin']
        for h in HORIZONS:
            col=f'win{h}';peers['peer']=peers.groupby(groups)[col].transform('mean');peers['peer_n']=peers.groupby(groups)[col].transform('count')
            for (name,unit),ids in selection.items():
                z=peers.loc[peers.index.intersection(ids)].copy();z['delta']=z[col]-z.peer
                weekly=z.groupby('date').delta.mean().reindex(calendar_dates());lo,hi=block_ci(weekly,round(h/5),3311)
                conditional.append(dict(threshold=threshold,method=name,unit=unit,horizon=h,total=len(z),known=z[col].count(),delta=weekly.mean(),lo=lo,hi=hi,
                    singleton_known=int((z[col].notna()&z.peer_n.eq(1)).sum()),median_peer_known=z.loc[z[col].notna(),'peer_n'].median()))
                for year,g in z.groupby(z.date.dt.year):
                    annual.append(dict(threshold=threshold,method=name,unit=unit,horizon=h,year=int(year),known=g.delta.count(),delta=g.groupby('date').delta.mean().mean()))
                pairinfo.append(pd.DataFrame({'row_id':z.index,'threshold':threshold,'method':name,'unit':unit,'horizon':h,'peer_rate':z.peer,'peer_n':z.peer_n,'delta':z.delta}))
    pd.DataFrame(coverage).to_csv(root/'finance_coverage.csv',index=False);pd.DataFrame(entries).to_csv(root/'entry_boundaries.csv',index=False)
    pd.DataFrame(conditional).to_csv(root/'conditional_summary.csv',index=False);pd.DataFrame(annual).to_csv(root/'conditional_annual.csv',index=False)
    pd.concat(pairinfo,ignore_index=True).to_csv(root/'conditional_pairs.csv.gz',index=False)
    inputs=[EP/'outputs/r09/evaluation_panel.parquet',EP/'outputs/r04/industry_coverage.csv.gz',EP/'rounds/r10_reflection.md',EP/'rounds/r11_financial_pool_plan.md',EP/'src/pool_evaluation.py',__file__]
    (root/'receipt.json').write_text(json.dumps({'status':'EXECUTED_EXPLORATORY','inputs':{str(x):sha(x) for x in inputs},'rules':7,'coverage_thresholds':[.3,.5],'horizons':HORIZONS},indent=2)+'\n')
    print(pd.read_csv(root/'coverage30/summary.csv').query('unit=="state"')[['method','horizon','known','pooled_win_rate','paired_all_delta','mean_pool']].to_string(index=False))
    print(pd.DataFrame(conditional).query('unit=="state" and threshold=="coverage30" and method in ["fin_improving","fin_slowing"]').to_string(index=False))
if __name__=='__main__':main()
