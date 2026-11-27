"""Compute same-date complete-month comparisons, portfolios, and coverage."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sources import OUT,OLD,PRIVATE
PAIRS={
'D1.1':[('N2','N2Boundary'),('N1','N1Boundary'),('N3','N3Boundary')],
'D1.2':[('NarrowGate','Narrow'),('WideGate','N2'),('Narrow','N2'),('NarrowGate','WideGate')],
'D1.3':[('Shallow','N2')],
'D1.4':[('Safe','N2'),('Announced','N2')],
'D1.5':[('Combo','Ridge'),('Combo','N2'),('Combo','ComboBoundary'),('Combo','ComboNoGate'),('Combo','NarrowGate'),('Combo','ComboNoCap'),('Combo1','N1'),('Combo3','N3')],
'D2.1':[(n,b) for n in ['B0_40','B24_40','B24_45'] for b in ['Ridge','EP38Buffer',n+'Cash']],
'D2.2':[(b+'Path',b) for b in ['B0_40','B24_40','B24_45']],
'D3.2':[('Diff','DiffLeft'),('ScreenDiff','ScreenDiffLeft'),('Diff','ScreenDiff')],
'D3.3':[('Intersection','IntersectionLeft'),('Intersection','Diff')],
'A2':[('SellTree',n) for n in ['SellRidge','Ridge','SellPos','SellVol','SellMoney']]}
def draws(n):
    rng=np.random.default_rng(4201);pos=rng.integers(0,n-2,size=(10000,(n+2)//3))
    return (pos[:,:,None]+np.arange(3)).reshape(10000,-1)[:,:n]
def summarize():
    direct=pd.read_parquet(OUT/'direct_months.parquet')
    # Index reference uses actual close of respective endpoints for annual/segment return.
    raw=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    index=pd.DataFrame(raw['items'],columns=raw['fields']).set_index('trade_date').close
    index.index=pd.to_datetime(index.index); index=index.sort_index()
    ix=index.resample('ME').last().pct_change()
    ix.index=ix.index.strftime('%Y-%m')
    scores=pd.read_parquet(OLD/'p2/results/scores.parquet',columns=['entry_idx','instrument','R'])
    labels=pd.read_parquet(OUT/'dual_scores.parquet',columns=['entry_idx','instrument','h10','event','right','risk','rtail','enabled'])
    labelrank=labels.sort_values(['entry_idx','h10','instrument']).dropna(subset=['h10'])
    # EP41 defines outcome deciles using order index divided by same-day valid count.
    labelrank['decile']=1+(10*labelrank.groupby('entry_idx').cumcount()//labelrank.groupby('entry_idx').instrument.transform('size'))
    labels=labels.merge(labelrank[['entry_idx','instrument','decile']],how='left')
    cov=pd.read_parquet(OUT/'covariates.parquet',columns=['entry_idx','instrument','riskcap','riskadv','announced','past_excess10'])
    aggs=[];annual=[];changes=[];arms=[]
    meta=scores.sort_values(['entry_idx','R','instrument'],ascending=[True,False,False])
    base={e:set(z.instrument.iloc[:len(z)//10]) for e,z in meta.groupby('entry_idx')}
    perstock=[];riskbud=[];natural=[]
    for scdir in sorted((OUT/'books').iterdir()):
        scope=scdir.name;r=pd.read_parquet(scdir/'Ridge/daily.parquet').set_index('date')
        for folder in sorted(scdir.iterdir()):
            name=folder.name
            d=pd.read_parquet(folder/'daily.parquet').set_index('date')
            prev=d.nav.shift().fillna(1.); previous_index=index.reindex(d.index).shift()
            for yr,g in d.groupby(d.index.year):
                t0,t1=g.index[0],g.index[-1]; net=g.nav.iloc[-1]/prev[t0]-1
                baseline=r.loc[t1,'nav']/r.nav.shift().fillna(1.).at[t0]-1
                bench=index[t1]/(previous_index[t0] if pd.notna(previous_index[t0]) else index[t0])-1
                annual.append((scope,name,yr,t0,t1,net,baseline,bench,net-baseline,net-bench))
            obs=pd.read_parquet(folder/'decisions.parquet');od=pd.read_parquet(folder/'orders.parquet')
            total=pd.DataFrame({'entry_idx':obs.entry_idx,'total':obs.k*obs.ticket,'n':obs.k,'support':obs.style_pairs})
            if 'Random' in name or 'Amount' in name or name in ['SellStyle','SellVolMatch','SellUniform']:continue
            td=[]
            for row in obs.itertuples():
                chosen=set(row.target);core=base[row.entry_idx]
                for sign,items in [('excluded',core-chosen),('added',chosen-core)]:
                    for j in items:td.append((row.entry_idx,j,sign,row.ticket))
            trade=pd.DataFrame(td,columns=['entry_idx','instrument','role','planned'])
            if trade.empty:
                arms.append((scope,name,0,0,total.total.sum(),0,0));continue
            trade=trade.merge(labels,on=['entry_idx','instrument'],validate='m:1').merge(cov,on=['entry_idx','instrument'],validate='m:1')
            # Active sleeve net order; aggregate cross-sleeve broker order only by sign for separate costs.
            lo=obs.entry_idx.min()
            od=od[od.sleeve==(od.entry_idx-lo)%10].groupby(['entry_idx','instrument'])[['net','broker','fee','target']].sum()
            trade=trade.join(od,on=['entry_idx','instrument'])
            trade['net']=trade.net.fillna(0);trade['dollars_actual_new']=trade.net.clip(lower=0)
            trade['new_gross_h10']=trade.dollars_actual_new*trade.h10
            trade['ticket_opportunity_h10']=trade.planned*trade.h10
            arms.append((scope,name,trade.entry_idx.nunique(),(trade.role=='added').sum(),total.total.sum(),trade.query("role=='added'").planned.sum(),trade.query("role=='added'").dollars_actual_new.sum()))
            if name in ['Diff','DiffLeft','ScreenDiff','ScreenDiffLeft','Intersection','IntersectionLeft','SellTree','SellRidge','N2','N2Boundary','Combo','Shallow']:
                perstock.append(trade.assign(scope=scope,arm=name))
            if name in ['B0_40Path','B24_40Path','B24_45Path']:
                q=obs[['entry_idx','ticket','removed']].explode('removed').dropna(subset='removed').rename(columns={'removed':'instrument'}).merge(cov,on=['entry_idx','instrument'])
                assert q.past_excess10.gt(.08-1.e-7).all()
            if name in ['Safe','Announced','Combo','N2']:
                q=trade.groupby('role').agg(planned=('planned','sum'),unknown_cap180=('riskcap',lambda x:x.isna().sum()),unknown_adv180=('riskadv',lambda x:x.isna().sum()),known_announced=('announced','sum'),seats=('planned','size')).reset_index()
                riskbud.append(q.assign(scope=scope,arm=name))
        bhold=pd.read_parquet(scdir/'Ridge/decisions.parquet');o=pd.read_parquet(scdir/'Ridge/orders.parquet')
        # The original natural-new set requires real pre-decision units. Reconstruct with raw
        # lot counts reported by replay's opening-state export in a separate diagnostic pass.
    if perstock:pd.concat(perstock).to_parquet(OUT/'actual_switches.parquet',index=False)
    pd.concat(riskbud).to_csv(OUT/'risk_coverage.csv',index=False)
    pd.DataFrame(arms,columns='scope arm changed_days added_seats sum_planned_core sum_planned_added actual_net_bought_added'.split()).to_csv(OUT/'capital.csv',index=False)
    pd.DataFrame(annual,columns='scope arm year start end net ridge index excess_ridge excess_index'.split()).to_csv(OUT/'annual.csv',index=False)
    for (scope,fee),group in direct.groupby(['scope','fees']):
        data=group.pivot(index='month',columns='arm',values=['net','gross','fee','turnover'])
        b=draws(len(data))
        for item,pairs in PAIRS.items():
            for a,ref in pairs+[(p[0],'Ridge') for p in pairs if p[1]!='Ridge']:
                diff=(data.xs(a,level=1,axis=1)-data.xs(ref,level=1,axis=1))*10000
                z=diff.net.to_numpy();lo,hi=np.quantile(z[b].mean(axis=1),[.025,.975])
                aggs.append((item,scope,fee,a,ref,len(z),z.mean(),lo,hi,np.sort(z)[:-3].mean(),diff.gross.mean(),diff.fee.mean(),diff.turnover.mean()))
    cols='id scope cost arm control months net_bp lo hi drop3 gross_bp fee_bp turnover_bp'.split()
    pd.DataFrame(aggs,columns=cols).drop_duplicates().to_csv(OUT/'contrasts.csv',index=False)
    raw=[]
    for f in sorted((OUT/'random').glob('*.parquet')):
        a=f.stem
        ref=('SellTree' if a.startswith('Sell') else a.replace('Random','').replace('Amount',''))
        refdata=direct[(direct.arm==ref)&(direct.fees==1)]
        z=pd.read_parquet(f).merge(refdata,on=['scope','month'],suffixes=('_r','_a'))
        z['diff']=(z.net_a-z.net_r)*10000;z['turn_diff']=(z.turnover_a-z.turnover_r)
        # Turnover-comparable is a descriptive paired diagnostic only. No stock is selected with it.
        z['close_turn']=z.turn_diff.abs()<=.05*z.turnover_a
        for (scope,seed),g in z.groupby(['scope','seed_r']):
            close=g[g.close_turn]
            raw.append((a,scope,seed,g['diff'].mean(),g.turn_diff.mean(),len(close),close['diff'].mean(),g['diff'].abs().max(),g.net_r.mean()))
    co=pd.DataFrame(raw,columns='control scope seed gap_bp turnover_gap close_turn_months close_turn_gap_bp max_single_gap_bp control_mean'.split())
    co.to_parquet(OUT/'random_contrasts.parquet',index=False)
    co.groupby(['control','scope']).agg(seeds=('seed','nunique'),median=('gap_bp','median'),min=('gap_bp','min'),max=('gap_bp','max'),turnover_gap=('turnover_gap','median'),matched_months=('close_turn_months','median'),matched_net_bp=('close_turn_gap_bp','median')).to_csv(OUT/'random_summary.csv')
if __name__=='__main__':summarize()
