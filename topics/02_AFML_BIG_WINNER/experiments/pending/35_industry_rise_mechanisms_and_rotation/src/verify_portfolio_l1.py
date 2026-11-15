import pandas as pd
from common import *
from evaluate_r01 import scores

def run():
    out=ROOT/'outputs/r17';h=pd.read_parquet(out/'holdings.parquet');intervals=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit'])
    daily=pd.read_parquet(out/'daily_returns.parquet');summary=pd.read_csv(out/'summary.csv')
    panel=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet');p=pd.read_parquet(ROOT/'data/l1_daily.parquet').pivot(index='date',columns='industry_code',values='nav')
    checked=0;maxerror=0.
    for method,g in intervals.groupby('method'):
        valid=g[g.status=='valid'].sort_values('origin');assert len(valid)==52
        assert valid.entry.iloc[1:].reset_index(drop=True).equals(valid.exit.iloc[:-1].reset_index(drop=True))
        terminal={'gross':1.,'net20':1.,'net50':1.};drift={}
        for row in valid.itertuples():
            selected=h[(h.method==method)&(h.origin==row.origin)];assert np.isclose(selected.weight.sum(),1)
            universe=panel[(panel.date==row.origin)&panel.price_ready].dropna(subset=['breadth21','breadth63'])
            expected=universe if method=='equal' else universe.assign(score=scores(universe)[method]).sort_values(['score','industry_code'],ascending=[False,True]).head(6)
            assert set(selected.industry_code)==set(expected.industry_code)
            assert len(selected)==(len(universe) if method=='equal' else 6)
            target=selected.set_index('industry_code').weight
            a=p.loc[row.entry:row.exit,target.index];relative=a/a.iloc[0];wealth=relative.mul(target,axis=1).sum(axis=1)
            assert a.notna().all().all()
            trade=sum(abs(target.get(code,0)-drift.get(code,0)) for code in set(target.index)|set(drift))
            assert np.isclose(trade,row.turnover)
            assert np.isclose(wealth.iloc[-1]-1,row.gross_return)
            for label,cost in [('gross',0),('net20',.002),('net50',.005)]:terminal[label]*=(1-cost*trade)*wealth.iloc[-1]
            drift=(relative.iloc[-1]*target/wealth.iloc[-1]).to_dict();checked+=1
        for label,cost in [('gross',0),('net20',.002),('net50',.005)]:
            terminal[label]*=1-cost
            observed=(1+daily.loc[daily.method==method,label]).prod();maxerror=max(maxerror,abs(observed-terminal[label]))
            reported=summary[(summary.method==method)&(summary.cost==label)].iloc[0]
            assert np.isclose(reported.total_return,terminal[label]-1)
            assert np.isclose(reported.total_turnover_with_final_exit,valid.turnover.sum()+1)
    assert maxerror<1e-10
    membership=pd.read_csv(out/'membership_concentration.csv');assert np.allclose(membership.known_nominal_weight+membership.unresolved_nominal_weight,1)
    assert membership.duplicate_member_entries.eq(0).all()
    risk=pd.read_csv(out/'risk_by_origin.csv');assert np.allclose(risk.loc[risk.method!='equal','target_hhi'],1/6)
    assert risk.loc[risk.prior_observations<42,'prior_vol'].isna().all()
    js(out/'verification.json',dict(status='PASS',intervals_replayed=checked,terminal_wealth_error=maxerror,
        checks=['fixed top6/equal selection','continuous monthly schedule','drift turnover not target-to-target turnover','initial buy and final liquidation fees','independent compounded terminal wealth','nominal membership plus unresolved weight equals1','no duplicate L1 memberships'],
        limitation='synthetic basket accounting only; no stock-level fill or internal turnover validation'))
    print('R17 VERIFIED',checked,'intervals; terminal wealth error',maxerror)
if __name__=='__main__':run()
