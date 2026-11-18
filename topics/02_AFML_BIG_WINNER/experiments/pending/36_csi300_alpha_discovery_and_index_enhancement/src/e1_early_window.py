"""Same starting inventory and budget, three policies over the actual early window."""
import json
import numpy as np
import pandas as pd
from common import EP, PRIVATE, sha, save_json
from e1_monthly_alignment import ROOT, REV, NAMED, ORIGINAL, DELAY, load_account, context, require_close
from e1_mechanism import bootstrap
from e1_return_attribution import log_link
from backtest import Inputs
from portfolio import trade
from suspension_sensitivity import marks

RUN = 'e1_early_window_20261118'
OUT = ROOT/RUN
DOC = EP/'reports'/RUN
SLEEVES = PRIVATE/'e1_reversal_validation_20261117/sleeves.parquet'
TARGETS = PRIVATE/'e1_excluded_styles_20261117/targets.parquet'
MONTHS = ROOT/'e1_monthly_alignment_20261118/monthly.csv'
REFERENCE = ROOT/'e1_timing_mechanism_20261117/evaluation_v2/path_segments_v2_months.csv'
METRICS = ['E1_minus_old','REV_minus_old','E1_minus_REV']

def weights(frame, index):
    values = np.zeros(len(index)+1)
    loc = index.get_indexer(frame.instrument)
    assert (loc>=0).all() and frame.instrument.is_unique
    values[loc]=frame.weight
    require_close(values.sum(),1.)
    return values

def initial(book, inp, start):
    acc,_,holdings=book
    day=inp.days[start-1]
    g=holdings[holdings.date.eq(day)]
    units=np.zeros(inp.n)
    units[inp.symbols.get_indexer(g.instrument)]=g.synthetic_units
    cash=acc.at[day,'nav']*acc.at[day,'cash_weight'] if day in acc.index else 1.
    prices=inp.o[start]
    assert np.isfinite(prices[units>0]).all()
    nav=units@np.nan_to_num(prices)+cash
    return units/nav,cash/nav

def replay(inp, ev, book, baskets, anchor, scope, stock_rows):
    start=inp.days.get_loc(ev.entry_date)
    end=inp.days.get_loc(ev.actual_delayed_open)
    old,cash=initial(book,inp,start)
    px=inp.o[start]; final=inp.o[end]
    buy,sell=context(inp,start-1,start)
    row=dict(month=ev.month,signal_date=ev.signal_date,entry_date=ev.entry_date,delayed_open=ev.actual_delayed_open,sessions=end-start,anchor=anchor,scope=scope,budget=ev.budget)
    if end==start:
        row['status']='NO_DELAY_WINDOW'
        return row
    row['status']='OK'
    def mark(units):
        held=units>0
        if not np.isfinite(final[held]).all() or not np.isfinite(inp.c[start:end,held]).all():
            return np.nan
        return units@np.nan_to_num(final)
    row['old_return']=mark(old)+cash-1
    move=np.nan_to_num(final)-np.nan_to_num(px)
    for name,target in baskets.items():
        updated,cash_after,info=trade(old.copy(),cash,px,target,buy,sell,.001,.002)
        result=mark(updated)+cash_after-1
        if not np.isfinite([result,row['old_return']]).all():
            row['status']='UNKNOWN_MARK'
            continue
        delta=updated-old
        contrib=delta*move
        additions=np.maximum(delta,0)@move
        disposals=np.minimum(delta,0)@move
        fee=info['fees']
        row.update({name+'_return':result,name+'_minus_old':result-row['old_return'],name+'_buy_pnl':additions,name+'_sell_pnl':disposals,name+'_fee':fee,name+'_unfilled_buy':info['unfilled_buy'],name+'_unfilled_sell':info['unfilled_sell']})
        require_close(additions+disposals-fee,row[name+'_minus_old'])
        for j in np.flatnonzero((old>0)|(updated>0)|(target[:-1]>0)):
            stock_rows.append(dict(month=ev.month,anchor=anchor,scope=scope,policy=name,instrument=inp.symbols[j],old_units=old[j],target=target[j],final_units=updated[j],buy_allowed=buy[j],sell_allowed=sell[j],open_price=px[j],end_open=final[j],gross_difference=contrib[j],fee=abs(delta[j])*np.nan_to_num(px[j])*(.001 if delta[j]>0 else .002)))
    if row['status']=='OK':
        row['E1_minus_REV']=row['E1_return']-row['REV_return']
        for col in METRICS:
            row[col+'_account_budget']=row[col]*(ev.budget if scope=='sleeve' else 1.)
    return row

def summarize(result):
    records=[]
    for (anchor,scope),panel in result.groupby(['anchor','scope']):
        panel=panel.set_index('signal_date').sort_index()
        groups={'all':panel.sessions.gt(0),'named':panel.month.isin(NAMED),'rest':~panel.month.isin(NAMED)}
        groups.update({str(y):panel.index.year==y for y in panel.index.year.unique()})
        groups.update({'omit_'+m:panel.month.ne(m) for m in panel.month})
        for group,mask in groups.items():
            mask=mask & panel.status.eq('OK')
            for metric in METRICS:
                series=panel[metric].where(mask)
                known=series.dropna()
                row=dict(anchor=anchor,scope=scope,group=group,metric=metric,n=len(known),mean=known.mean(),median=known.median(),wins=(known>1e-12).sum(),losses=(known< -1e-12).sum(),flat=(abs(known)<=1e-12).sum(),account_budget_mean=panel.loc[mask,metric+'_account_budget'].mean())
                if group in ['all','rest']:
                    stats=bootstrap(series,'M',3)
                    row.update(ci_low=stats['ci_low'],ci_high=stats['ci_high'])
                records.append(row)
    return pd.DataFrame(records)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=[MONTHS,SLEEVES,TARGETS,REFERENCE,REV/'selection_checks.csv',DOC/'PROTOCOL.md',EP/'src/e1_early_window.py',EP/'src/portfolio.py',EP/'src/backtest.py',EP/'src/suspension_sensitivity.py',EP/'src/e1_monthly_alignment.py']
    for root in [ORIGINAL,DELAY]:
        receipt=root.with_suffix('.json')
        info=json.loads(receipt.read_text())
        inputs.extend([root.with_suffix('.csv'),receipt,info['orders_path'],info['holdings_path']])
    inputs.extend(PRIVATE/(s+'.parquet') for s in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','limits/daily','suspensions/daily','weights/snapshots'])
    save_json(OUT/'inputs.json',{'sha256':{str(p):sha(p) for p in inputs}})
    inp=Inputs()
    marks(inp,0.)
    months=pd.read_csv(MONTHS,parse_dates=['signal_date','entry_date','actual_delayed_open']).dropna(subset=['signal_date'])
    sleeves=pd.read_parquet(SLEEVES).groupby(['signal_date','strategy'])
    full=pd.read_parquet(TARGETS).groupby(['signal_date','strategy'])
    books={'immediate':load_account(ORIGINAL),'delayed':load_account(DELAY)}
    rows=[]; stocks=[]
    for ev in months.itertuples():
        baskets={scope:{name:weights(source.get_group((ev.signal_date,label)),inp.symbols) for name,label in [('E1','O'),('REV','REV')]} for scope,source in [('sleeve',sleeves),('full',full)]}
        require_close(baskets['full']['E1']-baskets['full']['REV'],ev.budget*(baskets['sleeve']['E1']-baskets['sleeve']['REV']))
        for anchor,book in books.items():
            for scope,targets in baskets.items():
                rows.append(replay(inp,ev,book,targets,anchor,scope,stocks))
    result=pd.DataFrame(rows)
    assert len(result)==200
    full_rows=result[result.scope.eq('full') & result.status.eq('OK')].copy()
    full_rows['log_gap']=np.log1p(full_rows.E1_return)-np.log1p(full_rows.old_return)
    ref=pd.read_csv(REFERENCE).set_index('month')
    gap=full_rows.groupby('month').log_gap.mean()
    require_close(gap,ref.loc[gap.index,'early_timing'])
    for part,col in [('stock','early_stock'),('fee','early_fee')]:
        raw=(full_rows.E1_buy_pnl+full_rows.E1_sell_pnl) if part=='stock' else -full_rows.E1_fee
        link=raw*log_link(full_rows.E1_return.to_numpy(),full_rows.old_return.to_numpy())
        sums=link.groupby(full_rows.month).mean()
        require_close(sums,ref.loc[sums.index,col])
    stock=pd.DataFrame(stocks)
    summed=stock.groupby(['month','anchor','scope','policy'])[['gross_difference','fee']].sum()
    for name in ['E1','REV']:
        reference=result.query("status=='OK'").set_index(['month','anchor','scope'])
        ledger=summed.xs(name,level='policy').reindex(reference.index)
        require_close(ledger.gross_difference-ledger.fee,reference[name+'_minus_old'])
    result.to_csv(OUT/'monthly.csv',index=False)
    stock.to_csv(OUT/'stock_ledger.csv.gz',index=False)
    summarize(result).to_csv(OUT/'comparisons.csv',index=False)
    save_json(OUT/'audit.json',dict(status=result.status.value_counts().to_dict(),primary_decisions=len(months),tests=['common target budget per month','fill, fee and stock ledger closure','frozen full E1 early log gap and price/fee decomposition for both anchors averaged'],outputs={p.name:sha(p) for p in [OUT/'monthly.csv',OUT/'stock_ledger.csv.gz',OUT/'comparisons.csv']}))
if __name__=='__main__':main()
