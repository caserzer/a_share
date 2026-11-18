"""Descriptive alignment of frozen E1 monthly decisions, REV events and timing ledgers."""
from pathlib import Path
import numpy as np
import pandas as pd
from common import EP, OUT, PRIVATE, sha, save_json
from backtest import Inputs
from suspension_sensitivity import marks
from portfolio import trade
from e1_mechanism import bootstrap
from e1_timing_mechanism_evaluate_v2 import ORIGINAL, DELAY, END, load_account
from e1_return_attribution import wealth_scale, log_link

ROOT = OUT/'diagnostics'
REV = ROOT/'e1_reversal_validation_20261117'
TIM = ROOT/'e1_timing_mechanism_20261117/evaluation_v2'
ATTR = ROOT/'e1_return_attribution_20261117'
STYLES = ROOT/'e1_excluded_styles_20261117'
DEST = ROOT/'e1_monthly_alignment_20261118'
NAMED = {'2022-05', '2024-01', '2024-02'}
INPUTS = set()

def read(path):
    INPUTS.add(path)
    return pd.read_parquet(path) if path.suffix == '.parquet' else pd.read_csv(path)

def save(frame, name):
    frame.to_csv(DEST/(name+'.csv'), index=False)

def require_close(actual, expected):
    np.testing.assert_allclose(actual, expected, atol=2e-10, rtol=1e-9, equal_nan=True)

def monthly_wealth():
    monthly = read(ATTR/'periods.csv').query("frequency == 'M'").rename(columns={'period':'month'})
    accounts = read(REV/'period_returns.csv').query("freq == 'M'").rename(columns={'period':'month'})
    monthly = monthly.merge(accounts[['month','O_return','REV_return']], validate='one_to_one')
    require_close(monthly.O_return, monthly.portfolio_return)
    scale = monthly.wealth_contribution.sum()/monthly.log_contribution.sum()
    monthly['O_minus_local_REV_yuan'] = scale*(np.log1p(monthly.O_return)-np.log1p(monthly.REV_return))
    monthly['local_REV_minus_index_yuan'] = scale*(np.log1p(monthly.REV_return)-np.log1p(monthly.benchmark_return))
    require_close(monthly.O_minus_local_REV_yuan+monthly.local_REV_minus_index_yuan,monthly.wealth_contribution)
    return monthly

def context(inp, signal, date):
    member,_,_,_,_,buy,sell,_ = inp.context(signal,date)
    return buy & member,sell

def events(inp, schedule, states):
    sleeves = read(PRIVATE/'e1_reversal_validation_20261117/sleeves.parquet')
    saved = read(REV/'events.csv').query("cost=='main' and horizon==10").set_index(['signal_date','strategy'])
    details, rows = [], []
    for ev in schedule.itertuples():
        date = ev.signal_date
        si = inp.days.get_loc(date)
        entry, exit_i = si+1, si+11
        entry_px, exit_px = inp.o[entry], inp.o[exit_i]
        metadata = states.loc[date].reindex(inp.symbols)
        ranks = metadata.score_residual.rank(pct=True).to_numpy()
        buy,_ = context(inp,si,entry)
        _,sell = context(inp,si,exit_i)
        row = dict(signal_date=date, exit_date=inp.days[exit_i], month=ev.month)
        legs = {}
        for policy in ['O','REV']:
            target = np.zeros(inp.n)
            basket = sleeves[(sleeves.signal_date==date)&(sleeves.strategy==policy)]
            target[inp.symbols.get_indexer(basket.instrument)] = basket.weight
            valid = np.isfinite(ranks)
            coverage = target[valid].sum()
            row[policy+'_rank_coverage'] = coverage
            row[policy+'_rank'] = np.nansum(ranks*target)/coverage if coverage else np.nan
            units,cash,info = trade(np.zeros(inp.n),1.,entry_px,np.r_[target,0.],buy,np.zeros(inp.n,bool),.001,.002)
            rec = saved.loc[(str(date.date()),policy)]
            net = rec.net_return
            row[policy+'_reason'] = rec.reason
            actual = units*np.nan_to_num(entry_px)
            stock = units*(np.nan_to_num(exit_px)-np.nan_to_num(entry_px))
            fee = actual*.001 + units*np.nan_to_num(exit_px)*.002
            if np.isfinite(net):
                assert np.all(np.isfinite(exit_px[units>0])) and np.all(sell[units>1e-12])
                require_close((stock-fee).sum(),net)
            legs[policy]=(target,actual,stock,fee,net)
        o,r = legs['O'],legs['REV']
        row['rank_gap_available'] = row['O_rank']-row['REV_rank']
        row['rank_gap_lower'] = row['O_rank']*row['O_rank_coverage']-row['REV_rank']*row['REV_rank_coverage']-(1-row['REV_rank_coverage'])
        row['rank_gap_upper'] = row['rank_gap_lower']+2-row['O_rank_coverage']-row['REV_rank_coverage']
        row['H10_net_gap']=o[-1]-r[-1]
        if np.isfinite(row['H10_net_gap']):
            ids=np.flatnonzero((o[0]+r[0])>0)
            ret=exit_px[ids]/entry_px[ids]-1
            target_effect=(o[0][ids]-r[0][ids])*ret
            gross=(o[2]-r[2])[ids]
            fees=(r[3]-o[3])[ids]
            for k,j in enumerate(ids):
                details.append(dict(month=ev.month,instrument=inp.symbols[j],state=metadata.state.iloc[j],O_target=o[0][j],REV_target=r[0][j],O_filled=o[1][j],REV_filled=r[1][j],stock_return=ret[k],target_effect=target_effect[k],execution_effect=gross[k]-target_effect[k],actual_gross=gross[k],fee_effect=fees[k],net_contribution=gross[k]+fees[k]))
            require_close((gross+fees).sum(),row['H10_net_gap'])
            diff=o[0][ids]-r[0][ids]
            active=np.abs(diff)
            if active.sum()>1e-10:
                center=np.average(ret,weights=active)
                row['differential_stock_return_sd']=np.sqrt(np.average((ret-center)**2,weights=active))
                row['O_overweight_basket_return']=np.average(ret,weights=np.maximum(diff,0))
                row['REV_overweight_basket_return']=np.average(ret,weights=np.maximum(-diff,0))
                require_close(target_effect.sum(),active.sum()/2*(row['O_overweight_basket_return']-row['REV_overweight_basket_return']))

        rows.append(row)
    return pd.DataFrame(rows),pd.DataFrame(details)

def calendar_segments(inp, schedule, monthly):
    # Split actual full-account log returns at the two pre-trade opens.
    levels={}
    for strategy in ['O','REV']:
        acc=read(STYLES/'accounts'/(strategy+'__main.csv')).set_index('date')
        orders=read(PRIVATE/'e1_excluded_styles_20261117/orders'/(strategy+'__main.parquet'))
        snapshots={date:g for date,g in orders.groupby('date')}
        units=np.zeros(inp.n)
        prev=1.
        for ev in schedule.itertuples():
            entry=ev.entry_date
            day=str(entry.date())
            group=snapshots[entry]
            start=float(acc.loc[day,'pretrade_nav'])
            units.fill(0)
            units[inp.symbols.get_indexer(group.instrument)]=group.units_after
            i=inp.days.get_loc(entry)
            cash=acc.loc[day,'nav']-units@np.nan_to_num(inp.c[i])
            m=monthly.loc[monthly.month.eq(ev.month)].iloc[0]
            end=float(acc.loc[m.end,'nav'])
            horizon=inp.days[i+10]
            mark=cash+units@np.nan_to_num(inp.o[i+10]) if horizon<=pd.Timestamp(m.end) else end
            if horizon<=pd.Timestamp(m.end):assert np.isfinite(inp.o[i+10,units>0]).all()
            assert cash>=-1e-10
            levels[(strategy,ev.month)]=np.log(np.array([start,mark,end])/np.array([prev,start,mark]))
            require_close(levels[(strategy,ev.month)].sum(),np.log1p(m[strategy+'_return']))
            prev=end
    out=[]
    for month in schedule.month:
        gap=levels['O',month]-levels['REV',month]
        out.append(dict(month=month,pre_entry_log_gap=gap[0],entry_to_H10_or_monthend_log_gap=gap[1],after_H10_log_gap=gap[2]))
    return pd.DataFrame(out)

def timing(inp,schedule,states):
    # Replay the frozen two-start/two-calendar bridge, exposing each stock's
    # early and late price P&L and the actual differential exposure before B trades.
    books={policy:load_account(root) for policy,root in [('A',ORIGINAL),('B',DELAY)]}
    maps={}
    for tag,(_,orders,_) in books.items():
        maps[tag]={}
        for date,g in orders.groupby('date'):
            v=np.zeros(inp.n+1)
            v[inp.symbols.get_indexer(g.instrument)]=g.target_weight
            maps[tag][date]=v
    ref=read(TIM/'path_segments_v2_months.csv').set_index('month')
    scale=wealth_scale(books['A'][0].nav.iloc[-1],books['B'][0].nav.iloc[-1])
    records=[]
    for ev in schedule.itertuples():
        start=inp.days.get_loc(ev.entry_date)
        boundary=next(d for d in maps['B'] if str(d.to_period('M'))==ev.month)
        mid=inp.days.get_loc(boundary)
        last=ref.loc[ev.month,'last_close']
        end=inp.days.get_loc(ref.loc[ev.month,'end'])
        endpx=inp.c[end] if last else inp.o[end]
        labels=states.loc[ev.signal_date].state.reindex(inp.symbols).fillna('UNKNOWN').to_numpy()
        for anchor,(account,_,holdings) in books.items():
            units=np.zeros(inp.n)
            prev=inp.days[start-1]
            g=holdings[holdings.date==prev]
            units[inp.symbols.get_indexer(g.instrument)]=g.synthetic_units
            cash=account.at[prev,'nav']*account.at[prev,'cash_weight'] if prev in account.index else 1.
            nav=cash+units@np.nan_to_num(inp.o[start])
            units/=nav
            cash/=nav
            legs={}
            for policy,trade_date in [('A',start),('B',mid)]:
                buy,sell=context(inp,trade_date-1,trade_date)
                updated,after,info=trade(units.copy(),cash,inp.o[trade_date],maps[policy][inp.days[trade_date]],buy,sell,.001,.002)
                early_units=updated if trade_date<mid else units
                px0,px1,px2=map(np.nan_to_num,(inp.o[start],inp.o[mid],endpx))
                early=np.r_[early_units*(px1-px0),-info['fees'] if trade_date<mid else 0.]
                midpoint=1+early.sum()
                late=np.r_[updated*(px2-px1),-info['fees'] if trade_date==mid else 0.]/midpoint
                require_close((1+early.sum())*(1+late.sum()),ref.loc[ev.month,anchor+policy])
                legs[policy]=(early,late,early_units)
            delta=legs['A'][2]-legs['B'][2]
            for k,segment in enumerate(['early','late']):
                a,b=legs['A'][k],legs['B'][k]
                amount=(a-b)*log_link(np.array([a.sum()]),np.array([b.sum()]))[0]*scale/2
                for j in np.flatnonzero(amount):
                    fee=j==inp.n
                    action='fee' if fee else 'post_delay' if k else 'new_or_added' if delta[j]>0 else 'sold_or_reduced'
                    records.append(dict(month=ev.month,delay_execution=boundary,anchor=anchor,segment=segment,instrument='__FEES__' if fee else inp.symbols[j],state='__FEES__' if fee else labels[j],action=action,yuan=amount[j]))
    detail=pd.DataFrame(records)
    for (month,seg),g in detail.groupby(['month','segment']):
        for fee,field in [(True,'fee'),(False,'stock')]:
            require_close(g.loc[g.action.eq('fee')==fee,'yuan'].sum(),ref.at[month,seg+'_'+field]*scale)
    return detail

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    inp=Inputs()
    marks(inp,0.)
    sched=read(TIM/'schedule.csv')
    for c in ['signal_date','entry_date']:sched[c]=pd.to_datetime(sched[c])
    states=read(PRIVATE/'e1_timing_mechanism_20261117/states.parquet').set_index(['signal_date','instrument'])
    monthly=monthly_wealth()
    event,stock=events(inp,sched,states)
    ic=read(TIM/'residual_correlations.csv').query("state=='ALL' and outcome=='immediate'")[['signal_date','n_stocks','conditional_rank_ic']]
    ic.signal_date=pd.to_datetime(ic.signal_date)
    support=read(REV/'selection_checks.csv')
    support.signal_date=pd.to_datetime(support.signal_date)
    decision=sched.merge(event,on=['signal_date','month']).merge(ic,on='signal_date').merge(support,on='signal_date')
    pair=read(REV/'event_pairs.csv').query('horizon==10')
    require_close(decision.sort_values('signal_date').H10_net_gap,pair.sort_values('signal_date').difference)
    master=monthly.merge(decision,on='month',how='left',validate='one_to_one').merge(calendar_segments(inp,sched,monthly),on='month',how='left')
    timed=timing(inp,sched,states)
    ref=read(TIM/'path_segments_v2_months.csv')
    master=master.merge(ref[['month','timing_wealth','inherited_wealth','total_wealth']],how='left',on='month')
    actions=timed.pivot_table(index='month',columns='action',values='yuan',aggfunc='sum',fill_value=0).reindex(sched.month,fill_value=0)
    b_dates=load_account(DELAY)[1].date.drop_duplicates().sort_values()
    master['actual_delayed_open']=master.month.map(dict(zip(b_dates.dt.to_period('M').astype(str),b_dates)))
    master=master.merge(actions.add_suffix('_timing_yuan'),on='month',how='left')
    assert len(master)==51 and len(decision)==50 and master.H10_net_gap.count()==45
    require_close(actions.sum(axis=1),ref.timing_wealth)
    save(master,'monthly');save(stock,'H10_stock');save(stock[stock.month.isin(NAMED)],'named_H10_stock')
    save(stock.groupby(['month','state'],dropna=False,as_index=False).sum(numeric_only=True)[['month','state','actual_gross','fee_effect','net_contribution']],'H10_states')
    save(timed,'timing_stock');save(timed[timed.month.isin(NAMED)],'named_timing_stock')
    save(timed.groupby(['month','segment','state','action'],as_index=False).yuan.sum(),'timing_state_action')
    rows=[]
    groups={'all':master,'named':master[master.month.isin(NAMED)],'rest':master[~master.month.isin(NAMED)]}
    for m in master.month:groups['omit_'+m]=master[master.month!=m]
    for label,g in groups.items():
        paired=g.dropna(subset=['H10_net_gap'])
        rows.append(dict(group=label,calendar_n=len(g),decisions=g.signal_date.count(),pairs=len(paired),ic=g.conditional_rank_ic.mean(),ic_paired=paired.conditional_rank_ic.mean(),ic_missing_exit=g.loc[g.signal_date.notna()&g.H10_net_gap.isna(),'conditional_rank_ic'].mean(),net_H10_pp=100*paired.H10_net_gap.mean(),rank_gap=paired.rank_gap_available.mean(),ic_vs_gap_spearman=paired.conditional_rank_ic.corr(paired.H10_net_gap,method='spearman'),wealth=g.wealth_contribution.sum(),local_increment=g.O_minus_local_REV_yuan.sum(),retained=g.local_REV_minus_index_yuan.sum()))
    save(pd.DataFrame(rows),'groups_and_leave_one_out')
    uncertainty=[]
    calendar=decision.set_index('signal_date')
    for label in ['all','rest']:
        mask=~calendar.month.isin(NAMED) if label=='rest' else calendar.month.notna()
        for field in ['H10_net_gap','conditional_rank_ic']:
            series=calendar[field].where(mask & calendar.H10_net_gap.notna())
            uncertainty.append(dict(sample=label,field=field,**bootstrap(series,'M',3)))
    save(pd.DataFrame(uncertainty),'paired_intervals')
    for root in [ORIGINAL,DELAY]:
        import json
        receipt=root.with_suffix('.json')
        info=json.loads(receipt.read_text())
        INPUTS.update([receipt,root.with_suffix('.csv'),Path(info['orders_path']),Path(info['holdings_path'])])
    INPUTS.update([PRIVATE/(name+'.parquet') for name in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry','limits/daily','suspensions/daily','weights/snapshots']])

    save_json(DEST/'audit.json',dict(source=sha(__file__),input_sha256={str(p.relative_to(EP)):sha(p) for p in sorted(INPUTS)},calendar_months=51,decisions=50,valid_H10=45,stock_reconciliation='per leg and executable pair',timing_reconciliation='four published path NAVs per month and both segment fee/stock components',status='PASS'))
if __name__=='__main__':main()
