"""Recheck dated score windows, entire account algebra, funded cash-flow totals and G3 flags."""
from scale_common import *
import json
def main():
    st=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    frame=data(['mom5','mom20','money_rel20']);frame['Z1']=frame.signal_date.map(st)
    frame['unknown_state']=frame.Z1.isna()
    for col in ['mom5','mom20','money_rel20']:frame['unknown_'+col]=frame[col].isna()
    flags=[c for c in frame if c.startswith('unknown')]
    atomic_parquet(frame[KEY+['outer','weekly','Z1']+flags],RES/'G3_input_flags.parquet')
    daily=pd.read_parquet(RES/'daily.parquet')
    alg=np.abs(daily.nav-daily.prev-daily.gross_pnl+daily.fee).max()
    assert alg<1e-10
    pred=pd.read_parquet(RES/'scale_scores.parquet',columns=KEY+['vol_live'])
    original=pd.read_parquet(SCORES,columns=KEY+['R','T'])
    merged=pred.merge(original,on=KEY,validate='1:1')
    np.testing.assert_allclose(merged.vol_live,merged['T'],atol=1e-10,rtol=0)
    assert len(merged)==len(original)==407372
    cmpd=pd.read_csv(RES/'comparisons.csv')
    for _,g in cmpd.groupby(['arm','base','fee_multiple','id']):
        assert dict(zip(g.segment,g.months))=={'all':67,'primary':49,'later':18}
    totals=daily[daily.fee_multiple.eq(1)].groupby(['arm','segment'])[['fee','gross_pnl']].sum()
    co=pd.read_parquet(RES/'cohort_pnl.parquet')
    co.segment=co.segment.map({1:'primary',2:'later'})
    c=co.groupby(['arm','segment'])[['fee','overnight','intraday']].sum()
    ts=totals.reindex(c.index)
    e1=np.max(np.abs(ts.fee-c.fee));e2=np.max(np.abs(ts.gross_pnl-c.overnight-c.intraday))
    assert max(e1,e2)<1e-10
    early=pd.read_csv(RES/'shallow_early_folds.csv')
    assert (early.max_inner_maturity<early.first_valid_signal).all()
    z=pd.read_parquet(RES/'S4_placebo_dates.parquet')
    assert (z.source_date<pd.PeriodIndex(z.quarter,freq='Q').to_timestamp()).all()
    assert len(z)==1389*20
    left=pd.read_parquet(RES/'S1_features.parquet').groupby(['quarter','cohort','path','signal_date'])[['deviation','observable_weight']].sum()
    right=pd.read_parquet(RES/'S1_daily.parquet').set_index(['fold','cohort','path','signal_date']).sort_index()
    err=np.max(abs((left.deviation/left.observable_weight).to_numpy()-right.structure.to_numpy()))
    assert err<1e-10
    proof={'score_rows':len(merged),'outer_scoring_dates':merged.signal_date.nunique(),'account_rows':len(daily),'account_pnl_error':alg,'cohort_fee_error':e1,'cohort_gross_error':e2,'S1_feature_decomposition_error':err,'registered_month_counts':[49,18],'all_23_quarters_early_train_mature_before_validation':True,'all_placebo_dates_precede_quarter':True,'placebo_dates':len(z)}
    (RES/'account_audit.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
