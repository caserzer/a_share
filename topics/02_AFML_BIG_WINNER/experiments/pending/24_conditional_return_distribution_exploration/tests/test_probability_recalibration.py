import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from probability_recalibration import calibration_history, fit_calibrator, transform, replace_class_mass, fit_mixture
from run_direct_probability import classes


def test_calibration_excludes_current_and_unmatured_labels():
    p=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29','2021-02-26','2021-03-31','2021-04-30']),
        label_end=pd.to_datetime(['2021-02-28','2021-04-30','2021-05-31','2021-06-30']), actual=[.1,.2,.3,.4]))
    assert list(calibration_history(p,pd.Timestamp('2021-04-30')).index)==[0]
    assert list(calibration_history(p,pd.Timestamp('2021-08-31'),2).index)==[2,3]


def test_calibrator_reduces_known_overconfidence_without_invalid_probabilities():
    p=np.zeros((100,7));p[:,0]=.2;p[:,6]=.8
    y=np.r_[np.zeros(80,dtype=int),np.full(20,6,dtype=int)]
    dates=np.repeat(pd.Timestamp('2020-01-31'),100)
    parameters,audit=fit_calibrator(p,y,dates);q=transform(p,parameters)
    np.testing.assert_allclose(q.sum(axis=1),1)
    assert (q>0).all() and .25<=parameters[0]<=4
    assert q[:,6].mean()<.8 and audit['penalized_loss']<audit['identity_penalized_loss']


def test_class_mass_replacement_preserves_shape_and_supplies_absent_class():
    a=np.array([[-.4,-.3,.1,.15]]);w=np.array([[.1,.3,.3,.3]])
    target=np.array([[.2,0,0,.1,0,.7,0]])
    backup=np.repeat([-.3,-.1,-.025,0,.025,.1,.3],32)
    aa,ww=replace_class_mass(a,w,target,backup)
    mass=np.column_stack([(ww*(classes(aa)==k)).sum(axis=1) for k in range(7)])
    np.testing.assert_allclose(mass,target);np.testing.assert_allclose(ww.sum(axis=1),1)
    assert (np.diff(aa,axis=1)>=0).all()
    np.testing.assert_allclose(ww[aa==-.4].sum()/ww[aa==-.3].sum(),1/3)


def test_learned_mixture_is_convex_and_responds_to_valid_history():
    labels=np.array([0,6]*20);target=np.eye(7)[labels]
    base=np.zeros_like(target);base[:,0]=.5;base[:,6]=.5
    bad=np.zeros_like(target);bad[:,0]=.9;bad[:,6]=.1
    stack=np.stack([base,target,bad],axis=1)
    w=fit_mixture(stack,labels,np.repeat(pd.Timestamp('2020-01-31'),len(labels)))
    assert (w>=0).all();np.testing.assert_allclose(w.sum(),1)
    assert w[1]>.5
