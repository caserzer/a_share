import numpy as np
import pandas as pd
import pytest
import torch
from scipy.stats import spearmanr
from model import Transform, predict, soft_rankic, date_rankic, train_rankic


def test_soft_rank_gradient_matches_finite_difference():
    s=torch.tensor([[.2,-.7,1.1,.4]],dtype=torch.float64,requires_grad=True)
    y=torch.tensor([[2.,1.,4.,3.]],dtype=torch.float64);mask=torch.ones_like(y)
    loss=soft_rankic(s,y,mask,.3).sum();loss.backward()
    for j in range(4):
        up=s.detach().clone();down=up.clone();up[0,j]+=1e-6;down[0,j]-=1e-6
        finite=((soft_rankic(up,y,mask,.3)-soft_rankic(down,y,mask,.3))/(2e-6)).item()
        assert abs(finite-s.grad[0,j].item())<1e-7
    assert torch.linalg.vector_norm(s.grad)>0


def test_padding_cannot_change_loss_or_real_gradient():
    s=torch.tensor([[.2,-.7,1.1,.4]],dtype=torch.float64,requires_grad=True)
    y=torch.tensor([[2.,1.,4.,3.]],dtype=torch.float64)
    l=soft_rankic(s,y,torch.ones_like(y));l.sum().backward()
    sp=torch.tensor([[.2,-.7,1.1,.4,100.,-100.]],dtype=torch.float64,requires_grad=True)
    yp=torch.tensor([[2.,1.,4.,3.,900.,-900.]],dtype=torch.float64)
    mask=torch.tensor([[1.,1.,1.,1.,0.,0.]],dtype=torch.float64)
    lp=soft_rankic(sp,yp,mask);lp.sum().backward()
    assert torch.allclose(l,lp,atol=1e-12)
    assert torch.allclose(s.grad,sp.grad[:,:4],atol=1e-12)
    assert torch.equal(sp.grad[:,4:],torch.zeros_like(sp.grad[:,4:]))


def test_rankic_is_within_date_not_pooled():
    f=pd.DataFrame(dict(signal_date=[1]*4+[2]*4,h10=[1,2,3,4,100,200,300,400]))
    scores=np.array([101,102,103,104,4,3,2,1])
    assert np.allclose(date_rankic(f,scores),[1,-1])
    assert not np.isclose(spearmanr(scores,f.h10).statistic,0)


def test_transform_uses_only_training_statistics_and_preserves_constant():
    t=Transform().fit(pd.DataFrame(dict(a=[1.,3.,np.nan],b=[7.,7.,7.])))
    x=t.transform(pd.DataFrame(dict(a=[100.,np.nan],b=[7.,7.])))
    assert t.median.tolist()==[2.,7.]
    assert t.sd[1]==1 and np.all(x[:,1]==0) and x[1,0]==0
    assert x[0,0]>100


def test_prediction_rejects_labels():
    with pytest.raises(AssertionError):predict(pd.DataFrame({'h10':[1.]}),{})


def test_rankic_model_learns_synthetic_order_and_is_deterministic():
    rng=np.random.default_rng(42);rows=[]
    for d in range(12):
        x=rng.normal(size=(30,3));y=x[:,0]-.7*x[:,1]+rng.normal(size=30)*.1
        f=pd.DataFrame(x,columns=['a','b','c']);f['signal_date']=d;f['h10']=y
        f['target_z']=(y-y.mean())/y.std();f['target_rank']=pd.Series(y).rank()/31-.5;rows.append(f)
    data=pd.concat(rows,ignore_index=True)
    cfg=dict(torch_threads=2,seed=42,lr=.005,batch_dates=4,temperature=.1,max_steps=12,selection_steps=[6,12])
    m,trace,step=train_rankic(data,['a','b','c'],cfg,validation=data)
    m2,_,_=train_rankic(data,['a','b','c'],cfg,validation=data)
    pred=predict(data.drop(columns=['h10','target_z','target_rank']),m)
    assert date_rankic(data,pred).mean()>.98
    assert m==m2 and step in [6,12] and len(m['coef'])==3
    assert np.isclose(np.linalg.norm(m['coef']),1)


def test_positive_scale_and_shift_invariance():
    s=torch.tensor([[.1,.7,-.2,2.]],dtype=torch.float64)
    y=torch.tensor([[3.,2.,1.,4.]],dtype=torch.float64);mask=torch.ones_like(y)
    assert torch.allclose(soft_rankic(s,y,mask),soft_rankic(3*s+10,y,mask),atol=1e-12)
