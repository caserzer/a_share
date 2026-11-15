"""Fixed-stock valuation for frozen R04 selections, separate from executability."""
import pandas as pd
from common import *


def weighted_path(prices, weights):
    prices=np.asarray(prices,float);weights=np.asarray(weights,float)
    if prices.ndim!=2 or prices.shape[1]!=len(weights) or not np.isclose(weights.sum(),1):raise ValueError('invalid weights')
    if not np.isfinite(prices).all() or (prices<=0).any():return None
    relatives=prices/prices[0]
    wealth=relatives@weights
    return wealth,weights*relatives[-1]/wealth[-1]


def run():
    out=ROOT/'outputs/r06';intervals=pd.read_csv(ROOT/'outputs/r04/intervals.csv',parse_dates=['origin','entry','exit'])
    holdings=pd.read_parquet(ROOT/'outputs/r04/holdings.parquet');holdings['origin']=pd.to_datetime(holdings.origin)
    members_path=CACHE/'extension_v2/products/assignments.parquet'
    members=pd.read_parquet(members_path,columns=KEY+['month','date','security_id','instrument','unresolved'])
    assert not members.duplicated(['era','level','month','security_id']).any()
    evidence_path=EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json';ev=json.loads(evidence_path.read_text())
    assert sha(members_path)==ev['reads'][str(members_path)]
    bench=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;days=pd.DatetimeIndex(bench.index)
    reads={str(members_path):sha(members_path),str(evidence_path):sha(evidence_path)}
    for p in [ROOT/'outputs/r04/holdings.parquet',ROOT/'outputs/r04/intervals.csv']:reads[str(p)]=sha(p)
    ids=sorted(members.security_id.unique());si={sid:i for i,sid in enumerate(ids)}
    shape=(len(days),len(ids));prices=np.full(shape,np.nan);chains=np.full(shape,-1,dtype=np.int16)
    volume_good=np.zeros(shape,bool);buy=np.zeros(shape,np.uint8);sell=np.zeros(shape,np.uint8)
    paths={Path(p).stem:Path(p) for p in ev['reads'] if '/normalized/prices_qfq/' in p}
    for j,sid in enumerate(ids):
        p=paths[sid];h=sha(p);assert h==ev['reads'][str(p)];reads[str(p)]=h
        f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id','volume','volume_conflict','can_buy','can_sell']).set_index('date').reindex(days)
        prices[:,j]=pd.to_numeric(f.qfq_close).where(f.close_conflict.eq(False)&pd.to_numeric(f.qfq_close).gt(0))
        chains[:,j]=pd.factorize(f.factor_chain_id)[0]
        volume_good[:,j]=(pd.to_numeric(f.volume).gt(0)&f.volume_conflict.eq(False)).to_numpy()
        for name,array in [('can_buy',buy),('can_sell',sell)]:
            array[:,j]=np.where(f[name].eq(True),1,np.where(f[name].eq(False),2,0))
        if (j+1)%1500==0:print('READ STOCKS',j+1,len(ids),flush=True)
    member_lookup={k:g for k,g in members.groupby(['era','level','month','industry_code'],sort=False)}
    selection_lookup={k:g for k,g in holdings.groupby(['era','level','method','origin'],sort=False)}
    records=[];positions=[];daily=[];summaries=[]
    for key,schedule in intervals.groupby(['era','level','method']):
        era,level,method=key;drift={};ever=False;invalid=False;portfolio_daily=[];valid_records=[]
        for r in schedule.sort_values('origin').itertuples():
            rec=dict(era=era,level=level,method=method,origin=r.origin,entry=r.entry,exit=r.exit,r04_status=r.status,
                     r04_gross_return=getattr(r,'gross_return',np.nan))
            if r.status=='insufficient_signal_universe':
                if ever:invalid=True
                records.append(dict(rec,status='insufficient_signal_universe'));continue
            ever=True;sel=selection_lookup[(era,level,method,r.origin)];weights={};unresolved=0;missing=[];max_mdate=pd.NaT
            for row in sel.itertuples():
                g=member_lookup.get((era,level,r.origin.to_period('M'),row.industry_code))
                if g is None or len(g)==0:missing.append(row.industry_code);continue
                assert g.date.le(r.origin).all();max_mdate=max(max_mdate,g.date.max()) if pd.notna(max_mdate) else g.date.max()
                unresolved+=int(g.unresolved.max())
                for sid in g.security_id:weights[sid]=weights.get(sid,0)+row.weight/len(g)
            rec.update(unresolved_members=unresolved,missing_industries=';'.join(missing),n_stocks=len(weights),membership_max_date=max_mdate)
            if unresolved or missing or not weights:
                invalid=True;drift={};records.append(dict(rec,status='unresolved_membership'));continue
            assert np.isclose(sum(weights.values()),1)
            asset_ids=sorted(weights);cols=np.array([si[s] for s in asset_ids]);w=np.array([weights[s] for s in asset_ids])
            lo=days.get_loc(r.entry);hi=days.get_loc(r.exit);p=prices[lo:hi+1,cols];ch=chains[lo:hi+1,cols]
            stable=(ch==ch[0]).all(axis=0)&(ch[0]>=0)
            valid_price=np.isfinite(p).all(axis=0)&(p>0).all(axis=0)
            rec.update(missing_price_stocks=int((~valid_price).sum()),chain_change_stocks=int((~stable).sum()),
                endpoint_volume_bad_stocks=int((~volume_good[lo,cols]|~volume_good[hi,cols]).sum()),
                buy_unknown_stocks=int((buy[lo,cols]==0).sum()),sell_unknown_stocks=int((sell[hi,cols]==0).sum()),
                buy_disallowed_stocks=int((buy[lo,cols]==2).sum()),sell_disallowed_stocks=int((sell[hi,cols]==2).sum()),
                max_stock_weight=w.max(),effective_stocks=1/(w@w))
            for sid,weight in weights.items():positions.append(dict(era=era,level=level,method=method,origin=r.origin,security_id=sid,weight=weight))
            if not (stable&valid_price).all():
                invalid=True;drift={};records.append(dict(rec,status='missing_or_conflicting_stock_path'));continue
            wealth,terminal=weighted_path(p,w)
            names=set(weights)|set(drift);turn=sum(abs(weights.get(s,0)-drift.get(s,0)) for s in names)
            # Check actual direction of each rebalance, rather than treating retained stock as a fresh buy.
            gate_unknown_weight=0.;gate_false_weight=0.
            for sid in names:
                change=weights.get(sid,0)-drift.get(sid,0)
                if abs(change)<1e-12:continue
                gate=(buy if change>0 else sell)[lo,si[sid]]
                if gate==0:gate_unknown_weight+=abs(change)
                elif gate==2:gate_false_weight+=abs(change)
            drift=dict(zip(asset_ids,terminal));ret=wealth[-1]-1
            rec.update(status='valuation_complete_execution_unproven',gross_return=ret,turnover=turn,
                net20=(1-.002*turn)*wealth[-1]-1,net50=(1-.005*turn)*wealth[-1]-1,
                gate_unknown_turnover=gate_unknown_weight,gate_disallowed_turnover=gate_false_weight,
                gross_difference_vs_r04=ret-rec['r04_gross_return'])
            records.append(rec);valid_records.append(rec)
            portfolio_daily.append(dict(date=r.entry,gross=0.,net20=-.002*turn,net50=-.005*turn,benchmark=0.))
            for k in range(1,len(wealth)):
                pr=wealth[k]/wealth[k-1]-1
                portfolio_daily.append(dict(date=days[lo+k],gross=pr,net20=pr,net50=pr,benchmark=bench.iloc[lo+k]/bench.iloc[lo+k-1]-1))
        if not valid_records:continue
        portfolio_daily.append(dict(date=valid_records[-1]['exit'],gross=0.,net20=-.002,net50=-.005,benchmark=0.))
        rr=pd.DataFrame(portfolio_daily).groupby('date')[['gross','net20','net50','benchmark']].agg(lambda s:(1+s).prod()-1)
        for k,v in zip(['era','level','method'],key):rr[k]=v
        rr['whole_path_valid']=not invalid;daily.append(rr.reset_index())
        for cost in ['gross','net20','net50']:
            s=dict(era=era,level=level,method=method,cost=cost,whole_path_valid=not invalid,valid_intervals=len(valid_records),
                start=valid_records[0]['entry'],end=valid_records[-1]['exit'],executability_proven=False,
                mean_stock_turnover=np.mean([v['turnover'] for v in valid_records]),max_stock_weight=max(v['max_stock_weight'] for v in valid_records),
                min_effective_stocks=min(v['effective_stocks'] for v in valid_records),
                conditional_mean_interval_return=np.mean([v['gross_return' if cost=='gross' else cost] for v in valid_records]))
            if not invalid:
                nav=(1+rr[cost]).cumprod();years=(rr.index.max()-rr.index.min()).days/365.25
                s.update(cagr=nav.iloc[-1]**(1/years)-1,drawdown=(nav/nav.cummax().clip(lower=1)-1).min(),vol=rr[cost].std()*np.sqrt(252),
                    beta=rr[cost].cov(rr.benchmark)/rr.benchmark.var(),benchmark_cagr=(1+rr.benchmark).prod()**(1/years)-1)
            summaries.append(s)
    result=pd.DataFrame(records);result.to_csv(out/'intervals.csv',index=False)
    pd.DataFrame(positions).to_parquet(ROOT/'data/r06_stock_positions.parquet',index=False)
    pd.concat(daily,ignore_index=True).to_parquet(out/'daily_returns.parquet',index=False)
    pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False)
    js(out/'receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r06.json'),code_sha256=sha(__file__),source_hashes=reads,
        status_counts=result.status.value_counts().to_dict(),stock_partitions=len(ids),executability_proven=False,
        complete_portfolios=pd.DataFrame(summaries).query("cost=='net20' and whole_path_valid")[['era','level','method']].to_dict('records')))
    print(result.groupby(['era','level','status']).size().to_string(),flush=True)

if __name__=='__main__':run()
