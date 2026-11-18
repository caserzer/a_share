"""Read-only post-hoc EP36/EP37 comparison; no retraining or parameter search."""
import json
import numpy as np
import pandas as pd
from core import *

def run():
    dest=OUT/'ep36_comparison_20261118';dest.mkdir(exist_ok=True)
    files=sorted((SOURCE/'outputs/fold_predictions/expanding').glob('*.parquet'))
    old=pd.concat([pd.read_parquet(x,columns=['signal_date','instrument','score'],
        filters=[('model_id','==','E1'),('seed_or_ensemble','==','fixed')]) for x in files]).rename(columns={'score':'E1'})
    p=pd.read_parquet(CACHE/'predictions.parquet');p=p.loc[(p.scheme=='expanding')&(p.offset==0)]
    lab=pd.read_parquet(CACHE/'labels.parquet');lab=lab.loc[lab.offset==0,['signal_date','instrument','h10']]
    oldlabels=pd.read_parquet(PRIVATE/'labels.parquet',columns=['signal_date','instrument','h10']).rename(columns={'h10':'old_h10'})
    p=p.merge(lab,on=['signal_date','instrument'],validate='one_to_one')
    g=p.merge(old,on=['signal_date','instrument'],validate='one_to_one').merge(oldlabels,on=['signal_date','instrument'],validate='one_to_one')
    g=g.loc[g.exit_date.notna()&(g.exit_date<='2025-03-03')].dropna(subset=['E1','J_R','h10'])
    assert np.allclose(g.h10,g.old_h10,rtol=0,atol=1e-14)
    rows=[]
    for date,x in g.groupby('signal_date'):
        if len(x)>=100:
            rows.append(dict(signal_date=date,n=len(x),E1_RankIC=rankcorr(x.E1,x.h10),J_R_RankIC=rankcorr(x.J_R,x.h10),
                             score_rank_correlation=rankcorr(x.E1,x.J_R)))
    s=pd.DataFrame(rows);s['difference_E1_minus_J_R']=s.E1_RankIC-s.J_R_RankIC
    cal=pd.read_csv(OUT/'calendar.csv',parse_dates=['signal_date','entry_date','exit_date'])
    dates=cal.loc[(cal.offset==0)&(cal.entry_date>='2021-01-11')&(cal.exit_date<='2025-03-03'),'signal_date']
    ci=bootstrap(s.set_index('signal_date').difference_E1_minus_J_R.reindex(dates))
    op=SOURCE/'outputs/sensitivity/q5_rebalance_20261116/all_metrics.csv'
    om=pd.read_csv(op);om=om.loc[(om.valuation=='suspend_flat')&(om.model=='E1')&(om.scope=='main_common')&(om.benchmark=='CSI300_TOTAL_RETURN')&om.cost.isin(['zero','main'])]
    nm=pd.read_csv(OUT/'accounts.csv');nm=nm.loc[(nm.scheme=='expanding')&(nm.offset==0)&(nm.scope=='primary')&(nm.valuation=='flat')]
    oldnet=om.loc[(om.frequency=='1m')&(om.cost=='main'),'cagr'].iloc[0];oldgross=om.loc[(om.frequency=='1m')&(om.cost=='zero'),'cagr'].iloc[0]
    newnet=nm.loc[(nm.model=='J_R')&(nm.portfolio=='D10')&(nm.cost=='main'),'cagr'].iloc[0];newgross=nm.loc[(nm.model=='J_R')&(nm.portfolio=='D10')&(nm.cost=='zero'),'cagr'].iloc[0]
    oldfold=json.loads((SOURCE/'outputs/manifests/expanding_2021Q1.json').read_text());fold=pd.read_csv(OUT/'folds.csv')
    newfold=fold.loc[(fold.scheme=='expanding')&(fold.offset==0)&(fold.fold=='2021Q1')&(fold.model=='J_R')].iloc[0]
    bridge=dict(old_E1_monthly_gross=oldgross,old_E1_monthly_net=oldnet,new_J_R_H10_gross=newgross,new_J_R_H10_net=newnet,
                net_decline=oldnet-newnet,gross_decline_combined_changes=oldgross-newgross,old_cost_drag=oldgross-oldnet,
                new_cost_drag=newgross-newnet,extra_cost_drag=(newgross-newnet)-(oldgross-oldnet),
                caveat='EP36 terminal close and 1001-day CAGR versus EP37 terminal open and 1000-session CAGR; accounting identity, not causal feature attribution')
    assert abs(bridge['net_decline']-bridge['gross_decline_combined_changes']-bridge['extra_cost_drag'])<1e-12
    summary=dict(same_date_common_stocks=dict(dates=len(s),stock_events=int(s.n.sum()),mean_stock_count=s.n.mean(),
                 E1_RankIC=s.E1_RankIC.mean(),J_R_RankIC=s.J_R_RankIC.mean(),mean_score_rank_correlation=s.score_rank_correlation.mean(),
                 paired_difference_bootstrap=ci,identical_H10_labels_verified=True),published_endpoint_cost_bridge=bridge,
                 initial_training_rows=dict(EP36_E1=oldfold['train_rows'],EP37_J_R=int(newfold.train_rows)),
                 new_J_R_top20_net=nm.loc[(nm.model=='J_R')&(nm.portfolio=='TOP20')&(nm.cost=='main'),'cagr'].iloc[0],
                 posthoc_diagnostic=True,new_training=False)
    s.to_csv(dest/'same_date_ranking.csv',index=False);om.to_csv(dest/'ep36_costs.csv',index=False)
    nm.loc[nm.model.isin(['J_R','A_R','J_Z','EW'])].to_csv(dest/'ep37_costs_and_groups.csv',index=False)
    dump(dest/'summary.json',clean(summary))
    files += [op,OUT/'accounts.csv',OUT/'folds.csv',CACHE/'predictions.parquet',CACHE/'labels.parquet',PRIVATE/'labels.parquet',
              SOURCE/'outputs/manifests/expanding_2021Q1.json',Path(__file__)]
    dump(dest/'sources.json',[dict(path=str(x),sha256=sha(x)) for x in files])
    print('same-date labels verified; cost bridge closed; no training or portfolio changes')

if __name__=='__main__':run()
