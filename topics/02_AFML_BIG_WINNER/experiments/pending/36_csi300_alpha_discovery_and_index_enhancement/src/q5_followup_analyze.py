"""Matched-period comparisons, ledger checks and descriptive exposure diagnostics."""
import json
import numpy as np
import pandas as pd
from common import EP,PRIVATE,sha,save_json,protocol
from q5_followup import DEST,CONFIG,specs
from summarize import returns

def key(model,freq='1m',phase=1,buffer=0,cost='main'):
    return f'{model}__{freq}__p{phase}__b{buffer}__{cost}'

def stats(nav,benchmark):
    n=len(nav);r=returns(nav);b=returns(benchmark);active=r-b
    cg=nav.iloc[-1]**(252/n)-1;bc=benchmark.iloc[-1]**(252/n)-1
    rel=nav/benchmark;peak=np.maximum.accumulate(np.r_[1.,nav]);rp=np.maximum.accumulate(np.r_[1.,rel])
    beta=np.cov(r,b,ddof=1)[0,1]/b.var() if b.var()>0 else np.nan
    return dict(sessions=n,cagr=cg,benchmark_cagr=bc,cagr_difference=cg-bc,relative_nav_cagr=rel.iloc[-1]**(252/n)-1,max_drawdown=np.min(np.r_[1.,nav]/peak-1),relative_max_drawdown=np.min(np.r_[1.,rel]/rp-1),tracking_error=active.std()*np.sqrt(252),information_ratio=active.mean()/active.std()*np.sqrt(252) if active.std()>0 else np.nan,beta_to_total_return=beta,descriptive_annual_intercept=(r.mean()-beta*b.mean())*252)

def uncertainty(x):
    x=np.asarray(x);n=len(x);L=65;B=2000
    if n<2*L:return np.nan,np.nan,np.nan
    rng=np.random.default_rng(20261116);starts=rng.integers(0,n,(B,int(np.ceil(n/L))))
    idx=((starts[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n]
    means=x[idx].mean(axis=1);lo,hi=np.quantile(means,[.025,.975])
    # Recentered bootstrap approximates the null of zero paired mean.
    p=(1+np.sum(np.abs(means-x.mean())>=abs(x.mean())))/(B+1)
    return lo*252,hi*252,p

def main():
    freeze=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==freeze['config_sha256']
    for x in freeze['inputs']+freeze['sources']:assert sha(x['path'])==x['sha256']
    schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date','execution_date']);assert sha(DEST/'schedule.csv')==freeze['schedule_sha256']
    anchor=schedule.signal_date.min();raw=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    tr=pd.DataFrame(raw['items'],columns=raw['fields']);tr=tr.assign(date=pd.to_datetime(tr.trade_date)).set_index('date').sort_index().close
    accounts={};receipts={};checks=[];inventory=[];holdpaths={}
    def check(name,condition):checks.append(dict(check=name,passed=bool(condition)))
    for spec in specs():
        k=spec['account'];rp=DEST/'accounts'/f'{k}.json';r=json.loads(rp.read_text());cp=rp.with_suffix('.csv')
        f=pd.read_csv(cp,parse_dates=['date']).set_index('date').sort_index();accounts[k]=f;receipts[k]=r
        check(k+'_hashes',sha(cp)==r['nav_sha256'] and sha(r['orders_path'])==r['orders_sha256'] and sha(r['holdings_path'])==r['holdings_sha256'])
        check(k+'_freeze',r['config_sha256']==freeze['config_sha256'] and r['predictions']==freeze['predictions'])
        check(k+'_initial',str(f.index.min().date())=='2021-01-11')
        if r['failures']:check(k+'_stop',f.index.max()<pd.Timestamp(r['failures'][0]['date']))
        z=pd.read_parquet(r['orders_path']);delta=z.units_after-z.units_before
        check(k+'_execution_gate',not ((delta>1e-10)&(~z.can_buy|~z.current_member)).any() and not ((delta< -1e-10)&~z.can_sell).any())
        planned=schedule.loc[schedule.frequency.eq(r['frequency'])&schedule.phase.eq(r['phase']),'execution_date']
        check(k+'_scheduled_only',set(z.date).issubset(set(planned)))
        z['bv']=delta.clip(lower=0)*z.qfq_open;z['sv']=(-delta).clip(lower=0)*z.qfq_open
        g=z.groupby('date').agg(bv=('bv','sum'),sv=('sv','sum'),cb=('cash_before','first'),ca=('cash_after','first'))
        bf,sf=np.array(protocol()['costs_bps'][r['cost']])/10000
        check(k+'_cash_fee_conservation',(g.cb+g.sv*(1-sf)-g.bv*(1+bf)-g.ca).abs().max()<1e-8)
        ix=f.index.intersection(g.index);check(k+'_fee_record',np.allclose(f.loc[ix,'fees'],g.loc[ix,'bv']*bf+g.loc[ix,'sv']*sf,atol=1e-10))
        h=pd.read_parquet(r['holdings_path']);h['value']=h.synthetic_units*h.valuation_close
        values=h.groupby('date').value.sum().reindex(f.index,fill_value=0)
        check(k+'_nav',np.allclose(values+f.nav*f.cash_weight,f.nav,atol=1e-9) and f.cash_weight.min()>=-1e-9)
        tw=z.loc[z.target_weight>0].groupby('date').target_weight.agg(['min','max','sum'])
        check(k+'_equal_targets',np.allclose(tw['min'],tw['max'],atol=1e-12) and np.allclose(tw['sum'],1.,atol=1e-10))
        fail=r['failures'][0] if r['failures'] else {}
        inventory.append({**spec,'end':f.index.max(),'days':len(f),'failure_date':fail.get('date'),'failure_reason':fail.get('reason'),'instruments':fail.get('instruments')})
        if r['cost']=='main':holdpaths[k]=r['holdings_path']
    inv=pd.DataFrame(inventory);inv.to_csv(DEST/'account_inventory.csv',index=False)
    members={
        'control':[s['account'] for s in specs() if s['group']=='control'],
        'phase':[s['account'] for s in specs() if s['frequency']=='1m' and s['buffer'] is None],
        'buffer':[s['account'] for s in specs() if s['model']!='EW' and s['phase']==1],
    }
    ends={name:min(accounts[k].index.max() for k in keys) for name,keys in members.items()}
    save_json(DEST/'comparison_periods.json',dict(anchor=anchor,input_end=tr.index.max(),family_ends=ends,definition='minimum available end of every account and cost in each family'))
    metric=[];monthly=[]
    def measure(k,end,scope):
        f=accounts[k].loc[:end];r=receipts[k];b=tr.reindex(f.index)/tr.loc[anchor];assert b.notna().all()
        v=stats(f.nav,b);flow=f.buy+f.sell;initial=flow.loc[flow>1e-12].iloc[0]
        metric.append(dict(account=k,model=r['model'],frequency=r['frequency'],phase=r['phase'],buffer=r['buffer'],cost=r['cost'],scope=scope,end=end,**v,annual_one_way_turnover=.5*(flow.sum()-initial)*252/len(f),mean_holdings=f.holdings.mean(),mean_cash=f.cash_weight.mean(),total_fees=f.fees.sum()))
    for k,f in accounts.items():
        measure(k,f.index.max(),'native')
        for family,keys in members.items():
            if k in keys:measure(k,ends[family],family)
        nr=returns(f.nav);br=returns(tr.reindex(f.index)/tr.loc[anchor])
        for period in pd.period_range(anchor,tr.index.max(),freq='M'):
            ids=f.index[f.index.to_period('M')==period]
            base={x:receipts[k][x] for x in ['account','model','frequency','phase','buffer','cost']};base.update(month=str(period))
            if not len(ids):monthly.append({**base,'status':'BLOCKED','days':0});continue
            a=(1+nr.loc[ids]).prod()-1;b=(1+br.loc[ids]).prod()-1
            partial=period==anchor.to_period('M') or (period==f.index.max().to_period('M') and f.index.max()<period.end_time.normalize())
            monthly.append({**base,'start':ids.min(),'end':ids.max(),'days':len(ids),'net_return':a,'benchmark_return':b,'excess_difference':a-b,'status':'PARTIAL' if partial else 'FULL'})
    met=pd.DataFrame(metric);met.to_csv(DEST/'metrics.csv',index=False);pd.DataFrame(monthly).to_csv(DEST/'monthly_returns.csv',index=False)
    pair=[]
    def compare(a,b,family,scope,end):
        f=accounts[a].loc[:end];g=accounts[b].loc[f.index];delta=returns(f.nav)-returns(g.nav);lo,hi,p=uncertainty(delta)
        ra=receipts[a];rb=receipts[b];n=len(f)
        def turnover(z):flow=z.buy+z.sell;return .5*(flow.sum()-flow.loc[flow>1e-12].iloc[0])*252/n
        pair.append(dict(family=family,scope=scope,account=a,baseline=b,model=ra['model'],frequency=ra['frequency'],phase=ra['phase'],buffer=ra['buffer'],cost=ra['cost'],end=end,sessions=n,cagr_difference=f.nav.iloc[-1]**(252/n)-g.nav.iloc[-1]**(252/n),relative_cagr=(f.nav.iloc[-1]/g.nav.iloc[-1])**(252/n)-1,annual_mean_delta=delta.mean()*252,ci_low=lo,ci_high=hi,p_raw=p,turnover_delta=turnover(f)-turnover(g)))
    requests=[]
    for s in specs():
        k=s['account'];m=s['model'];freq=s['frequency'];phase=s['phase'];cost=s['cost']
        if s['group']=='control' and m!='EW':requests.append((k,key('EW',freq,cost=cost),'control','control'))
        if s['group']=='phase':
            requests.append((k,key(m,cost=cost),'phase','phase'))
            if m!='EW':requests.append((k,key('EW',phase=phase,cost=cost),'phase_selection','phase'))
        if s['group']=='buffer':requests.append((k,key(m,freq,cost=cost),'buffer','buffer'))
    for a,b,family,parent in requests:
        compare(a,b,family,'family_common',ends[parent])
        end=min(accounts[a].index.max(),accounts[b].index.max())
        if end!=ends[parent]:compare(a,b,family,'pair_common',end)
    pairs=pd.DataFrame(pair);pairs['p_holm']=np.nan
    for _,g in pairs.groupby(['family','scope','cost']):
        v=g.p_raw.dropna().sort_values();adjusted=np.maximum.accumulate(v.to_numpy()*np.arange(len(v),0,-1)).clip(0,1);pairs.loc[v.index,'p_holm']=adjusted
    pairs.to_csv(DEST/'paired_comparisons.csv',index=False)
    # Monthly holdings and industry deviations, on same dates against matched EW.
    industry=pd.read_parquet(PRIVATE/'industry.parquet');industry['instrument']=industry.ts_code.str[-2:]+industry.ts_code.str[:6];industry['start']=pd.to_datetime(industry.in_date);industry['end']=pd.to_datetime(industry.out_date).fillna(pd.Timestamp('2100-01-01'))
    common=min(ends.values());calendar=accounts[key('EW','1w')].loc[:common].index
    snapdates=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).last().tolist();indmap={}
    for d in snapdates:
        h=industry.loc[(industry.start<=d)&(industry.end>d)].groupby('instrument').l1_code.agg(lambda x:next(iter(set(x))) if len(set(x))==1 else 'UNKNOWN');indmap[d]=h.to_dict()
    exposure=[]
    for k,hpath in holdpaths.items():
        h=pd.read_parquet(hpath);h=h.loc[h.date.isin(snapdates)].copy();h['industry']=[indmap[d].get(s,'UNKNOWN') for d,s in zip(h.date,h.instrument)]
        for (date,ind),g in h.groupby(['date','industry']):exposure.append(dict(account=k,date=date,industry=ind,weight=g.weight.sum()))
    ex=pd.DataFrame(exposure)
    # Zero exposure is a real zero, not a missing month in the mean.
    grid=pd.MultiIndex.from_product([list(holdpaths),snapdates,sorted(ex.industry.unique())],names=['account','date','industry'])
    ex=ex.set_index(['account','date','industry']).reindex(grid,fill_value=0).reset_index()
    ex.to_csv(DEST/'monthly_industry_weights.csv',index=False)
    expairs=[]
    for k in holdpaths:
        r=receipts[k]
        if r['model']=='EW':continue
        bk=key('EW',r['frequency'],r['phase']);a=ex.loc[ex.account.eq(k)].set_index(['date','industry']).weight;b=ex.loc[ex.account.eq(bk)].set_index(['date','industry']).weight
        delta=a.subtract(b,fill_value=0)
        for (date,ind),value in delta.items():expairs.append(dict(account=k,baseline=bk,date=date,industry=ind,active_weight=value))
    pd.DataFrame(expairs).to_csv(DEST/'monthly_industry_deviations.csv',index=False)
    check('126_accounts',len(accounts)==126);check('original_sources_unchanged',all(sha(x['path'])==x['sha256'] for x in freeze['inputs']+freeze['sources']))
    result=dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',checks=checks,accounts=len(accounts),size_exposure='NOT_EVALUATED: no certified time-matched market-cap panel in frozen inputs; no new data acquired',uncertainty='two-sided centered circular block bootstrap; Holm within family/scope/cost; native and pairwise longer horizons are supplementary')
    save_json(DEST/'validation.json',result);assert result['status']=='PASS'
    print('PASS',len(checks),'checks; family ends',ends,flush=True)

if __name__=='__main__':main()
