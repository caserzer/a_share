from shared import *
from wide_sources import CACHE
from core import sha
def main():
    days=pd.read_parquet(PRIVATE/'market.parquet').index
    windows=pd.read_parquet(OUT/'all_windows.parquet');daily=pd.concat([pd.read_parquet(OUT/(n+'.parquet')) for n in ['daily','wide_daily']])
    key=['scope','model','cost']
    indexed=windows.set_index(key).sort_index()
    for k,d in daily.groupby(key):
        g=indexed.loc[k].sort_values('entry_idx');d=d.sort_values('date')
        np.testing.assert_allclose(np.prod(1+g.net),d.nav.iloc[-1],rtol=0,atol=1e-10)
        mul={'base':1,'zero':0,'double':2}[k[-1]]
        np.testing.assert_allclose(d.fees,(.001*d.buy+.002*d.sell)*mul,atol=1e-12)
        np.testing.assert_allclose(d.cash,1+(d.sell-d.buy-d.fees).cumsum(),atol=1e-10)
    # Sealed complete day-by-day reference ledger, including holdings-constrained execution.
    for scope in ['later','primary']:
        old=pd.read_parquet(ROUNDS/f'133_midpoint_matched_orders/results/{scope}_daily.parquet').query("phase==0 and model=='original'")
        new=daily.query("model=='original' and scope==@scope and cost=='base'").merge(old,on='date')
        for field in ['cash','buy','sell','nav']:
            np.testing.assert_allclose(new[field+'_x'],new[field+'_y'],atol=1e-10)
    pairs=pd.read_parquet(OUT/'fold_pairs.parquet')
    assert pairs.groupby('quarter').size().eq(78*77//2).all()
    assert pairs.query("first=='ret_lag0' and second=='mom1'").exact.all()
    trials=pd.read_parquet(OUT/'search.parquet')
    assert (trials.last_exit<pd.PeriodIndex(trials.quarter,freq='Q').start_time).all()
    assert trials.groupby(['objective','quarter']).size().eq(15).all()
    matched=pd.read_csv(OUT/'matched_incoming.csv')
    np.testing.assert_allclose(matched.target_incoming,matched.uniform_incoming,atol=1e-12)
    interaction=[];monthly=[]
    for (scope,cost),g in windows.groupby(['scope','cost']):
        if scope=='primary':continue
        p=g.pivot(index='entry_idx',columns='model',values='net')
        diff=(p.transfer_selection-p.transfer)-(p.selection-p.original)
        assert diff.notna().all()
        a=diff.to_numpy()*1e4;rng=np.random.default_rng(3803)
        idx=(rng.integers(len(a),size=(10000,(len(a)+2)//3,1))+np.arange(3))%len(a)
        lo,hi=np.quantile(a[idx.reshape(10000,-1)[:,:len(a)]].mean(axis=1),[.025,.975])
        interaction.append(dict(scope=scope,cost=cost,n=len(a),net_interaction_bp=a.mean(),ci_low=lo,ci_high=hi))
        mm=daily[(daily.scope==scope)&(daily.cost==cost)].pivot(index='date',columns='model',values='nav')
        mm=mm.groupby(mm.index.to_period('M')).last();mr=mm/mm.shift().fillna(1)-1
        v=(mr.transfer_selection-mr.transfer)-(mr.selection-mr.original)
        monthly.extend(dict(scope=scope,cost=cost,month=str(k),net_interaction_bp=x*1e4) for k,x in v.items())
    pd.DataFrame(interaction).to_csv(OUT/'interaction.csv',index=False)
    pd.DataFrame(monthly).to_csv(OUT/'interaction_monthly.csv',index=False)
    coverage=pd.read_parquet(OUT/'wide_scores.parquet').groupby('signal_date').size().rename('eligible').reset_index()
    got=pd.read_csv(OUT/'wide_coverage.csv',parse_dates=['signal_date'])
    evidence=[]
    for model in ['transfer','wide_train','transfer_selection']:
        for r in coverage.itertuples():
            s='primary' if days[days.get_loc(r.signal_date)+1]<pd.Timestamp('2025-03-03') else 'later'
            h=got[(got.model==model)&(got.signal_date==r.signal_date)]
            exact=h[h.scope==s];restart=h[h.scope=='primary_restart']
            row=exact if len(exact) else restart
            evidence.append(dict(model=model,signal_date=r.signal_date,original_scope=s,members=800,eligible=r.eligible,
                                 account_scope=row.scope.iloc[0] if len(row) else None,
                                 positions=row.actual_positions.iloc[0] if len(row) else None,
                                 new_buy_names=row.buy_filled_names.iloc[0] if len(row) else None,
                                 reason='' if len(exact) else 'SZ000540 valuation gap; independent restart' if len(restart) else 'SZ000540 unpriced on 2023-06-16'))
    pd.DataFrame(evidence).to_csv(OUT/'wide_calendar.csv',index=False)
    raw=pd.read_parquet(CACHE/'market/wide_features.parquet');small=outer()
    both=small[KEY+COLS].merge(raw[KEY+COLS],on=KEY,suffixes=('_300','_800'),validate='1:1')
    parity=[]
    for c in COLS:
        a=both[c+'_300'];b=both[c+'_800'];np.testing.assert_allclose(a,b,atol=1e-12,rtol=0,equal_nan=True)
        parity.append(dict(feature=c,common_rows=len(both),known=a.count(),missing_mask_equal=a.isna().equals(b.isna()),max_abs_error=(a-b).abs().max()))
    pd.DataFrame(parity).to_csv(OUT/'wide_feature_parity.csv',index=False)
    source_files=[PRIVATE/(k+'.parquet') for k in ['features','labels','daily_members','qfq_close','qfq_open','qfq_high','qfq_low','close','open','money','volume','turnover_rate','opening_trade_status_v2','limits/daily','suspensions/daily','industry','market']]
    source_files += [OLD/'outputs/original_78_features.csv',OLD/'model.py',OLD/'local_cache/h10_features.parquet',OLD/'local_cache/predictions.parquet',EP/'outputs/local_cache/labels.parquet',ROUNDS/'51_earlier_replication/results/models.json',PRIVATE/'net_excess_20261116/H00300.CSI.json',ROUNDS/'64_mature_group_switch/account.py',EP/'code/accounts.py',PRIVATE.parent/'src/features.py',HERE.parent/'THREE_TRACK_EXPERIMENT_PLAN.md']
    source_files+=list((OLD/'local_cache/models').glob('*_RANK_MSE_78.json'))
    receipt=dict(input_sha256={str(f.relative_to(HERE.parents[3])):sha(f) for f in source_files},script_sha256={f.name:sha(f) for f in HERE.glob('*.py')},output_sha256={f.name:sha(f) for f in OUT.iterdir() if f.is_file() and f.name!='verification.json'},audited_accounts=daily.groupby(key).ngroups,training_folds=trials.quarter.nunique(),official_month_end_matches=len(pd.read_csv(OUT/'monthly_constituent_checks.csv')),shared_feature_rows=len(both))
    (OUT/'verification.json').write_text(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
