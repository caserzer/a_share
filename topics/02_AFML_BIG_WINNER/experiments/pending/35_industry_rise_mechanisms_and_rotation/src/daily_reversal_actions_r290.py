from common import *
import pandas as pd
from followup_r10 import exit_economics

def run():
    out=ROOT/'outputs/r290';out.mkdir(exist_ok=True)
    o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet')
    o['n']=o.groupby(['era','level','date']).date.transform('size');o['p']=np.ceil(o.n/5)/o.n
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[p.end_time.normalize()<=cal.max() for p in ends.index]]
    parts=[];unknown=[]
    for strategy,g in [('daily',o),('monthly',o[o.date.isin(ends.values)])]:
        for variant in ['base','state','interaction']:
            selected=a[a.strategy.eq(strategy)&a.variant.eq(variant)][KEY+['date']].assign(alert=True)
            q=g.merge(selected,on=KEY+['date'],how='left',validate='one_to_one');q['alert']=q.alert.eq(True)
            assert q.groupby(['era','level','date']).alert.sum().eq(np.ceil(q.groupby(['era','level','date']).size()/5)).all()
            u=q[~q.complete_path][KEY+['date','n','p','alert']].copy();u['unknown_gain_coefficient']=(u.alert.astype(float)-u.p)/u.n;u['strategy']=strategy;u['variant']=variant;unknown.append(u)
            for cost in [0,.002,.005]:
                v=q.copy();cash,market=exit_economics(v.return20,v.market_return20,cost)
                for name,gain in [('cash',cash),('market',market)]:
                    gain=gain.where(v.complete_path);v[name+'_selected']=gain*v.alert;v[name+'_random']=gain*v.p;v[name+'_difference']=gain*(v.alert.astype(float)-v.p)
                grouped=v.groupby(['era','level','date']);agg=grouped.agg(eligible=('n','size'),alerts=('alert','sum'),known=('complete_path','sum'))
                agg['unknown']=agg.eligible-agg.known;agg['complete_date']=agg.unknown.eq(0)
                for name in ['cash','market']:
                    for kind in ['selected','random','difference']:
                        total=grouped[name+'_'+kind].sum(min_count=1)
                        agg[name+'_'+kind+'_known_conditional']=total/agg.known.where(agg.known.gt(0))
                        # Empty known set has exact zero known contribution, not zero unknown payoff.
                        agg[name+'_'+kind+'_known_contribution']=total.fillna(0)/agg.eligible
                parts.append(agg.reset_index().assign(strategy=strategy,variant=variant,cost=cost))
    dates=pd.concat(parts,ignore_index=True);dates.to_parquet(out/'date_metrics.parquet',index=False);pd.concat(unknown,ignore_index=True).to_parquet(out/'unknown_coefficients.parquet',index=False)
    rows=[]
    for key,g in dates.groupby(['era','level','strategy','variant','cost']):
        for period,z in [('all',g)]+[(str(y),t) for y,t in g.groupby(g.date.dt.year)]:
            full=z[z.complete_date];r=dict(zip(['era','level','strategy','variant','cost'],key),period=period,dates=len(z),complete_dates=len(full),known_dates=int(z.known.gt(0).sum()),unknown_origins=int(z.unknown.sum()))
            for name in ['cash','market']:
                for kind in ['selected','random','difference']:
                    col=name+'_'+kind+'_known_conditional';r[name+'_'+kind+'_complete']=full[col].mean();r[name+'_'+kind+'_conditional']=z[col].mean()
            rows.append(r)
    summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False)
    full=summary[summary.period.eq('all')];result=dict(status='PASS',groups=len(full),date_cost_records=len(dates),cash_complete_positive_vs_hold=int(full.cash_selected_complete.gt(0).sum()),cash_complete_positive_vs_random=int(full.cash_difference_complete.gt(0).sum()),market_complete_positive_vs_hold=int(full.market_selected_complete.gt(0).sum()),market_complete_positive_vs_random=int(full.market_difference_complete.gt(0).sum()),no_refit=True,adoption=False)
    js(out/'result.json',result);reads=json.loads((ROOT/'protocols/r290.json').read_text())['inputs']+['protocols/r290.json','src/daily_reversal_actions_r290.py','src/followup_r10.py']
    js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},benchmark_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}));print(result);print(full[full.cost.eq(.005)][['era','level','strategy','variant','complete_dates','cash_selected_complete','cash_difference_complete','market_selected_complete','market_difference_complete']].to_string(index=False))
if __name__=='__main__':run()
