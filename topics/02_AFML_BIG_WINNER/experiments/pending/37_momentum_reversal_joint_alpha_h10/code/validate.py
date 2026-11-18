"""Independent source, model replay, trade ledger and event-account reconciliation."""
import sys,json
import numpy as np
import pandas as pd
from core import *
from data_models import predict

def run():
    frozen=verify_freeze();checks=[]
    def check(name,value,detail=None):
        if not bool(value):raise AssertionError((name,detail))
        checks.append(dict(check=name,status='PASS',detail=detail))
    check('all_frozen_inputs_unchanged',True,len(frozen['inputs']))
    f=pd.read_parquet(CACHE/'features.parquet');p=pd.read_parquet(CACHE/'predictions.parquet')
    folds=pd.read_csv(OUT/'folds.csv',parse_dates=['cutoff','max_label_maturity','inner_last_exit','validation_first_entry'])
    check('all_registered_fits_available',folds.status.eq('OK').all(),folds.status.value_counts().to_dict())
    check('mature_training', (folds.max_label_maturity<=folds.cutoff).all())
    check('purged_inner_training',(folds.inner_last_exit<folds.validation_first_entry).all())
    check('minimum_common_validation',folds.validation_dates.ge(12).all())
    for r in folds.itertuples():
        path=EP/r.model_path;check('model_hash:'+path.name,sha(path)==r.model_sha256)
        model=json.loads(path.read_text());test=f.loc[(f.offset==r.offset)&f.signal_date.dt.to_period('Q').astype(str).eq(r.fold)]
        expected=p.loc[(p.scheme==r.scheme)&(p.offset==r.offset)&p.fold.eq(r.fold),['signal_date','instrument',r.model]]
        got=test[['signal_date','instrument']].copy();got['replay']=predict(test,model)
        joined=expected.merge(got,on=['signal_date','instrument'],validate='one_to_one')
        err=float(abs(joined[r.model]-joined.replay).max())
        check('prediction_replay:'+path.name,err<1e-12,err)
    targets=pd.read_parquet(CACHE/'targets.parquet');check('exact_H10_target_endpoints',(targets.exit_idx-targets.entry_idx).eq(10).all())
    check('no_target_leverage',targets.groupby(['scheme','offset','model','portfolio','signal_date']).weight.sum().le(1+1e-12).all())
    check('target_unique_security',not targets.duplicated(['scheme','offset','model','portfolio','signal_date','instrument']).any())
    ranks=pd.read_parquet(CACHE/'rankings.parquet')
    for k,g in ranks.groupby(['scheme','offset','signal_date','model']):
        counts=g.decile.value_counts()
        check('ten_groups:'+str(k),len(counts)==10 and counts.max()-counts.min()<=1)
        check('rank_order:'+str(k),g.groupby('decile').score.min().is_monotonic_increasing)
    daily=pd.read_parquet(CACHE/'daily_accounts.parquet')
    check('cash_nonnegative',daily.cash.ge(-1e-10).all())
    check('daily_self_financing',daily.accounting_residual.abs().max()<1e-9,float(daily.accounting_residual.abs().max()))
    summaries=pd.read_csv(OUT/'accounts.csv');events=pd.read_csv(OUT/'events.csv',parse_dates=['entry_date','exit_date'])
    details=pd.read_parquet(CACHE/'event_stock_details.parquet')
    profit=details.groupby(['scheme','offset','model','portfolio','cost','signal_date']).net_stock_profit.agg(lambda x:x.sum() if x.notna().all() else np.nan)
    ev=pd.read_csv(OUT/'events.csv',parse_dates=['signal_date','entry_date','exit_date'])
    ev=ev.loc[ev.cost.eq('main')].set_index(['scheme','offset','model','portfolio','cost','signal_date'])
    joined=ev.join(profit.rename('stock_profit'))
    known=joined.loc[joined.complete_exit]
    check('event_stock_profit_adds_to_net_return',np.max(abs(known.net_return-known.stock_profit))<1e-10)
    ledger=CACHE/'ledgers';ledger_count=0;product_count=0
    for orderfile in sorted(ledger.glob('*_orders.parquet')):
        name=orderfile.name[:-len('_orders.parquet')];holds=pd.read_parquet(ledger/(name+'_holdings.parquet'))
        orders=pd.read_parquet(orderfile);d=daily.loc[daily.account==name].sort_values('date').set_index('date')
        traded=orders.loc[orders.side.isin(['BUY','SELL'])].copy()
        check('actual_lot_age_H10_or_overdue:'+name,traded.loc[traded.side=='SELL','actual_age'].ge(10).all())
        traded['cash_flow']=np.where(traded.side=='BUY',-traded.value-traded.fee,traded.value-traded.fee)
        cash=1+traded.groupby('date').cash_flow.sum().reindex(d.index,fill_value=0).cumsum()
        check('cash_ledger:'+name,float(abs(cash-d.cash).max())<1e-9)
        traded['signed_units']=np.where(traded.side=='BUY',traded.units,-traded.units)
        if len(traded):
            pos=traded.pivot_table(index='date',columns='instrument',values='signed_units',aggfunc='sum',fill_value=0).reindex(d.index,fill_value=0).cumsum()
            actual=holds.pivot(index='date',columns='instrument',values='units').reindex(index=d.index,columns=pos.columns).fillna(0) if len(holds) else pos*0
            check('positions_ledger:'+name,float(np.max(abs(pos.to_numpy()-actual.to_numpy())))<1e-9)
        marked=holds.assign(value=holds.units*holds.mark).groupby('date').value.sum().reindex(d.index,fill_value=0)
        check('nav_ledger:'+name,float(abs(cash+marked-d.nav).max())<1e-9)
        check('return_compounding:'+name,abs(float(np.prod(1+d.return_))-float(d.nav.iloc[-1]))<1e-9)
        row=summaries.loc[summaries.account==name].iloc[0]
        subset=events.loc[(events.scheme==row.scheme)&(events.offset==row.offset)&(events.model==row.model)&(events.portfolio==row.portfolio)&(events.cost=='main')&
                          (events.entry_date>=pd.Timestamp(row.start))&(events.exit_date<=pd.Timestamp(row.end))]
        if row.valuation_complete and subset.complete_exit.all() and len(subset):
            expected=float(np.prod(1+subset.net_return))
            check('independent_events_vs_continuous:'+name,abs(expected-float(d.nav.iloc[-1]))<1e-8)
            product_count+=1
        ledger_count+=1
    tests=pd.read_csv(OUT/'primary_tests.csv')
    check('primary_family_size',tests.groupby('scope').size().eq(6).all())
    check('unknown_controls_not_zero',pd.read_csv(OUT/'conditional_information.csv').loc[lambda x:x.n_controls==0,'ic'].isna().all())
    for item in json.loads((EP/'notes/source_snapshot.json').read_text())['files']:
        check('EP36_design_source_unchanged:'+item['path'],sha(EP.parents[4]/item['path'])==item['sha256'])
    dump(MAN/'final_validation.json',clean(dict(status='PASS',checks=checks,count=len(checks),model_replays=len(folds),ledger_accounts=ledger_count,
                                               event_account_exact_reconciliations=product_count,source_files=len(frozen['inputs']),
                                               economic_certification=False,quality='Historical-proxy; tests establish implementation consistency')))
    print('validation passed',len(checks),'models',len(folds),'ledgers',ledger_count,'event products',product_count,flush=True)

if __name__=='__main__':run()
