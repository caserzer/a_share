"""Numerical, temporal and accounting checks for the new revision only."""
import json
import numpy as np
import pandas as pd
from run import ROOT, EP37, EP36, PRIVATE, CACHE, OUT, MAN, freeze, columns, config, sha, dump
from model import predict


def main():
    frozen=freeze(); count=0
    def check(condition,message):
        nonlocal count
        assert condition,message
        count+=1
    cols=columns()
    feats=pd.read_parquet(CACHE/'h10_features.parquet')
    pred=pd.read_parquet(CACHE/'predictions.parquet')
    folds=pd.read_csv(OUT/'folds.csv',parse_dates=['max_label_maturity','cutoff','inner_last_exit','validation_first_entry'])
    curve=pd.read_csv(OUT/'validation_checkpoints.csv')
    check(len(folds)==72,'72 final models')
    check((folds.max_label_maturity<=folds.cutoff).all(),'Outer maturity')
    check((folds.inner_last_exit<folds.validation_first_entry).all(),'Inner purge')
    check((folds.validation_dates>=12).all(),'Validation dates')
    check(not pred.duplicated(['signal_date','instrument']).any(),'Unique predictions')
    checks=[]
    for row in folds.itertuples():
        file=ROOT/row.model_path; check(sha(file)==row.model_sha256,'Model hash')
        m=json.loads(file.read_text());check(m['columns']==cols,'Original ordered78 preserved')
        f=feats.loc[feats.fold.eq(row.fold)].copy()
        actual=pred.loc[pred.fold.eq(row.fold)]
        check(f[['signal_date','instrument']].reset_index(drop=True).equals(actual[['signal_date','instrument']].reset_index(drop=True)),'Replay row order')
        err=np.max(np.abs(predict(f,m)-actual[row.model].to_numpy()))
        check(err<1e-12,'Saved prediction replay')
        if row.model=='RIC_78':
            candidates=curve.loc[curve.fold.eq(row.fold)&curve.step.isin(config()['optimizer']['selection_steps'])]
            chosen=candidates.sort_values(['validation_mean_rankic','step'],ascending=[False,True]).iloc[0]
            check(chosen.step==row.chosen_steps==m['trained_steps'],'Validation-only step selection')
            check(np.isclose(np.linalg.norm(m['coef']),1),'RIC coefficient scale')
        checks.append(dict(fold=row.fold,model=row.model,max_error=err))
    parity=pd.read_csv(OUT/'feature_parity.csv')
    check(len(parity)==78 and parity.missing_mask_equal.all() and parity.max_abs_error.eq(0).all(),'All original feature values and masks exactly match')
    replay=pd.read_csv(OUT/'original_E1_reproduction.csv')
    check(replay.max_prediction_error.max()<1e-10,'Original E1 forecasts reproduced')
    check(replay.train_rows.equals(replay.original_train_rows),'Original weekly rows recovered')
    # Labels independently recovered from raw endpoints; no endpoint substitution.
    close=pd.read_parquet(PRIVATE/'qfq_close.parquet');op=pd.read_parquet(PRIVATE/'qfq_open.parquet')
    labels=pd.read_parquet(EP37/'outputs/local_cache/labels.parquet')
    z=pred.loc[pred.exit_date.notna()].merge(labels.loc[labels.offset.eq(0),['signal_date','instrument','h10']],on=['signal_date','instrument'],validate='one_to_one')
    si=op.columns.get_indexer(z.instrument);a=op.to_numpy()
    expected=a[z.exit_idx.to_numpy(int),si]/a[z.entry_idx.to_numpy(int),si]-1
    check(np.allclose(expected,z.h10,equal_nan=True,rtol=0,atol=1e-14),'H10 endpoints')
    check((z.exit_idx-z.entry_idx).eq(10).all(),'Exact H10 horizon')
    target=pd.read_parquet(CACHE/'targets.parquet')
    check(np.allclose(target.groupby(['signal_date','model','portfolio']).weight.sum(),1),'Target budgets')
    check(target.exit_idx.sub(target.entry_idx).eq(10).all(),'Target horizons')
    ranks=pd.read_parquet(CACHE/'rankings.parquet')
    check(ranks.groupby(['signal_date','model']).decile.nunique().eq(10).all(),'All ten groups')
    check(ranks.groupby(['signal_date','model']).size().unstack().nunique(axis=1).eq(1).all(),'Common universe')
    for (date,mid),g in ranks.groupby(['signal_date','model']):
        ordered=g.sort_values(['score','instrument'])
        check(np.array_equal(ordered.decile,np.floor(10*np.arange(len(g))/len(g)).astype(int)+1),'Deciles from scores only')
    daily=pd.read_parquet(CACHE/'daily_accounts.parquet')
    check(daily.accounting_residual.abs().max()<1e-9,'Daily PNL identity')
    ledger_checks=[]
    for name,d in daily.loc[daily.valuation.eq('flat')&daily.cost.eq('main')].groupby('account'):
        orders=pd.read_parquet(CACHE/'ledgers'/f'{name}_orders.parquet')
        holds=pd.read_parquet(CACHE/'ledgers'/f'{name}_holdings.parquet')
        d=d.sort_values('date').set_index('date')
        cash=1.;maxerr=0.;units={}
        byorder={date:g for date,g in orders.groupby('date')}
        byhold={date:g for date,g in holds.groupby('date')}
        for date,r in d.iterrows():
            if date in byorder:
                for order in byorder[date].itertuples():
                    if order.side in ['BUY','SELL']:
                        sign=1 if order.side=='BUY' else -1
                        cash-=sign*order.value+order.fee
                        units[order.instrument]=units.get(order.instrument,0)+sign*order.units
                        check(abs(order.units*order.quote-order.value)<1e-10,'Units and actual fill')
                        check(order.actual_age==0 if sign==1 else order.actual_age>=10,'No premature sell')
            h=byhold.get(date,pd.DataFrame(columns=['instrument','units','mark']))
            saved=dict(zip(h.instrument,h.units))
            check(all(abs(saved.get(k,0)-v)<1e-10 for k,v in units.items()),'Holdings from actual fills')
            check(all(abs(units.get(k,0)-v)<1e-10 for k,v in saved.items()),'No fabricated holdings')
            nav=cash+float((h.units*h.mark).sum())
            maxerr=max(maxerr,abs(nav-r.nav),abs(cash-r.cash))
        check(maxerr<1e-9,'Cash and NAV independent ledger reconstruction')
        ledger_checks.append(dict(account=name,days=len(d),max_error=maxerr))
    pd.DataFrame(checks).to_csv(OUT/'model_replay.csv',index=False)
    pd.DataFrame(ledger_checks).to_csv(OUT/'ledger_reconstruction.csv',index=False)
    # A stopped account may report a partial total return but never a full-period CAGR.
    accounts=pd.read_csv(OUT/'accounts.csv')
    check(accounts.loc[~accounts.valuation_complete,'cagr'].isna().all(),'No comparison of incomplete CAGR')
    freeze()
    dump(MAN/'validation.json',dict(status='PASS',checks=count,frozen_input_hashes=len(frozen['files']),
        model_replays=len(checks),ledger_reconstructions=len(ledger_checks),original78_value_parity=11723400,
        original_E1_prediction_max_error=float(replay.max_prediction_error.max()),
        features_sha256=sha(CACHE/'h10_features.parquet'),predictions_sha256=sha(CACHE/'predictions.parquet'),
        limitations=['Historical-proxy','Flat suspension marks are labelled proxies','No certified total-return corporate-action ledger','No independent future validation']))
    print('PASS',count,'checks',len(checks),'models',len(ledger_checks),'ledgers',flush=True)


if __name__=='__main__':main()
