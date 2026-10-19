import numpy as np
import pandas as pd
from mature_neural_calibration import history_for,fit_history,fit_sign,sign_transform


def test_strict_maturity_excludes_boundary_and_future_changes():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29','2021-02-26','2021-03-31','2021-04-30']),label_end=pd.to_datetime(['2021-02-28','2021-04-30','2021-04-29','2021-06-01']),actual=[.1,-.2,0.,.3]))
    date=pd.Timestamp('2021-04-30')
    assert list(history_for(f,date,'sign').index)==[0]
    assert list(history_for(f,date,'bins').index)==[0,2]
    changed=f.copy();changed.loc[[1,3],'actual']=100
    pd.testing.assert_frame_equal(history_for(f,date,'sign'),history_for(changed,date,'sign'))


def test_recent_window_and_insufficient_history_identity():
    dates=pd.date_range('2019-01-01',periods=40,freq='MS');f=pd.DataFrame(dict(date=dates,label_end=dates+pd.Timedelta(days=1),actual=.1))
    hist=history_for(f,pd.Timestamp('2024-01-01'),'sign');assert hist.date.nunique()==36 and hist.date.min()==dates[4]
    for mode in ['sign','bins']:
        pars,active,info=fit_history(hist.iloc[:11],mode);assert not active and info['iterations']==0
        np.testing.assert_array_equal(pars,np.array([0.]) if mode=='sign' else np.r_[1.,np.zeros(7)])


def test_sign_fit_corrects_bias_and_preserves_zero_rank_and_month_weights():
    p=np.tile(np.array([.03,.03,.03,.01,.3,.3,.3]),(40,1));y=np.r_[np.ones(10),np.zeros(30)]
    dates=np.repeat(pd.to_datetime(['2020-01-01','2020-02-01']),20)
    pars,info=fit_sign(p,y,dates);assert pars[0]<0 and info['penalized_loss']<info['identity_penalized_loss']
    q=sign_transform(p,pars[0]);np.testing.assert_array_equal(q[:,3],p[:,3]);np.testing.assert_allclose(q.sum(axis=1),1)
    # Duplicating every observation of one month must not change its total influence.
    p2=np.concatenate([p,p[:20]]);y2=np.r_[y,y[:20]];dates2=np.r_[dates,dates[:20]]
    pars2,_=fit_sign(p2,y2,dates2);np.testing.assert_allclose(pars,pars2,atol=1e-12)
    r=np.random.default_rng(24).dirichlet(np.ones(7),50);q=sign_transform(r,pars[0])
    np.testing.assert_array_equal(np.argsort(r[:,4:].sum(axis=1)/r[:,:3].sum(axis=1)),np.argsort(q[:,4:].sum(axis=1)/q[:,:3].sum(axis=1)))


def test_boundary_solution_has_correct_gradient():
    p=np.tile([.3,.3,.3,.01,.03,.03,.03],(20,1));pars,info=fit_sign(p,np.ones(20),np.repeat(pd.Timestamp('2020-01-01'),20))
    assert pars[0]==2. and info['gradient']<0
