import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
import pandas as pd
import pytest
from core import classify, assign_deciles, state_weights, bootstrap, holm
from data_models import grid, fit_linear, predict, split
from accounts import buy_amounts, account, event
from analyze import conditional_metric

def market(n=31):
    class M:pass
    m=M();m.days=pd.bdate_range('2021-01-01',periods=n);m.symbols=pd.Index(['A','B']);m.n=2
    m.c=np.full((n,2),10.);m.o=m.c.copy();m.buy=np.ones((n,2),bool);m.sell=m.buy.copy();m.members=m.buy.copy()
    m.marks={'strict':(m.o,m.c),'flat':(m.o.copy(),m.c.copy())}
    return m

def target(m,entries=(1,),instrument='A',weight=1.):
    return pd.DataFrame([dict(instrument=instrument,state='DD',weight=weight,entry_idx=e,exit_idx=e+10,
                             signal_date=m.days[e-1],entry_date=m.days[e],exit_date=m.days[e+10]) for e in entries])

def test_state_zero_unknown_and_raw_signs():
    assert classify([1,1,-1,-1,0,np.nan],[1,-1,1,-1,1,-1]).tolist()==['UU','UD','DU','DD','ZERO','UNKNOWN']

@pytest.mark.parametrize('n',[100,101,299,300,301])
def test_decile_ties_and_complete_partition(n):
    f=pd.DataFrame({'instrument':[f'S{i:03}' for i in range(n)],'score':np.ones(n)})
    d=assign_deciles(f,'score');assert d.iloc[0]==1 and d.iloc[-1]==10
    sizes=d.value_counts();assert sizes.max()-sizes.min()<=1 and sizes.sum()==n

def test_grid_uses_actual_sessions_not_weeks():
    days=pd.bdate_range('2017-01-01','2021-05-01').difference(pd.to_datetime(['2021-02-11','2021-02-12','2021-02-15']))
    g=grid(days);assert (g.exit_idx-g.entry_idx==10).all()
    z=g.loc[g.entry_date.eq('2021-01-11')].iloc[0];assert days[z.exit_idx]==z.exit_date

def test_balance_weights_no_oversampling_and_unit_date_mean():
    f=pd.DataFrame({'signal_date':[1]*20+[2]*8,'state':['UU']*19+['DD']+['UD']*4+['DU']*4})
    w=state_weights(f);assert len(w)==len(f)
    assert w[:20].mean()==pytest.approx(1) and w[20:].mean()==pytest.approx(1)
    assert w[19]>w[0] and np.isfinite(w).all()

def test_prediction_rejects_future_target():
    f=pd.DataFrame({'x':np.arange(12.),'Z':np.arange(12.),'signal_date':[1]*12,'state':['UU']*12})
    model=fit_linear(f,['x'],'Z',10)
    with pytest.raises(AssertionError):predict(f,model)
    x=f[['x']];before=predict(x,model);f.Z*=999
    assert np.array_equal(before,predict(x,model))

def test_maturity_and_purge():
    dates=pd.date_range('2017-01-01','2021-02-01',freq='10D')
    f=pd.DataFrame({'signal_date':dates,'entry_date':dates+pd.Timedelta(days=1),
                    'exit_date':dates+pd.Timedelta(days=15),'Z':1.,'R':1.})
    cutoff=pd.Timestamp('2020-12-31');m,i,v,r=split(f,cutoff,'expanding',dates[0])
    assert r=='' and m.exit_date.max()<=cutoff and i.exit_date.max()<v.entry_date.min()
    f.loc[f.exit_date>cutoff,'Z']=99999
    m2,*_=split(f,cutoff,'expanding',dates[0]);pd.testing.assert_frame_equal(m,m2)

def test_cash_and_post_fee_weight():
    v=buy_amounts(np.array([.5,.5]),1.,0.,.001)
    assert v.sum()*1.001==pytest.approx(1)
    v=buy_amounts(np.array([.5,.5]),.2,.8,.001)
    assert v.sum()*1.001<=.2+1e-12

def test_repeat_selection_has_two_round_trips():
    m=market();g=target(m,(1,11));d,o,h,r=account(m,g,21,'strict',.001,.002,'test')
    expected=((1-.002)/(1+.001))**2
    assert d[-1]['nav']==pytest.approx(expected)
    assert [x['side'] for x in o]==['BUY','SELL','BUY','SELL']
    assert r['terminal_liquidated'] and max(abs(x['accounting_residual']) for x in d)<1e-12

def test_blocked_exit_does_not_restart_clock_or_add_new_lot():
    m=market();m.sell[11,0]=False;g=target(m,(1,11))
    d,o,h,r=account(m,g,21,'strict',.001,.002,'test')
    sells=[x for x in o if x['side']=='SELL'];buys=[x for x in o if x['side']=='BUY']
    assert len(buys)==1 and sells[0]['actual_age']==11 and sells[0]['date']==m.days[12]
    assert any(x['side']=='BUY_BLOCKED' and x['date']==m.days[11] for x in o)
    assert d[10]['overdue_count']==1

def test_unknown_held_quote_stops_certification():
    m=market();m.c[4,0]=np.nan;m.marks['strict']=(m.o,m.c)
    d,o,h,r=account(m,target(m),11,'strict',0,0,'test')
    assert not r['valuation_complete'] and r['failure']['reason']=='HELD_CLOSE_VALUATION_UNKNOWN'

def test_event_blocked_exit_na_and_failed_buy_cash():
    m=market();m.sell[11,0]=False
    e,_=event(m,target(m),.001,.002);assert np.isnan(e['net_return']) and not e['complete_exit']
    m.buy[1,0]=False
    e,_=event(m,target(m),.001,.002);assert e['net_return']==0 and not e['any_entry']

def test_event_and_account_match_complete_h10():
    m=market();m.c[:,0]=np.linspace(10,16,len(m.days));m.o=m.c.copy();m.marks['strict']=(m.o,m.c)
    g=target(m);e,detail=event(m,g,.001,.002);d,*_=account(m,g,11,'strict',.001,.002,'test')
    assert e['net_return']==pytest.approx(d[-1]['nav']-1)
    assert detail.net_stock_profit.sum()==pytest.approx(e['net_return'])

def test_holm_retains_missing_family_members():
    out=holm([.01,np.nan,.03]);assert out[0]==pytest.approx(.03) and out[2]==pytest.approx(.06) and np.isnan(out[1])

def test_bootstrap_preserves_calendar_missing_slots():
    x=np.r_[np.ones(12),np.full(12,np.nan)];r=bootstrap(x)
    assert r['n']==12 and r['calendar_n']==24 and r['low']==1 and r['high']==1

def test_style_spanned_score_does_not_create_numeric_alpha():
    rng=np.random.default_rng(42);x=rng.normal(size=300)
    f=pd.DataFrame({'control':x,'industry':['I']*300,'J_R':3*x+2,'h10':rng.normal(size=300)})
    result=conditional_metric(f,['control'])
    assert result['status']=='NUMERICALLY_ZERO_SCORE_RESIDUAL' and np.isnan(result['ic'])

def test_conditional_projection_keeps_independent_signal():
    rng=np.random.default_rng(42);x=rng.normal(size=300);z=rng.normal(size=300)
    f=pd.DataFrame({'control':x,'industry':['I']*300,'J_R':x+z,'h10':4*x+z})
    result=conditional_metric(f,['control'])
    assert result['ic']==pytest.approx(1) and result['df']==298
