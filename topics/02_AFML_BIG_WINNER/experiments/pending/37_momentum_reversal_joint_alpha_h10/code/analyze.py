"""Registered full-curve, conditional-information and economic inference."""
import sys,json
import numpy as np
import pandas as pd
from core import *

def scopes(frame,date_col='exit_date'):
    d=pd.to_datetime(frame[date_col])
    return [('primary',frame.loc[d<='2025-03-03']),('extended',frame),
            ('extension_only',frame.loc[d>'2025-03-03'])]

def controls():
    f=pd.read_parquet(CACHE/'features.parquet');f=f.loc[(f.offset==0)&(f.signal_date>='2021-01-01')].copy()
    c=pd.read_parquet(PRIVATE/'qfq_close.parquet');raw=pd.read_parquet(PRIVATE/'close.parquet')
    ret=c.pct_change(fill_method=None)
    market=pd.read_parquet(PRIVATE/'market.parquet').close.reindex(c.index).pct_change(fill_method=None)
    m=pd.DataFrame(np.broadcast_to(market.to_numpy()[:,None],ret.shape),index=c.index,columns=c.columns).where(ret.notna())
    r=ret.where(m.notna());cov=(r*m).rolling(60).mean()-r.rolling(60).mean()*m.rolling(60).mean()
    var=m.rolling(60).var(ddof=0).where(lambda x:x>1e-16)
    money=pd.read_parquet(PRIVATE/'money.parquet').where(lambda x:x>0)
    turn=pd.read_parquet(PRIVATE/'turnover_rate.parquet').where(lambda x:x>=0)
    arrays=dict(vol20=ret.rolling(20).std(ddof=0),beta60=cov/var,
                log_money20=np.log(money.rolling(20).mean()),turnover20=turn.rolling(20).mean())
    idx=pd.MultiIndex.from_frame(f[['signal_date','instrument']])
    for k,v in arrays.items():f[k]=v.rename_axis(index='signal_date',columns='instrument').stack().reindex(idx).to_numpy()
    ind=pd.read_parquet(PRIVATE/'industry.parquet').copy()
    ind['instrument']=ind.ts_code.str[-2:]+ind.ts_code.str[:6];ind['start']=pd.to_datetime(ind.in_date)
    ind['end']=pd.to_datetime(ind.out_date).fillna(pd.Timestamp('2100-01-01'))
    f['industry']=None;f['log_total_mv']=np.nan;f['cap_source_date']=pd.NaT;cap_audit=[]
    for date,ix in f.groupby('signal_date').groups.items():
        active=ind.loc[(ind.start<=date)&(ind.end>date)]
        mapping=active.groupby('instrument').l1_code.agg(lambda v:v.iloc[0] if v.notna().all() and v.nunique()==1 else None)
        f.loc[ix,'industry']=f.loc[ix,'instrument'].map(mapping)
        pos=c.index.get_loc(date)-1;previous=c.index[pos];path=PRIVATE/'style_caps_20261117'/f'{previous:%Y%m%d}.json'
        if not path.exists():
            cap_audit.append(dict(signal_date=date,source_date=previous,status='EXACT_PRIOR_DATE_NOT_CACHED',rows=0,rejected=0));continue
        receipt=path.with_name(path.stem+'.receipt.json');rec=json.loads(receipt.read_text());assert sha(path)==rec['sha256']
        rawcap=json.loads(path.read_text())['data'];cap=pd.DataFrame(rawcap['items'],columns=rawcap['fields'])
        assert cap.trade_date.astype(str).eq(f'{previous:%Y%m%d}').all()
        cap['instrument']=cap.ts_code.str[-2:]+cap.ts_code.str[:6];cap=cap.loc[cap.instrument.isin(f.loc[ix,'instrument'])].copy()
        assert not cap.instrument.duplicated().any()
        for k in ['close','total_mv','total_share','circ_mv','float_share']:cap[k]=pd.to_numeric(cap[k],errors='coerce')
        reference=cap.instrument.map(raw.iloc[pos]);bad=~np.isfinite(reference)|(abs(cap.close-reference)>(.01+1e-5*abs(reference)))
        for mv,shares in [('total_mv','total_share'),('circ_mv','float_share')]:
            bad|=~(cap[mv]>0)|~(cap[shares]>0)|~(cap.close>0)|(abs(cap.close*cap[shares]-cap[mv])>np.maximum(.01,abs(cap[mv])*1e-4))
        cap['log_total_mv']=np.log(cap.total_mv.where(~bad))
        f.loc[ix,'log_total_mv']=f.loc[ix,'instrument'].map(cap.set_index('instrument').log_total_mv)
        f.loc[ix,'cap_source_date']=previous
        cap_audit.append(dict(signal_date=date,source_date=previous,status='EXACT_CACHED_DATE',rows=len(cap),rejected=int(bad.sum())))
    f=f.replace([np.inf,-np.inf],np.nan)
    f.to_parquet(CACHE/'controls.parquet',index=False);pd.DataFrame(cap_audit).to_csv(OUT/'capitalization_audit.csv',index=False)
    return f

def conditional_metric(g,columns):
    if len(g)<100:return dict(ic=np.nan,rank=0,df=len(g),status='INSUFFICIENT_ROWS')
    a=g[columns].to_numpy(float);sd=a.std(0);sd[sd<1e-12]=1
    a=(a-a.mean(0))/sd
    x=np.column_stack([np.ones(len(g)),a,pd.get_dummies(g.industry,drop_first=True).to_numpy(float)])
    u,s,_=np.linalg.svd(x,full_matrices=False);keep=s>s[0]*1e-12;q=u[:,keep];rank=int(keep.sum())
    if len(g)-rank<30:return dict(ic=np.nan,rank=rank,df=len(g)-rank,status='INSUFFICIENT_RESIDUAL_DF')
    y=g[['J_R','h10']].to_numpy(float);res=y-q@(q.T@y)
    if np.std(res[:,0])<1e-10*max(np.std(y[:,0]),1e-12):
        return dict(ic=np.nan,rank=rank,df=len(g)-rank,status='NUMERICALLY_ZERO_SCORE_RESIDUAL')
    return dict(ic=rankcorr(res[:,0],res[:,1]),rank=rank,df=len(g)-rank,status='AVAILABLE_PARTIAL_SUPPORT')

def run():
    verify_freeze();p=pd.read_parquet(CACHE/'predictions.parquet');labels=pd.read_parquet(CACHE/'labels.parquet')
    p=p.merge(labels[['signal_date','instrument','offset','h10']],on=['signal_date','instrument','offset'],validate='many_to_one')
    p=p.loc[p.exit_date.notna()]
    ranks=pd.read_parquet(CACHE/'rankings.parquet').merge(labels[['signal_date','instrument','offset','h10']],on=['signal_date','instrument','offset'],validate='many_to_one')
    ranks=ranks.loc[ranks.exit_date.notna()]
    icrows=[];stateic=[];curve=[];statecurve=[]
    for (scheme,offset,date),g in p.groupby(['scheme','offset','signal_date']):
        for mid in SCORES:
            if mid not in g or not g[mid].notna().any():continue
            valid=g[[mid,'h10']].dropna()
            icrows.append(dict(scheme=scheme,offset=offset,signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,n=len(valid),
                               RankIC=rankcorr(valid[mid],valid.h10) if len(valid)>=100 else np.nan))
            for state,h in g.groupby('state'):
                stateic.append(dict(scheme=scheme,offset=offset,signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,state=state,
                                    n=int(h[[mid,'h10']].dropna().shape[0]),RankIC=rankcorr(h[mid],h.h10)))
    for (scheme,offset,date,mid,decile),g in ranks.groupby(['scheme','offset','signal_date','model','decile']):
        known=g.h10.dropna()
        curve.append(dict(scheme=scheme,offset=offset,signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,decile=decile,
                          selected=len(g),known=len(known),mean=known.mean(),median=known.median(),p10=known.quantile(.1),p90=known.quantile(.9),
                          win_rate=known.gt(0).mean() if len(known) else np.nan))
        for state,h in g.groupby('state'):
            statecurve.append(dict(scheme=scheme,offset=offset,signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,decile=decile,state=state,
                                   count=len(h),share=len(h)/len(g),known=int(h.h10.notna().sum()),mean=h.h10.mean()))
    ic=pd.DataFrame(icrows);curves=pd.DataFrame(curve);sic=pd.DataFrame(stateic);sc=pd.DataFrame(statecurve)
    ic.to_csv(OUT/'rank_ic_by_date.csv',index=False);curves.to_csv(OUT/'deciles_by_date.csv',index=False)
    sic.to_csv(OUT/'state_ic_by_date.csv',index=False);sc.to_csv(OUT/'state_deciles_by_date.csv',index=False)
    summary=[];curve_summary=[]
    for scope,g in scopes(ic):
        for key,h in g.groupby(['scheme','offset','model']):
            b=bootstrap(h.sort_values('signal_date').RankIC)
            summary.append(dict(scope=scope,scheme=key[0],offset=key[1],model=key[2],**b))
    for scope,g in scopes(curves):
        for key,h in g.groupby(['scheme','offset','model','decile']):
            curve_summary.append(dict(scope=scope,scheme=key[0],offset=key[1],model=key[2],decile=key[3],
                                      mean_H10=h['mean'].mean(),mean_median_H10=h['median'].mean(),mean_win_rate=h.win_rate.mean(),
                                      known_stock_events=h.known.sum(),planned_stock_events=h.selected.sum(),rounds=len(h)))
    pd.DataFrame(summary).to_csv(OUT/'rank_ic_summary.csv',index=False);pd.DataFrame(curve_summary).to_csv(OUT/'deciles_summary.csv',index=False)

    ctrl=controls();main=p.loc[(p.scheme=='expanding')&(p.offset==0)].copy()
    columns=['log_total_mv','vol20','beta60','log_money20','turnover20']+BASE+['A_R']
    extra=['signal_date','instrument','industry','log_total_mv','vol20','beta60','log_money20','turnover20','cap_source_date']
    main=main.merge(ctrl[extra],on=['signal_date','instrument'],how='left',validate='one_to_one')
    rows=[];exposure=[];support_rows=[]
    main_ranks=ranks.loc[(ranks.scheme=='expanding')&(ranks.offset==0)]
    for date,g in main.groupby('signal_date'):
        available=g[columns+['industry','J_R']].notna().all(axis=1)
        known=available&g.h10.notna();eligible=g.loc[known]
        result=conditional_metric(eligible,columns)
        jtop=main_ranks.loc[(main_ranks.signal_date==date)&(main_ranks.model=='J_R')&(main_ranks.decile==10),'instrument']
        top=g.instrument.isin(jtop)
        rows.append(dict(signal_date=date,exit_date=g.exit_date.iloc[0],n_total=len(g),n_controls=int(available.sum()),n_labeled=int(known.sum()),
                         stock_coverage=available.mean(),D10_budget_coverage=float(available[top].mean()),**result))
        for mid in ['J_R','A_R','MOM','REV','FIX']:
            support_rows.append(dict(signal_date=date,exit_date=g.exit_date.iloc[0],model=mid,
                                     same_support_rank_ic=rankcorr(eligible[mid],eligible.h10),support_n=len(eligible)))
            picked=main_ranks.loc[(main_ranks.signal_date==date)&(main_ranks.model==mid)&(main_ranks.decile==10),'instrument']
            basket=g.loc[g.instrument.isin(picked)]
            for col in columns[:-1]:
                exposure.append(dict(signal_date=date,model=mid,control=col,mean=basket[col].mean(),known_budget=basket[col].notna().mean()))
            for industry,h in basket.groupby('industry',dropna=False):
                exposure.append(dict(signal_date=date,model=mid,control='industry:'+str(industry),mean=len(h)/len(basket),known_budget=float(pd.notna(industry))))
    cond=pd.DataFrame(rows);cond.to_csv(OUT/'conditional_information.csv',index=False)
    pd.DataFrame(support_rows).to_csv(OUT/'same_support_rank_ic.csv',index=False)
    pd.DataFrame(exposure).to_csv(OUT/'D10_risk_exposures.csv',index=False)
    main.to_parquet(CACHE/'analysis_common_panel.parquet',index=False)

    events=pd.read_csv(OUT/'events.csv',parse_dates=['signal_date','entry_date','exit_date'])
    calendar=pd.read_csv(OUT/'calendar.csv',parse_dates=['signal_date','entry_date','exit_date'])
    dates=calendar.loc[(calendar.offset==0)&(calendar.entry_date>='2021-01-11')&calendar.exit_date.notna()].copy()
    im=ic.loc[(ic.scheme=='expanding')&(ic.offset==0)].pivot(index='signal_date',columns='model',values='RankIC')
    ev=events.loc[(events.scheme=='expanding')&(events.offset==0)&(events.portfolio=='D10')&(events.cost=='main')].copy()
    # A zero-fill account is valid cash, but cannot support a claim about executed stock selection.
    valid=ev.complete_exit&ev.any_entry;ev['adjudicated']=ev.net_return.where(valid)
    em=ev.pivot(index='signal_date',columns='model',values='adjudicated')
    full=ev.pivot(index='signal_date',columns='model',values='full_entry')
    per=dates[['signal_date','entry_date','exit_date']].set_index('signal_date')
    per['P1']=(im.J_R-im.A_R).reindex(per.index)
    comparisons={'P2a':'A_R','P2b':'MOM','P2c':'REV','P2d':'FIX'}
    for name,baseline in comparisons.items():per[name]=(em.J_R-em[baseline]).reindex(per.index)
    per['P3']=cond.set_index('signal_date').ic.reindex(per.index)
    per.reset_index().to_csv(OUT/'primary_test_series.csv',index=False)
    tests=[];sens=[]
    for scope,g in scopes(per.reset_index()):
        for block in [6,3,12]:
            result=[dict(scope=scope,test=k,**bootstrap(g[k],length=block)) for k in ['P1','P2a','P2b','P2c','P2d','P3']]
            adj=holm([x['p'] for x in result])
            for row,q in zip(result,adj):row['holm_p']=q;row['positive_support']=bool(np.isfinite(q) and q<.05 and row['mean']>0)
            (tests if block==6 else sens).extend(result)
    pd.DataFrame(tests).to_csv(OUT/'primary_tests.csv',index=False);pd.DataFrame(sens).to_csv(OUT/'block_sensitivity.csv',index=False)
    pair_sens=[]
    required=['J_R','A_R','MOM','REV','FIX'];all_ok=em[required].notna().all(axis=1)
    for scope,g in scopes(per.reset_index()):
        for key,base in comparisons.items():
            index=pd.DatetimeIndex(g.signal_date)
            for rule,mask in [('all_baselines_common_exit',all_ok),('pair_full_entry',full.J_R&full[base])]:
                values=(em.J_R-em[base]).where(mask).reindex(index)
                pair_sens.append(dict(scope=scope,test=key,support_rule=rule,**bootstrap(values)))
    pd.DataFrame(pair_sens).to_csv(OUT/'event_support_sensitivity.csv',index=False)

    # Complete event evidence for costs and each portfolio, with matched date differences.
    event_summary=[]
    for scope,g in scopes(events):
        for keys,h in g.groupby(['scheme','offset','model','portfolio','cost']):
            values=h.net_return.where(h.complete_exit&h.any_entry)
            event_summary.append(dict(scope=scope,scheme=keys[0],offset=keys[1],model=keys[2],portfolio=keys[3],cost=keys[4],
                mean_net=values.mean(),known=values.notna().sum(),planned=len(h),mean_entry_weight=h.entry_weight.mean(),full_entry_rounds=h.full_entry.sum()))
    pd.DataFrame(event_summary).to_csv(OUT/'event_summary.csv',index=False)
    state_summary=[]
    # Missing state-decile cells have zero budget; do not average only months where a state appeared.
    for scope,g in scopes(sc):
        for key,h in g.groupby(['scheme','offset','model','decile']):
            dates2=pd.DatetimeIndex(h.signal_date.unique())
            for state in STATES:
                z=h.loc[h.state==state].set_index('signal_date')
                state_summary.append(dict(scope=scope,scheme=key[0],offset=key[1],model=key[2],decile=key[3],state=state,
                    average_share=z.share.reindex(dates2,fill_value=0).mean(),conditional_mean_return=z['mean'].mean(),present_rounds=len(z),all_rounds=len(dates2)))
    pd.DataFrame(state_summary).to_csv(OUT/'state_summary.csv',index=False)
    # Descriptive concentration only; these omissions are never new primary tests.
    concentration=[]
    for test in ['P1','P2a','P2b','P2c','P2d','P3']:
        for name,mask in [('all',np.ones(len(per),bool)),('exclude_2024_02',per.index.to_period('M')!=pd.Period('2024-02'))]+[(f'exclude_{year}',per.index.year!=year) for year in sorted(set(per.index.year))]:
            concentration.append(dict(test=test,omission=name,**bootstrap(per[test].where(mask))))
    pd.DataFrame(concentration).to_csv(OUT/'concentration_diagnostics.csv',index=False)
    record_stage('analysis',[OUT/'primary_tests.csv',OUT/'conditional_information.csv',OUT/'deciles_summary.csv',OUT/'rank_ic_summary.csv',OUT/'event_summary.csv'])
    print('analysis complete; primary test family retained at six',flush=True)

if __name__=='__main__':run()
