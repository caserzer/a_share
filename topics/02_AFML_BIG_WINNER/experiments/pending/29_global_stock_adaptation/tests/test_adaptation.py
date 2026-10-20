from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import labels,logodds,C
from issuer_adaptation import offset_map,nonoverlap_count,merged_event_stages,temporal_scores,estimate_tau,issuer_fit
from peer_prior import peer_sets,peer_fit
from local_baseline import local_probability
from hierarchical_model import mature_history,one_origin
from controls import permute_identity
from evaluate import weighted_intervals,score


def fixture(n=40,months=48):
    rows=[]
    for t,d in enumerate(pd.date_range('2018-01-31',periods=months,freq='ME')):
        for j in range(n):
            event=(t%(2 if j%2 else 9)==0)
            rows.append(dict(date=d,instrument=f'S{j:04}',log_cap=24+j/40,vol63=.2+j/300,
                market_beta63=.8+j/30,industry_beta63=.5+j/40,idiosyncratic_vol63=.2+j/400,
                industry_id='I1',industry_sector='I',industry_stale=0.,industry_published=d-pd.Timedelta(days=40),
                listing_date=pd.Timestamp('2000-01-01'),board=0,G=.2,GP=.2,actual=-.3 if event else .05,
                event=float(event),label_end=d+pd.DateOffset(months=6),offset_G=float(logodds(.2)),offset_GP=float(logodds(.2))))
    return pd.DataFrame(rows)


def test_event_threshold_strict_and_missing():
    np.testing.assert_equal(labels([-.2,-.2001,0,np.nan]),[0,1,0,np.nan])


def test_posterior_map_matches_closed_stationarity_equation():
    z=np.repeat(logodds(.2),40);y=np.r_[np.ones(20),np.zeros(20)];w=np.ones(40)/7
    fit=offset_map(z,y,w,1.,cap=3.)
    assert abs(np.sum(w*(y-expit(z+fit['estimate'])))-fit['estimate'])<1e-8


def test_stronger_prior_reduces_offset():
    z=np.repeat(logodds(.2),40);y=np.r_[np.ones(25),np.zeros(15)];w=np.ones(40)/7
    assert 0<offset_map(z,y,w,.25)['estimate']<offset_map(z,y,w,1.)['estimate']


def test_offset_is_bounded_even_all_events():
    r=offset_map(np.repeat(-5.,10000),np.ones(10000),np.ones(10000),1.)
    assert r['estimate']==1. and np.isfinite(r['sd'])


def test_fractional_duplicate_weights_do_not_fake_more_information():
    z=np.array([-1.,0.,1.]);y=np.array([0.,1.,1.]);a=offset_map(z,y,np.ones(3),.8,cap=3.)
    b=offset_map(np.repeat(z,7),np.repeat(y,7),np.ones(21)/7,.8,cap=3.)
    assert np.isclose(a['estimate'],b['estimate']) and np.isclose(a['sd'],b['sd'])


def test_single_crash_overlapping_labels_are_one_window():
    f=fixture(1,24);f['event']=0.;f.loc[:5,'event']=1.
    assert nonoverlap_count(f,1)==1 and merged_event_stages(f)==1
    assert issuer_fit(f,'offset_G',1.)['b']==0


def test_separated_event_stages_are_counted():
    f=fixture(1,36);f['event']=0.;f.loc[0:2,'event']=1.;f.loc[20:22,'event']=1.
    assert nonoverlap_count(f,1)==2 and merged_event_stages(f)==2


def test_zero_events_cannot_make_zero_risk():
    f=fixture(1,60);f['event']=0.
    r=issuer_fit(f,'offset_G',1.);assert r['b']==0 and r['reason']=='few_independent_event_windows'
    assert 0<local_probability(f,.2)['probability']<1


def test_no_history_falls_back_and_admits_uncertainty():
    r=issuer_fit(None,'offset_G',1.);assert r['b']==0 and np.isnan(r['posterior_sd'])
    r=local_probability(None,.123);assert r['probability']==.123 and (r['lower'],r['upper'])==(0.,1.)


def test_history_end_equal_cutoff_not_available():
    f=fixture(1,24);date=f.label_end.iloc[10]
    h=mature_history(f,date);assert (h.label_end<date).all() and 10 not in h.index


def test_unmatured_actual_is_never_used():
    f=fixture(1,24);date=pd.Timestamp('2019-05-31')
    a=mature_history(f,date);f.loc[f.label_end>=date,'actual']=-.99;b=mature_history(f,date)
    pd.testing.assert_frame_equal(a,b)


def test_peer_membership_ignores_outcomes_and_excludes_self():
    f=fixture(20,1);before=peer_sets(f);f['actual']=np.arange(len(f));after=peer_sets(f)
    assert before==after
    assert all(stock not in r['peers'] for stock,r in before.items())


def test_stale_industry_and_missing_features_fall_back():
    f=fixture(20,1);f.loc[0,'industry_stale']=1;f.loc[1,'vol63']=np.nan;p=peer_sets(f)
    assert p['S0000']['peers']==[] and p['S0001']['peers']==[]


def test_peer_history_weights_are_month_clustered():
    h=fixture(10,24);row=h.iloc[-1].to_dict()
    a=peer_fit(row,dict(peers=[f'S{i:04}' for i in range(9)],route='industry'),h)
    dup=h.copy();dup['instrument']=dup.instrument+'x';hh=pd.concat([h,dup],ignore_index=True)
    peers=[f'S{i:04}' for i in range(9)]+[f'S{i:04}x' for i in range(9)]
    b=peer_fit(row,dict(peers=peers,route='industry'),hh)
    assert np.isclose(a['a'],b['a']) and np.isclose(a['posterior_sd'],b['posterior_sd'])


def test_temporal_halves_are_purged():
    f=fixture(1,48);assert temporal_scores(f,'offset_G') is not None
    f['label_end']=pd.Timestamp('2099-01-01');assert temporal_scores(f,'offset_G') is None


def test_tau_requires_enough_issuers():
    f=fixture(10,36);assert estimate_tau(dict(tuple(f.groupby('instrument'))),'offset_G')['tau']==0


def test_training_covariance_detects_persistent_effects():
    f=fixture(40,48);r=estimate_tau(dict(tuple(f.groupby('instrument'))),'offset_G')
    assert r['tau']>0 and r['issuers']==40


def test_zero_tau_disables_individual_fit():
    f=fixture(1,60);r=issuer_fit(f,'offset_G',0.)
    assert r['b']==0


def test_current_future_outcomes_do_not_change_predictions():
    history=fixture(40,48);current=history[history.date==history.date.max()].copy()
    current['date']=pd.Timestamp('2022-09-30');current['actual']=np.nan;current['label_end']=pd.NaT
    a,pa,_=one_origin(current,history)
    current['actual']=-.99;current['label_end']=pd.Timestamp('2099-01-01')
    b,pb,_=one_origin(current,history)
    pd.testing.assert_frame_equal(a[C['formal_models']],b[C['formal_models']]);pd.testing.assert_frame_equal(pa,pb)


def test_identity_permutation_keeps_risk_outcome_rows_intact():
    f=fixture(40,3);shuffled,audit=permute_identity(f)
    assert not shuffled.duplicated(['date','instrument']).any()
    assert audit.changed.sum()>0
    for c in ['actual','G','GP','vol63','log_cap','industry_id']:pd.testing.assert_series_equal(f[c],shuffled[c])


def test_weightings_are_distinct_on_unbalanced_panel():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-01-31','2020-02-28']),
        instrument=['a','b','a'],actual=[.1,.1,.1],G=[0.,0.,0.],GPI=[.2,.8,.4]))
    result=weighted_intervals(f,'GPI','G',6,True);r={x['weighting']:x['estimate'] for x in result}
    assert np.isclose(r['pooled'],(.04+.64+.16)/3)
    assert np.isclose(r['month'],((.04+.64)/2+.16)/2)
    assert np.isclose(r['company'],((.04+.16)/2+.64)/2)


def test_brier_common_relative_identity():
    f=fixture(20,1)
    for fraction in [5,10,20]:f[f'flag_G_{fraction}']=False
    r=score(f,'G');assert np.isclose(r['brier'],r['common_brier']+r['relative_brier'])


def test_all_formal_probabilities_are_interior():
    h=fixture(40,48);g=h[h.date==h.date.max()].copy();g['date']=pd.Timestamp('2022-09-30')
    out,_,_=one_origin(g,h)
    assert np.isfinite(out[C['formal_models']].to_numpy()).all()
    assert ((out[C['formal_models']]>0)&(out[C['formal_models']]<1)).all().all()
