import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from datetime import datetime,timezone
import json
import numpy as np
import pandas as pd
import pytest
from versioned_observations import observations,evaluate_rows,check_capture,source_copy,seal,verify_bundle

def fixture():
    dates=pd.bdate_range('2026-01-01',periods=100)
    d=pd.DataFrame(dict(era='SW2021',level='L3',industry_code='a',industry_name='A',
        date=dates,nav=np.arange(100.,200.),block=1,day_i=range(100),breadth21=.6,breadth63=.5,
        coverage=1.,members=10,membership_asof=dates[0]))
    c=pd.DataFrame(dict(era=['SW2021']*2,level=['L3']*2,industry_code=['a','b'],industry_name=['A','B']))
    return d,pd.Series(100.,index=dates),c

def test_prefix_only_and_complete_catalog_without_outcomes():
    d,b,c=fixture();asof=d.date.iloc[70]
    old=observations(d,b,c,asof,'SW2021')
    d.loc[d.date>asof,'nav']=9999
    d['excess20']=999
    new=observations(d,b,c,asof,'SW2021')
    pd.testing.assert_frame_equal(old,new)
    assert len(new)==2 and new.loc[new.industry_code=='b','status'].iloc[0]=='missing_basket_at_asof'
    assert 'excess20' not in new and 'entry_date' not in new

def test_unlisted_identity_quarantined_not_ranked():
    d,b,c=fixture();c=c[c.industry_code=='b']
    got=observations(d,b,c,d.date.iloc[70],'SW2021')
    assert got.industry_code.tolist()==['b']
    assert got.attrs['quarantined'][0]['industry_code']=='a'

def test_maturity_boundary_and_missing_path_are_distinct():
    d,b,c=fixture()
    obs=observations(d,b,c,d.date.iloc[60],'SW2021')
    pending=evaluate_rows(obs,d,b,d.date.iloc[80])
    assert pending.status.eq('pending_market_sessions').all()
    mature=evaluate_rows(obs,d,b,d.date.iloc[81])
    row=mature[(mature.industry_code=='a')&(mature.horizon==20)].iloc[0]
    assert row.status=='mature' and np.isclose(row.absolute_return,181/161-1)
    missing=d[d.date!=d.date.iloc[70]]
    result=evaluate_rows(obs,missing,b,d.date.iloc[81])
    assert result[(result.industry_code=='a')&(result.horizon==20)].status.iloc[0]=='missing_or_discontinuous_price_path'

def test_forward_cannot_be_backdated_or_before_close():
    now=datetime(2026,11,13,8,tzinfo=timezone.utc)
    assert check_capture('2026-11-13','forward',now)=='forward_candidate'
    with pytest.raises(ValueError):check_capture('2026-11-12','forward',now)
    with pytest.raises(ValueError):check_capture('2026-11-13','forward',datetime(2026,11,13,6,tzinfo=timezone.utc))

def test_seal_idempotence_and_tamper_detection(tmp_path):
    source=tmp_path/'original.txt';source.write_text('one')
    sources={'input':source_copy(source,tmp_path/'store')}
    identity={'sources':{k:v['sha256'] for k,v in sources.items()}}
    bundle=seal(tmp_path/'store','observations',identity,sources,{'a.csv':pd.DataFrame({'x':[1]})},{'created_at':'first'})
    again=seal(tmp_path/'store','observations',identity,sources,{'a.csv':pd.DataFrame({'x':[9]})},{'created_at':'second'})
    assert again==bundle and verify_bundle(bundle)['created_at']=='first'
    source.write_text('two')
    assert verify_bundle(bundle)
    newer=source_copy(source,tmp_path/'store')
    assert newer['sha256']!=sources['input']['sha256']
    (bundle/'a.csv').write_text('corrupted')
    with pytest.raises(ValueError):verify_bundle(bundle)

def test_revised_sources_create_new_evaluation_without_mutating_observation(tmp_path):
    from versioned_observations import capture,evaluate
    d,b,c=fixture();dp=tmp_path/'daily.parquet';mp=tmp_path/'market.parquet';cp=tmp_path/'catalog.csv'
    d.to_parquet(dp,index=False);b.to_frame('close').to_parquet(mp);c.to_csv(cp,index=False)
    store=tmp_path/'store';bundle=capture(store,[dp],mp,cp,str(d.date.iloc[60].date()))
    original=(bundle/'observations.parquet').read_bytes()
    first=evaluate(store,bundle,[dp],mp,str(d.date.iloc[99].date()))
    d.loc[20,'nav']*=1.01;d.to_parquet(dp,index=False)
    second=evaluate(store,bundle,[dp],mp,str(d.date.iloc[99].date()))
    assert first!=second
    assert verify_bundle(second)['historical_price_prefix_changed_rows']==1
    assert (bundle/'observations.parquet').read_bytes()==original
