import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from evaluate_improvement_search import paired_margin_interval
from run_improvement_round1 import class_distribution,normalize_features
from run_direct_probability import weighted_stats


def test_relative_twenty_percent_gate_and_direction():
    base=np.repeat(.25,24)
    lo,hi=paired_margin_interval(np.repeat(.2,24),base,'brier')
    assert abs(lo)<1e-12 and abs(hi)<1e-12
    lo,hi=paired_margin_interval(np.repeat(.21,24),base,'brier')
    assert hi<0
    lo,hi=paired_margin_interval(np.repeat(.6,24),np.repeat(.5,24),'accuracy')
    assert abs(lo)<1e-12


def test_class_distribution_preserves_probability_and_shape():
    y=np.array([-.3,-.1,-.01,0,.01,.1,.3]);c=np.arange(7)
    probabilities=np.array([[.1,.1,.1,.1,.1,.1,.4],[.1,.1,.2,0,.2,.2,.2]])
    atoms,weights=class_distribution(y,c,probabilities)
    stats=weighted_stats(atoms,weights,np.array([np.nan,np.nan]))
    np.testing.assert_allclose(stats.p_up,probabilities[:,4:].sum(axis=1))
    np.testing.assert_allclose(stats.p_down,probabilities[:,:3].sum(axis=1))
    assert stats.brier.isna().all()


def test_feature_scaling_does_not_fit_test_data():
    train=pd.DataFrame({'a':[0.,1.,2.,3.]});test=pd.DataFrame({'a':[1.,100000.]})
    _,x=normalize_features(train,test,['a']);_,y=normalize_features(train,test.iloc[:1],['a'])
    np.testing.assert_array_equal(x.iloc[:1],y)


def test_prequential_weights_ignore_unmatured_and_future_outcomes():
    from run_prequential_search import mature_history,choose_weights
    rows=[]
    for date in pd.date_range('2020-01-31',periods=15,freq='ME'):
        for model,p in [('B',.55),('candidate',.7)]:
            rows.append(dict(date=date,label_end=date+pd.Timedelta(days=40),model=model,
                actual=.1,p_up=p,p_down=1-p,brier=(1-p)**2,multiclass_brier=(1-p)**2,crps=(1-p)))
    data=pd.DataFrame(rows);cutoff=pd.Timestamp('2021-03-01')
    first=choose_weights(mature_history(data,cutoff),['B','candidate'])
    data.loc[data.label_end>=cutoff,['actual','brier','multiclass_brier','crps']]=999
    second=choose_weights(mature_history(data,cutoff),['B','candidate'])
    np.testing.assert_array_equal(first[0],second[0]);assert first[1]==second[1]
    assert (mature_history(data,cutoff).label_end<cutoff).all()


def test_distribution_mixture_exact_crps_and_probabilities():
    from run_prequential_search import combine_distributions,calibrate_equal_atoms
    a=np.array([[-.1,.1]]);b=np.array([[-.2,.2]])
    atoms,weights=combine_distributions([(a,np.array([[.25,.75]])),(b,np.array([[.5,.5]]))],[.4,.6])
    s=weighted_stats(atoms,weights,[.03])
    expected=(weights*np.abs(atoms-.03)).sum()-.5*(weights[:,:,None]*weights[:,None,:]*np.abs(atoms[:,:,None]-atoms[:,None,:])).sum()
    np.testing.assert_allclose(s.crps,expected)
    np.testing.assert_allclose(s.p_up,.6)
    hist=pd.DataFrame({'date':pd.date_range('2020-01-01',periods=12,freq='MS'),'pit':np.linspace(0,1,12)})
    w=calibrate_equal_atoms(hist,200)
    assert (w>0).all();np.testing.assert_allclose(w.sum(),1)


def test_market_component_can_be_removed_by_zero_beta():
    from run_market_residual_search import combine_components
    residual=np.array([[-.1,0,.1]])
    a=combine_components(np.array([-1.,0,1.]),residual,np.array([0.]),np.array([1.]))
    b=combine_components(np.array([-100.,0,100.]),residual,np.array([0.]),np.array([1.]))
    np.testing.assert_allclose(a,b)


def test_cross_sectional_features_do_not_use_other_months_or_labels():
    from run_rank_residual_search import cross_sectional_ranks
    d=pd.DataFrame({'date':[1,1,2,2],'value':[1,2,100,200],'actual':[1,2,3,4]})
    first=cross_sectional_ranks(d,['value']).iloc[:2]
    d.loc[d.date==2,'value']=-999;d['actual']=-999
    pd.testing.assert_frame_equal(first,cross_sectional_ranks(d,['value']).iloc[:2])
