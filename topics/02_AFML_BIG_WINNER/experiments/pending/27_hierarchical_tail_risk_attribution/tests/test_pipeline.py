import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from core import labels,loo_median,rebuild_industry,metrics,ci,split,risk_cells,warning
from conditional import conditional_auc,make_pairs,error_decomposition
from controls import permute_conditionally
from calibrate import fit_offset,apply_offset,mature_calibration_rows
from portfolio import select,trade,simulate,drawdown_duration


def test_strict_threshold_and_missing():
    y=labels([-.200001,-.2,-.199999,np.nan]);np.testing.assert_array_equal(y[:3],[1,0,0]);assert np.isnan(y[3])


def test_leave_one_out_median_matches_direct_exclusion_with_ties_and_nan():
    v=np.array([1,1,2,3,4,5,np.nan,6.]);actual=loo_median(v)
    expected=[]
    for i in range(len(v)):
        peer=np.delete(v,i);peer=peer[np.isfinite(peer)];expected.append(np.median(peer) if len(peer)>=5 else np.nan)
    np.testing.assert_allclose(actual,expected,equal_nan=True)


def test_industry_publication_prefix_and_peer_future_independence(tmp_path):
    path=tmp_path/'old.parquet';pd.DataFrame(dict(code=[f'{i:06d}' for i in range(8)],major=['C26']*8,sector=['C']*8)).to_parquet(path,index=False)
    releases=[dict(published='2019-01-01',table_path=str(path))]
    frame=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31']*8),instrument=[f'SZ{i:06d}' for i in range(8)],mom63=np.arange(8.),mom126=np.arange(8.)*2,actual=np.arange(8.)))
    result=rebuild_industry(frame,releases)
    frame.actual=-frame.actual*1000;again=rebuild_industry(frame,releases+[dict(published='2021-01-01',table_path='/does/not/exist')])
    pd.testing.assert_frame_equal(result[['industry_id','industry_mom63','industry_breadth63']],again[['industry_id','industry_mom63','industry_breadth63']])
    assert result.industry_published.lt(result.date).all();assert result.industry_mom63.iloc[0]==4


def test_publication_on_prediction_date_is_unavailable(tmp_path):
    frame=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31']),instrument=['SZ000001'],mom63=[.1],mom126=[.2]))
    out=rebuild_industry(frame,[dict(published='2020-01-31',table_path='/does/not/exist')])
    assert out.industry_id.iloc[0]=='UNKNOWN'


def test_brier_and_nested_error_decomposition_exact():
    frame=pd.DataFrame(dict(actual=[-.3,.2,-.4,.1,.2,.3,.4,.5],probability=[.3,.2,.4,.1,.2,.3,.4,.1],industry_id=['A']*4+['B']*4,board=[0]*8,log_cap=np.arange(8.),vol63=np.arange(8.)+.1))
    d=error_decomposition(frame)
    assert d['total']==pytest.approx(np.mean((frame.probability-labels(frame.actual))**2))
    assert sum(d[k] for k in ['common_error','industry_error','risk_cell_error','individual_error'])==pytest.approx(d['total'])


def test_group_auc_insufficient_events_reported_not_forced():
    f=pd.DataFrame(dict(industry_id=['C']*8,actual=[-.3]+[.1]*7,probability=np.arange(8)/10))
    result,audit=conditional_auc(f);assert np.isnan(result['conditional_auc']);assert audit[0]['status']=='too_few_events' and result['coverage']==0


def test_group_auc_constant_predictor_has_half_auc():
    f=pd.DataFrame(dict(industry_id=['C']*8,actual=[-.3]*3+[.1]*5,probability=[.2]*8))
    result,audit=conditional_auc(f);assert result['conditional_auc']==.5 and result['coverage']==1


def test_conditional_permutation_preserves_month_industry_and_missing():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31']*12),industry_id=['A']*6+['B']*6,y_6=[-.5,-.3,.1,.2,.3,np.nan]*2))
    new=permute_conditionally(f)
    for name,g in f.groupby(['date','industry_id']):
        z=new.loc[g.index];np.testing.assert_array_equal(g.y_6.isna(),z.y_6.isna());assert (g.y_6<-.2).sum()==(z.y_6<-.2).sum()
    pd.testing.assert_frame_equal(new,permute_conditionally(f))


def match_frame():
    n=30
    return pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31']*n),industry_id=['C26']*n,board=[0]*n,instrument=[f'S{i:03d}' for i in range(n)],log_cap=np.linspace(24,24.05,n),vol63=np.linspace(.3,.31,n),p_base=[.2]*n,p_full=np.linspace(.1,.5,n),actual=np.arange(n)))


def test_matching_is_observable_and_caliper_limited_without_reuse():
    f=match_frame();a=make_pairs(f);f.actual=-f.actual*100;f['future_bad_event']=True;b=make_pairs(f)
    pd.testing.assert_frame_equal(a,b);assert len(a)>0
    assert (a.log_cap_gap<=.35).all() and (a.log_vol_gap<=.2).all()
    assert len(set(a.high)|set(a.low))==2*len(a)


def test_matching_refuses_risk_distance_instead_of_relaxing_to_fill():
    f=match_frame();f.loc[f.p_full>.3,'log_cap']=30
    assert len(make_pairs(f))==0


def test_warning_group_before_future_missing_filter():
    p=[.9,.2,.1,.05];flag=warning(p,['A','B','C','D'],.2);r=metrics(p,[np.nan,-.4,.2,.3],{'20':flag})
    assert np.isnan(r['precision20']) and r['rows']==3


def test_strict_label_maturity_and_quarter_freeze():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2019-01-31','2019-02-28','2020-04-30']),end_6=pd.to_datetime(['2020-03-31','2020-04-01',None]),y_6=[-.3,.1,np.nan]))
    train,test=split(f,6,pd.Period('2020Q2'));assert len(train)==1 and len(test)==1


def test_bootstrap_missing_calendar_preserved():
    result=ci([0.,np.nan,0.,np.nan,0.],6);assert result['months']==5 and result['defined_months']==3 and result['high95']==0


def test_global_offset_recovers_probability_without_changing_ranks():
    dates=np.repeat(pd.date_range('2000-01-31',periods=12,freq='ME'),10);y=np.tile([1]*4+[0]*6,12)
    fit=fit_offset(np.full(120,.1),y,np.zeros((120,4)),dates,state=False);assert fit['success']
    out=apply_offset(np.full(3,.1),np.zeros((3,4)),fit);np.testing.assert_allclose(out,.4,atol=1e-5)
    ranked=apply_offset(np.array([.05,.1,.2]),np.zeros((3,4)),fit);assert (np.diff(ranked)>0).all()


def test_calibration_never_uses_equal_date_maturity_or_future_origin():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2019-01-31','2019-02-28','2020-04-30']),label_end=pd.to_datetime(['2020-03-31','2020-04-01',None]),actual=[-.3,.2,np.nan],instrument=['A','B','C']))
    assert len(mature_calibration_rows(f,pd.Timestamp('2020-04-01')))==1


def test_industry_neutral_targets_unknowns_kept_and_no_future_selection():
    f=match_frame();f['log_money21']=np.log1p(1e8);f.loc[:2,'industry_id']='UNKNOWN'
    a,chosen=select(f);f.actual=-f.actual*10;_,new=select(f)
    for key in chosen:
        np.testing.assert_array_equal(chosen[key],new[key]);assert chosen[key][a.industry_id.eq('UNKNOWN')].all()
    counts=[a.loc[m].groupby('risk_cell').size() for m in chosen.values()]
    assert all(counts[0].equals(v) for v in counts[1:])


def test_liquidity_cap_and_transaction_cash_conservation():
    h,c,t,fee,limited=trade(np.zeros(2),1.,np.array([1.,1.]),np.array([1.,1.]),np.array([.5,.5]),np.array([.1,100.]),.01)
    assert h[0]<=.1+1e-12 and c>=0 and limited==1
    assert h.sum()+c+fee==pytest.approx(1.)


def test_missing_quote_cannot_sell_and_drawdown_duration():
    h,c,t,fee,limited=trade(np.array([1.]),0.,np.array([np.nan]),np.array([1.]),np.array([0.]),np.array([100.]),.01)
    assert h[0]==1 and t==0 and c==0
    assert drawdown_duration([0.,-.1,-.2,0.,-.1])==2
