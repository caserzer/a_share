"""R09: independently reconstruct pre-tax cash/split reinvestment labels.

Cash dividends reinvest at ex-date close; rights and unpriceable action dates
remain explicitly unavailable. This does not manufacture a complete TR database.
"""
import json
import numpy as np
import pandas as pd
from run_price_pilot import OUT
from run_holdout import distribution_stats


def reinvested_index(close, cash, shares):
    prior=close.ffill().shift(1)
    gross=(close*(1+shares)+cash)/prior
    gross.iloc[0]=1.
    return gross.fillna(1.).cumprod()


def run():
    dest=OUT/'r09_total_return_sensitivity'
    dest.mkdir(exist_ok=True)
    data=OUT.parents[3]/'data'
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(data/'qlib/cn_data_pit_largecap/calendars/day.txt',header=None)[0]))
    panel=pd.read_parquet(OUT/'local_cache/monthly_panel.parquet')
    folder=OUT/'local_cache/corporate_actions'
    actions=pd.read_parquet(folder/'RPT_SHAREBONUS_DET_all.parquet')
    rights=pd.read_parquet(folder/'RPT_IPO_ALLOTMENT_all.parquet')
    actions['date']=pd.to_datetime(actions.EX_DIVIDEND_DATE)
    actions['NOTICE_DATE']=pd.to_datetime(actions.NOTICE_DATE)
    actions=actions.sort_values('NOTICE_DATE').drop_duplicates(['SECURITY_CODE','date','REPORT_DATE'],keep='last')
    rights['begin']=pd.to_datetime(rights.EQUITY_RECORD_DATE).fillna(pd.to_datetime(rights.EX_DIVIDEND_DATE))
    rights['finish']=pd.to_datetime(rights.LISTING_DATE).fillna(pd.to_datetime(rights.EX_DIVIDEND_DATE))
    pieces=[]
    factor_audit=[]
    for instrument,g in panel.groupby('instrument'):
        raw=pd.read_csv(data/f'raw/akshare/day/raw/{instrument}.csv',parse_dates=['date']).set_index('date').reindex(calendar)
        qfq=pd.read_csv(data/f'raw/akshare/day/qfq/{instrument}.csv',parse_dates=['date']).set_index('date').reindex(calendar)
        close=raw.close.where(raw.close>0)
        a=actions[actions.SECURITY_CODE==instrument[2:]].copy()
        a['cash']=pd.to_numeric(a.PRETAX_BONUS_RMB,errors='coerce')/10
        a['shares']=pd.to_numeric(a.BONUS_IT_RATIO,errors='coerce')/10
        unknown=a.loc[a.cash.isna() & a.shares.isna(),'date'].tolist()
        cash=a.groupby('date').cash.sum(min_count=1).reindex(calendar).fillna(0)
        shares=a.groupby('date').shares.sum(min_count=1).reindex(calendar).fillna(0)
        unavailable=[d for d in a.date if d not in calendar or pd.isna(close.get(d))]
        # Negative actions are not conventional dividend/split events.
        unavailable.extend(a.loc[(a.cash<0)|(a.shares<0),'date'].tolist())
        # An independent corporate-action table can omit special transfers/reorganizations.
        # Detect unaccounted adjustment jumps; do not call the reconstruction valid there.
        factor=(qfq.close/close).ffill()
        observed=factor/factor.shift(1)
        prior=close.ffill().shift(1)
        expected=(1+shares)/(1-cash/prior)
        discrepancy=np.log(observed/expected).abs()
        rounding_allowance=.02+.005/qfq.close+.005/qfq.close.ffill().shift(1)
        unexplained=calendar[(discrepancy>rounding_allowance).fillna(False)].tolist()
        factor_audit.extend({'instrument':instrument,'date':str(d.date()),'observed_factor_change':observed.loc[d],
                             'expected_factor_change':expected.loc[d],'absolute_log_difference':discrepancy.loc[d]} for d in unexplained)
        tr=reinvested_index(close,cash,shares)
        r=rights[rights.SECURITY_CODE==instrument[2:]]
        for row in g.itertuples():
            for h in [126,252]:
                entry=row.entry_date
                end=getattr(row,f'label_end{h}')
                reason='ok'
                total=np.nan
                if pd.isna(end):
                    reason='immature'
                elif pd.isna(raw.open.get(entry)) or pd.isna(close.get(end)) or pd.isna(close.get(entry)):
                    reason='missing_entry_exit'
                elif ((r.begin<=end) & (r.finish>=entry)).any():
                    reason='rights_interval'
                elif any(entry<d<=end for d in unknown):
                    reason='unknown_action_amount'
                elif any(entry<d<=end for d in unavailable):
                    reason='action_on_unpriceable_date'
                elif any(entry<d<=end for d in unexplained):
                    reason='unexplained_adjustment_event'
                else:
                    total=tr.loc[end]/tr.loc[entry]*close.loc[entry]/raw.open.loc[entry]-1
                pieces.append({'date':row.date,'instrument':instrument,'horizon':h,'entry_date':entry,
                    'label_end':end,'qfq_return':getattr(row,f'return{h}'),'reinvested_return':total,'status':reason})
    labels=pd.DataFrame(pieces)
    pd.DataFrame(factor_audit).to_csv(dest/'unexplained_factor_events.csv',index=False)
    labels['difference']=labels.reinvested_return-labels.qfq_return
    labels.to_parquet(OUT/'local_cache/reinvested_labels.parquet',index=False)
    labels.groupby(['horizon','status']).size().rename('rows').to_csv(dest/'label_coverage.csv')
    valid=labels.dropna(subset=['difference'])
    summaries=[]
    for h,g in valid.groupby('horizon'):
        summaries.append({'horizon':h,'rows':len(g),'median_abs_difference':g.difference.abs().median(),
            'p95_abs_difference':g.difference.abs().quantile(.95),'p99_abs_difference':g.difference.abs().quantile(.99),
            'max_abs_difference':g.difference.abs().max(),
            'up_direction_disagreement':((g.qfq_return>0)!=(g.reinvested_return>0)).mean()})
    pd.DataFrame(summaries).to_csv(dest/'return_definition_difference.csv',index=False)
    valid.reindex(valid.difference.abs().sort_values(ascending=False).index).head(50).to_csv(dest/'largest_discrepancies.csv',index=False)
    original=pd.read_parquet(OUT/'r05_holdout/predictions.parquet')
    merged=original.merge(labels[['date','instrument','horizon','reinvested_return','status']],on=['date','instrument','horizon'],validate='many_to_one')
    results=[]
    for (h,model,quarter),g in merged.groupby(['horizon','model',merged.date.dt.to_period('Q')]):
        keys=pd.read_parquet(OUT/f'local_cache/r05_distributions/{h}_{quarter}_keys.parquet')
        atoms=np.load(OUT/f'local_cache/r05_distributions/{h}_{quarter}_{model}.npz')['atoms']
        idx={(r.date,r.instrument):i for i,r in enumerate(keys.itertuples())}
        keep=g[(g.status=='ok') & g.reinvested_return.notna() & g.actual.notna()].copy()
        if keep.empty:
            continue
        selected=[idx[(r.date,r.instrument)] for r in keep.itertuples()]
        for definition,y in [('qfq_same_sample',keep.actual),('cash_split_reinvested',keep.reinvested_return)]:
            stats=distribution_stats(atoms[selected],y)
            stats['date']=keep.date.to_numpy()
            stats['horizon'],stats['model'],stats['definition']=h,model,definition
            results.append(stats)
    scores=pd.concat(results,ignore_index=True).groupby(['horizon','model','definition','date'])[['crps','brier','below_q05','coverage90']].mean()
    scores.to_csv(dest/'monthly_scores.csv')
    score_summary=scores.groupby(['horizon','model','definition']).mean()
    score_summary.to_csv(dest/'summary.csv')
    (dest/'semantics.json').write_text(json.dumps({
        'cash':'PRETAX_BONUS_RMB per 10 shares / 10, reinvest ex-date close without tax or financing charge',
        'shares':'BONUS_IT_RATIO per 10 shares / 10',
        'entry':'next open; no dividend entitlement for purchase on ex-date itself',
        'unsupported':'rights intervals, action dates without price, unknown action amounts and unexplained adjustment jumps excluded explicitly',
        'factor_check':'abs(log(observed / expected factor change)) > 0.02 plus qfq rounding allowance flags unaccounted events; not an outcome-performance filter',
        'comparison':'fixed R05 forecasts rescored on same available targets, not retraining or new independent validation',
        'scope':'quantifies proxy sensitivity; not a claim of complete all-corporate-action total-return coverage',
    },indent=2)+'\n')
    print(pd.DataFrame(summaries).to_string(index=False))
    print(labels.groupby(['horizon','status']).size().to_string())
    print(score_summary.to_string())


if __name__=='__main__':
    run()
