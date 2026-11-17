"""Falsification-specific mathematical and point-in-time regression checks."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import alpha_falsification as a


def frame(n=160):
    rng=np.random.default_rng(17)
    f=pd.DataFrame(rng.normal(size=(n,len(a.PRICE+a.EXTRA))),columns=a.PRICE+a.EXTRA)
    f['industry']=np.where(np.arange(n)%2,'A','B')
    f['score']=f.mom20*2+f.mom1*.5+rng.normal(size=n)
    return f


def test_projection_orthogonal_and_reconstructs_score():
    f=frame();fit,res,info=a.score_decomposition(f,'available_style')
    np.testing.assert_allclose(fit+res,f.score,atol=1e-12)
    assert info['residual_orthogonality']<1e-10
    assert 0<info['r2']<1


def test_press_matches_explicit_leave_one_out():
    f=frame();x=a.design(f,'price_industry');y=f.score.to_numpy()
    fit,res,q,_=a.project(x,y);loo=res/(1-np.sum(q*q,axis=1))
    for i in [0,20,130]:
        mask=np.arange(len(f))!=i
        coef=np.linalg.lstsq(x[mask],y[mask],rcond=1e-12)[0]
        assert loo[i]==pytest.approx(y[i]-x[i]@coef,abs=1e-10)


def test_fwl_equals_joint_regression():
    f=frame();rng=np.random.default_rng(31)
    f['h10']=.02*f.score+.1*f.mom60+rng.normal(0,.01,len(f))
    f['explained'],f['residual'],_=a.score_decomposition(f,'available_style')
    r=a.evaluate(f,'available_style','h10')
    x=a.design(f,'available_style');s=(f.score-f.score.mean())/f.score.std(ddof=0)
    coef=np.linalg.lstsq(np.column_stack([x,s]),f.h10,rcond=1e-12)[0][-1]
    assert r['conditional_slope']==pytest.approx(coef,abs=1e-12)


def test_pure_style_score_has_no_residual_information():
    f=frame();f['score']=2*f.mom20-f.mom1
    fit,res,info=a.score_decomposition(f,'price')
    assert info['r2']==pytest.approx(1)
    assert np.isnan(a.rankcorr(res,np.arange(len(res))))


def test_labels_never_enter_score_decomposition():
    f=frame();f['h10']=0.;v=a.score_decomposition(f,'available_style')[:2]
    f['h10']=np.arange(len(f))*1000
    w=a.score_decomposition(f,'available_style')[:2]
    np.testing.assert_array_equal(v,w)


def test_holm_keeps_missing_member_in_family():
    np.testing.assert_allclose(a.holm([.01,.04,.03]),[.03,.06,.06])
    result=a.holm([.01,np.nan]);assert result[0]==.02 and np.isnan(result[1])


def test_bootstrap_retains_missing_calendar_weeks():
    idx=pd.date_range('2021-01-08',periods=80,freq='W-FRI')
    s=pd.Series(np.sin(np.arange(80)),index=idx).drop(idx[25:35])
    r=a.calendar_bootstrap(s)
    assert r['calendar_weeks']==80 and r['n']==70
    assert r==a.calendar_bootstrap(s)


def test_styles_do_not_use_future_rows(tmp_path,monkeypatch):
    dates=pd.bdate_range('2020-01-01',periods=100);symbols=['SH600000','SZ000001']
    rng=np.random.default_rng(1)
    close=pd.DataFrame(np.exp(np.cumsum(rng.normal(0,.01,(100,2)),axis=0)),index=dates,columns=symbols)
    close.to_parquet(tmp_path/'qfq_close.parquet')
    pd.DataFrame({'close':np.exp(np.cumsum(rng.normal(0,.01,100)))},index=dates).to_parquet(tmp_path/'market.parquet')
    (close*1e7).to_parquet(tmp_path/'money.parquet');(close*.01).to_parquet(tmp_path/'turnover_rate.parquet')
    pd.DataFrame(dict(ts_code=['600000.SH','000001.SZ'],in_date=['20190101']*2,out_date=[None]*2,l1_code=['A','B'])).to_parquet(tmp_path/'industry.parquet')
    f=pd.DataFrame(dict(signal_date=[dates[79]]*2,instrument=symbols,**{k:[1.,2.] for k in a.PRICE}))
    monkeypatch.setattr(a,'PRIVATE',tmp_path)
    original=a.style_panel(f)
    close.iloc[80:]*=100;close.to_parquet(tmp_path/'qfq_close.parquet')
    later=a.style_panel(f)
    pd.testing.assert_frame_equal(original,later)
