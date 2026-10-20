"""Fixed 5% holdings diagnostics; execution branch fails closed on settlement gaps."""
from core import *
from run import freeze


def selections(frame):
    f=frame[frame.log_money21>=np.log1p(C['portfolio']['minimum_past21_money_cny'])].copy().reset_index(drop=True)
    f=risk_cells(f);mr=warning(f.M_R,f.instrument,.05);l4=warning(f.L4,f.instrument,.05)
    matched=np.zeros(len(f),bool)
    for _,g in f.groupby('risk_cell'):
        count=int(mr[g.index].sum())
        if count:
            order=np.lexsort((tie(g.instrument),-g.L4.to_numpy()))
            matched[g.index[order[:count]]]=True
    assert matched.sum()==mr.sum()
    return f,{'S0':np.ones(len(f),bool),'S1':~mr,'S2':~l4,'S2_matched':~matched}


def main():
    freeze();gate=json.loads((EP/'outputs/audits/data_gate.json').read_text())
    full=pd.read_parquet(CACHE/'all_predictions.parquet');base=full[full.model.eq('M_R')].rename(columns={'probability':'M_R'})
    l4=full[full.model.eq('L4')][['date','instrument','probability']].rename(columns={'probability':'L4'})
    joint=base.merge(l4,on=['date','instrument'],validate='one_to_one');rows=[];exposures=[];holdings=[]
    for date,raw in joint.groupby('date'):
        f,sel=selections(raw)
        for name,mask in sel.items():
            g=f[mask];known=g.actual.notna();events=labels(g.actual)
            rows.append(dict(date=date,strategy=name,eligible=len(f),held=len(g),excluded=len(f)-len(g),
                target_equity=1.,known=int(known.sum()),missing=int((g.label_end.notna()&~known).sum()),
                event_fraction=float(np.nanmean(events)) if known.any() else np.nan,
                log_cap=float(g.log_cap.mean()),vol63=float(g.vol63.mean()),
                mean_past21_money=float(np.expm1(g.log_money21).mean()),execution_certified=False))
            for sector,z in g.groupby('industry_id'):exposures.append(dict(date=date,strategy=name,industry_id=sector,weight=len(z)/len(g)))
            holdings.extend(dict(date=date,strategy=name,instrument=s,weight=1/len(g)) for s in g.instrument)
    m=pd.DataFrame(rows);m.to_csv(OUT/'filter_holdings_monthly.csv',index=False);pd.DataFrame(exposures).to_csv(OUT/'filter_industry_exposure.csv',index=False)
    pd.DataFrame(holdings).to_parquet(CACHE/'filter_target_holdings.parquet',index=False)
    intervals=[]
    evaldates=set(m[m.event_fraction.notna()].date)
    for a,b in [('S1','S0'),('S2','S1'),('S2_matched','S1')]:
        aa=m[(m.strategy==a)&m.date.isin(evaldates)];bb=m[(m.strategy==b)&m.date.isin(evaldates)]
        for metric in ['event_fraction','log_cap','vol63']:
            for block in C['bootstrap']['blocks']:intervals.append(dict(candidate=a,baseline=b,metric=metric,**ci(paired(aa,bb,metric),block)))
    pd.DataFrame(intervals).to_csv(OUT/'filter_intervals.csv',index=False)
    assert not gate['settlement_repaired']
    write_json(EP/'outputs/audits/portfolio_gate.json',dict(status='executable_economic_branch_stopped',
        selected_model='L4',selection_before_scoring=True,fixed_filter=.05,diagnostic='equal-weight target holdings only; not actual holdings',
        unavailable=['actual held loss-event share','daily/monthly portfolio Expected Shortfall','maximum drawdown','net cumulative/annualized return','cost and participation-cap execution','realized exposure drift','opportunity cost'],
        reason='delisting settlement, suspension/resumption tradeability and special corporate-action total-return closure are not certified',
        planned_cost_bps=C['portfolio']['cost_bps'],cost_runs_not_executed=True,static_event_and_exposure_diagnostics_complete=True))
    print('Fixed holdings diagnostic complete; executable portfolio branch stopped by data gate.',flush=True)


if __name__=='__main__':main()
