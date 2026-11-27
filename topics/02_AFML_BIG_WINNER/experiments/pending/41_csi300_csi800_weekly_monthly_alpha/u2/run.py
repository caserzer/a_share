"""Run U2 once from the sealed scores and historical source snapshots."""
from common import *

OUT=HERE/'results'
OUT.mkdir(exist_ok=True)
RULES=['low_price','low_adv','two_down']

def main():
    s=Study()
    s.style()
    limit=pd.read_parquet(LOCAL/'limits/daily.parquet')
    limit['instrument']=limit.ts_code.str[-2:]+limit.ts_code.str[:6]
    limit['date']=pd.to_datetime(limit.trade_date)
    lim=limit.pivot(index='date',columns='instrument',values='down_limit').reindex_like(s.raw).to_numpy()
    valid=np.isfinite(lim)&(lim>0)&s.raw.notna().to_numpy()
    close_down=np.isclose(s.raw.to_numpy(),lim,atol=.00001,rtol=0)&valid
    rawopen=pd.read_parquet(LOCAL/'open.parquet').reindex_like(s.raw).to_numpy()
    down_open=np.isclose(rawopen,lim,atol=.00001,rtol=0)&(lim>0)
    plans={'baseline':s.blank(31)}
    for r in RULES:
        for kind in ['rule','supported','risk_control']:
            plans[f'{r}_{kind}']=s.blank(31)
    rows=[]; audits=[]; removals=[]; changes=[]
    for e,g in s.ranks.groupby('entry_idx'):
        ids=s.symbols.get_indexer(g.instrument)
        k=s.ks[e]; base=ids[:k]; plans['baseline'][e,:k]=base
        adv=pct(s.adv.iloc[e-1,ids].to_numpy())
        low_adv_n=int(np.isfinite(adv).sum()//10)
        low_adv=np.zeros(len(ids),bool)
        low_adv[np.lexsort((-ids,adv))[:low_adv_n]]=True
        cap=pct(s.cap[e-1,ids])
        sector=s.sectors[e-1,ids]
        price=s.raw.iloc[e-1,ids].to_numpy()
        all_known=np.ones(len(ids),bool)
        known=[np.isfinite(price),np.isfinite(adv),valid[e-1,ids]&valid[e-2,ids]]
        flags=[price<3,low_adv,close_down[e-1,ids]&close_down[e-2,ids]]
        # Outcome labels are joined after fixing all flags/ranks. Missing labels
        # leave both selection and replacement seats intact.
        ret=s.m.o[e+10,ids]/s.m.o[e,ids]-1
        winner=pct(ret)>.9
        for rule,mask,ok in zip(RULES,flags,known):
            dropped=np.flatnonzero(mask[:k])
            keep=np.flatnonzero(~mask[:k])
            adds=np.flatnonzero(~mask & (np.arange(len(ids))>=k))[:len(dropped)]
            l,r=match(dropped,keep,sector,cap,adv)
            for kind,exclude,new in [('rule',dropped,adds),('supported',l,adds[:len(l)]),('risk_control',r,adds[:len(l)])]:
                pick=np.r_[base[~np.isin(np.arange(k),exclude)],ids[new]]
                assert len(np.unique(pick))==k
                plans[f'{rule}_{kind}'][e,:k]=pick
            changes.append((e,rule,base,ids[adds]))
            rows.append(dict(signal_date=s.days[e-1],entry_idx=e,rule=rule,eligible=len(ids),valid=int(ok.sum()),pool_flag=int(mask.sum()),
                             head=k,head_valid=int(ok[:k].sum()),removed=len(dropped),matched=len(l),share_age_days=s.share_age[e-1],
                             removed_open_down=down_open[e,ids[dropped]].sum(),removed_h10_known=np.isfinite(ret[dropped]).sum(),
                             removed_winner=winner[dropped].sum(),zts_removed=int('SZ000540' in s.symbols[ids[dropped]])))
            for i,j in zip(dropped,adds):
                removals.append((s.days[e-1],rule,s.symbols[ids[i]],s.symbols[ids[j]],1/k,ret[i],ret[j],winner[i] if np.isfinite(ret[i]) else None,
                                 down_open[e,ids[i]],np.any(close_down[e:e+10,ids[i]]),s.valid_buy[e,ids[i]],s.valid_buy[e,ids[j]]))
            for i,j in zip(l,r):
                audits.append((s.days[e-1],rule,s.symbols[ids[i]],s.symbols[ids[j]],sector[i],cap[i]-cap[j],adv[i]-adv[j]))
    cov=pd.DataFrame(rows)
    cov.to_parquet(OUT/'signal_coverage.parquet',index=False)
    pd.DataFrame(audits,columns='date rule removed matched sector d_cap_pct d_adv_pct'.split()).to_parquet(OUT/'risk_pairs.parquet',index=False)
    pd.DataFrame(removals,columns='date rule removed substitute weight h10_old h10_new winner_old open_down_old any_observed_h10_down_close_old buyable_old buyable_new'.split()).to_parquet(OUT/'seat_changes.parquet',index=False)
    pd.DataFrame([dict(arm=name,entry_idx=e,targets=list(s.symbols[arr[e,arr[e]>=0]])) for name,arr in plans.items() for e in s.ks.index if np.any(arr[e]>=0)]).to_parquet(OUT/'targets.parquet',index=False)
    daily=[]; orders=[]; caps=[]; parity=[]; gaps=[]; months=[]; risks=[]
    baseline_ref=pd.read_parquet(OUT800/'strict_daily.parquet').query('size=="same300" and mode=="refit" and arm=="R" and path=="common"')
    calendar=s.days
    for name,plan in plans.items():
        for mark,periods in [('strict',PERIODS),('zero',dict(primary=PRIMARY,later=PERIODS['later'])),('last',dict(primary=PRIMARY,later=PERIODS['later']))]:
            for seg,period in periods.items():
                d,o,gap=s.replay(plan,period,mark=mark,keep_orders=mark=='strict')
                if gap:gaps.append(dict(arm=name,segment=seg,mark=mark,**gap))
                daily.append(d.reset_index().assign(arm=name,mark=mark,segment=seg))
                if mark!='strict':continue
                if name=='baseline':
                    ref=baseline_ref[(baseline_ref.scope==('later' if seg=='later' else 'primary'))&(baseline_ref.segment==(seg=='restart'))].set_index('date')
                    delta=(ref.loc[d.index,['nav','fee','cash','crossed']]-d[['nav','fee','cash','crossed']]).abs().to_numpy().max()
                    assert delta<1e-10
                    parity.append((seg,len(d),delta))
                orders.append(o.assign(arm=name,segment=seg))
                for month,v in monthly(d,calendar).items():months.append((name,seg,month,v))
                for aum in [1e6,1e7,1e8,1e9]:
                    amount=o.net_order.abs()
                    adv=o.adv20_signal.where(o.adv20_signal>0)
                    part=amount*aum/adv;rate=.001*np.sqrt(part/.01).clip(upper=10)
                    expense=amount/o.opening_nav*rate
                    caps.append(dict(arm=name,segment=seg,initial_cny=aum,orders=len(o),missing_adv=part.isna().sum(),
                                     missing_value_share=amount[part.isna()].sum()/amount.sum(),over_1pct=(part>.01).sum(),
                                     over_1pct_value_share=amount[part>.01].sum()/amount.sum(),max_known_participation=part.max(),
                                     impact_low_bp_per_day=expense.fillna(0).sum()/len(d)*1e4,
                                     impact_high_bp_per_day=expense.fillna(amount/o.opening_nav*.01).sum()/len(d)*1e4))
        # Audit the actual missing mark without imposing the common cutoff.
        _,_,gap=s.replay(plan,PRIMARY)
        if gap:gaps.append(dict(arm=name,segment='uninterrupted',mark='strict',**gap))
    all_daily=pd.concat(daily)
    all_daily.to_parquet(OUT/'accounts.parquet',index=False)
    pd.concat(orders).to_parquet(OUT/'net_orders.parquet',index=False)
    pd.DataFrame(caps).to_csv(OUT/'capacity.csv',index=False)
    pd.DataFrame(parity,columns='segment days max_abs_error'.split()).to_csv(OUT/'ep40_parity.csv',index=False)
    pd.DataFrame(gaps).to_csv(OUT/'gaps.csv',index=False)
    print('Deterministic accounts verified. Running 200 placebo paths per rule.',flush=True)
    changes={rule:[(e,base,adds) for e,r,base,adds in changes if r==rule and len(adds)] for rule in RULES}
    for seed in range(1,201):
        for rule in RULES:
            plan=plans['baseline'].copy()
            for e,base,adds in changes[rule]:
                # One date-specific ordering of codes, shared by all three stress filters.
                rng=np.random.default_rng(np.random.SeedSequence([seed,int(s.days[e-1].strftime('%Y%m%d'))]))
                order=np.argsort(rng.random(len(base)))[0:len(adds)]
                plan[e,:len(base)]=np.r_[np.delete(np.sort(base),order),adds]
            for seg,period in PERIODS.items():
                d,_,gap=s.replay(plan,period)
                risks.append(dict(seed=seed,rule=rule,segment=seg,gap=gap['date'] if gap else None,days=len(d),net=d.nav.iloc[-1]-1))
                for month,v in monthly(d,calendar).items():months.append((f'{rule}_random_{seed}',seg,month,v))
    pd.DataFrame(risks).to_csv(OUT/'random_paths.csv',index=False)
    mo=pd.DataFrame(months,columns='arm segment month net'.split())
    mo=mo.merge(mo.query('arm=="baseline"')[['segment','month','net']].rename(columns={'net':'baseline'}),on=['segment','month'])
    mo['gap_bp']=1e4*(mo.net-mo.baseline)
    mo['registered_month']=~((mo.segment=='later')&(mo.month=='2025-03'))
    mo.to_parquet(OUT/'paired_months.parquet',index=False)
    det=mo[~mo.arm.str.contains('random')]
    det.groupby(['arm','segment']).gap_bp.agg(['mean','size']).to_csv(OUT/'including_start_month.csv')
    mo=mo[mo.registered_month]
    summary=mo[~mo.arm.str.contains('random')].groupby(['arm','segment']).agg(months=('month','size'),mean_gap_bp=('gap_bp','mean')).reset_index()
    summary.to_csv(OUT/'summary.csv',index=False)
    for rule in RULES:
        z=mo[mo.arm.str.startswith(rule+'_random')].groupby(['arm','segment']).gap_bp.mean().groupby('segment').quantile([.025,.5,.975])
        print(rule,z,flush=True)
    sources=[OUT800/'scores.parquet',DEST/'daily_scores.parquet',LOCAL/'limits/daily.parquet',LOCAL/'suspensions/daily.parquet',
             PRIVATE36/'industry.parquet',next(PENDING.glob('38_*/three_track/results/effective800.parquet')),
             REG/'config.yaml',HERE/'common.py',HERE/'book.cpp',Path(__file__)]
    sources += [LOCAL/(k+'.parquet') for k in ['close','open','qfq_close','qfq_open','money','opening_trade_status_v2']]
    receipt={str(p):sha(p) for p in sources+sorted(p for p in OUT.iterdir() if p.suffix!='.json')}
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(summary.to_string(index=False),flush=True)

if __name__=='__main__':main()
