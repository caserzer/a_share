from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.stats import skew
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from core import labels,metrics,weights,split,bootstrap_indices,ci,warning,feature_names,C
from features import hill,shape,risk_structure,tail_loading
from conditional import conditional_auc,make_pairs,error_decomposition
from controls import permute_conditionally
from calibrate import offset_fit,history_rows
from scipy.special import expit,logit


def test_strict_event_and_missing():
    np.testing.assert_equal(labels([-.2,-.200001,0,np.nan]),[0,1,0,np.nan])


def test_permutation_preserves_group_counts_and_missing_positions():
    f=pd.DataFrame(dict(date=np.repeat(pd.to_datetime(['2020-01-31','2020-02-28']),20),
        industry_id=np.tile(['a']*10+['b']*10,2),y_6=np.tile([-.3,.1,np.nan,.2,-.4],8)))
    p=permute_conditionally(f)
    for key,g in f.groupby(['date','industry_id']):
        z=p.loc[g.index];np.testing.assert_array_equal(g.y_6.isna(),z.y_6.isna())
        np.testing.assert_array_equal(np.sort(g.y_6.dropna()),np.sort(z.y_6.dropna()))


def test_offset_corrects_constant_rate_without_rank_changes():
    p=np.full(100,.1);y=np.r_[np.ones(30),np.zeros(70)]
    a=offset_fit(p,y,pd.Series(pd.to_datetime(['2020-01-31']*100)))
    assert np.isclose(expit(logit(.1)+a),.3)
    v=np.linspace(.01,.9,100);assert np.array_equal(np.argsort(v),np.argsort(expit(logit(v)+a)))


def test_calibration_never_uses_unmatured_labels():
    raw=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-05-29','2020-08-31']),
        label_end=pd.to_datetime(['2020-07-31','2020-11-30','2021-02-26']),actual=[-.3,.1,-.4]))
    assert len(history_rows(raw,pd.Timestamp('2020-09-01')))==1


def test_hill_known_values_and_scale_invariance():
    x=np.r_[-.08,-.04,-.01,np.ones(37)*.01]
    value,u,n=hill(x,.05,2)
    assert n==2 and u<0
    assert np.isclose(value,np.mean(np.log(np.array([-.08,-.04])/u)))
    assert np.isclose(value,hill(x*2,.05,2)[0])


def test_hill_insufficient_or_nonnegative():
    assert np.isnan(hill(np.arange(100)/100,.05,2)[0])
    assert np.isnan(hill(-np.arange(1,11)/100,.05,2)[0])


def test_shape_against_independent_bias_corrected_skew():
    x=np.linspace(-.1,.05,60)**3
    nc,du=shape(x)
    assert np.isclose(nc,-skew(x,bias=False))
    centered=x-x.mean();down=centered[centered<0];up=centered[centered>0]
    expected=np.log(np.sum(down**2)/(len(down)-1)/(np.sum(up**2)/(len(up)-1)))
    assert np.isclose(du,expected)


def test_shape_missing_not_zero_filled():
    x=np.r_[np.linspace(-.05,.05,60),np.repeat(np.nan,6)]
    assert np.isnan(shape(x)[0])


def test_risk_decomposition_recovers_known_residual_variance():
    rng=np.random.default_rng(42);market=rng.normal(0,.01,3000);industry=rng.normal(0,.01,3000);eps=rng.normal(0,.003,3000)
    values=risk_structure(.8*market+1.2*industry+eps,market,industry)
    assert abs(values[0]-.8)<.04 and abs(values[1]-1.2)<.04
    assert abs(values[2]-.003*np.sqrt(252))<.004
    assert 0<values[3]<.1 and values[4]>.4


def test_structure_missing_and_collinearity_fail_closed():
    assert np.isnan(risk_structure(np.arange(10),np.arange(10),np.arange(10))).all()
    assert np.isnan(risk_structure(np.arange(60),np.arange(60),np.arange(60))).all()


def test_loading_lag_inputs_and_minimum_history():
    x=np.linspace(-1,1,40);y=2+3*x
    assert np.isclose(tail_loading(y,x),3)
    assert np.isnan(tail_loading(y[:35],x[:35]))


def test_no_target_in_any_feature_set():
    for model in C['candidates']:
        assert not any(x.startswith(('y_','end_','future_','target_')) for x in feature_names(model))


def test_training_requires_label_mature_before_quarter():
    p=pd.DataFrame({'date':pd.to_datetime(['2020-01-31','2020-12-31','2021-01-29']),
                    'end_6':pd.to_datetime(['2020-07-31','2021-07-01','2021-08-02']),'y_6':[0,-.3,.1]})
    train,test=split(p,6,pd.Period('2021Q1'));assert len(train)==1 and len(test)==1


def test_month_equal_training_weights():
    f=pd.DataFrame({'date':[1,2,2,2]});w=weights(f)
    assert np.isclose(w[0],sum(w[1:])) and np.isclose(w.mean(),1)


def test_brier_exact_decomposition():
    r=metrics([.1,.8,.4],[0,-.3,np.nan])
    assert np.isclose(r['brier'],.025)
    assert np.isclose(r['brier'],r['common_brier']+r['relative_brier'])


def test_bootstrap_uses_month_blocks_and_keeps_calendar_nan():
    a=bootstrap_indices(60,6,reps=2000);rate=np.mean(a[:,1:]==(a[:,:-1]+1)%60)
    assert .8<rate<.88
    r=ci([1.,np.nan,1.,1.]);assert r['months']==4 and r['defined_months']==3 and r['estimate']==1


def test_warning_fraction_and_permutation_determinism():
    stocks=np.array(['a','b','c','d','e']);p=np.ones(5);a=warning(p,stocks,.2);order=np.array([4,1,0,2,3]);b=warning(p[order],stocks[order],.2)
    assert a.sum()==1 and set(stocks[a])==set(stocks[order][b])


def test_conditional_auc_rejects_missing_classes():
    f=pd.DataFrame({'industry_id':['A']*10,'actual':[.1]*10,'probability':np.linspace(0,1,10)})
    result,groups=conditional_auc(f);assert np.isnan(result['conditional_auc']) and groups[0]['status']=='too_few_events'


def test_error_accounting_identity():
    rng=np.random.default_rng(9);n=40
    f=pd.DataFrame({'industry_id':['A']*20+['B']*20,'board':0,'log_cap':rng.normal(size=n),'vol63':rng.uniform(.1,.5,n),'actual':rng.choice([-.3,.1],n),'probability':rng.uniform(size=n)})
    d=error_decomposition(f);assert np.isclose(d['total'],sum(d[k] for k in d if k!='total'))


def test_matching_never_uses_future_outcome():
    n=20;f=pd.DataFrame({'instrument':[str(i) for i in range(n)],'industry_id':'A','board':0,'log_cap':20.,'vol63':.3,'p_base':.2,'p_full':np.linspace(.05,.6,n),'actual':0.})
    a=make_pairs(f);f['actual']=np.arange(n)*100;pd.testing.assert_frame_equal(a,make_pairs(f));assert len(a)>0
