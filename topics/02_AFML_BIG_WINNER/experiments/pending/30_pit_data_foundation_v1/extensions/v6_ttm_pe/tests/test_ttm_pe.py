"""Temporal leakage, missingness, source isolation, identities and integrity tests."""
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pe_common import CACHE, OUT, sha, write_json
from pe_identity import Identity, normalize
from ttm_pe_dataset import D2TTMPEDataset
from readiness import valid_window
from acquire import access_denied

@pytest.fixture
def release(tmp_path):
    inputs=CACHE/'building/inputs'
    if not inputs.exists():
        inputs=Path(json.loads((OUT/'release.json').read_text())['path'])/'inputs'
    shutil.copytree(inputs,tmp_path/'inputs')
    identity=Identity(tmp_path/'inputs')
    for provider,values in [('baostock',[10.,-5.,0.,None,np.inf]),('eastmoney',[20.,-6.,0.,None,np.inf])]:
        codes=['sh.600000','sz.000001','sh.600004','sh.600006','sh.600007']
        if provider=='baostock':
            frame=pd.DataFrame(dict(date=['2021-01-04']*5,code=codes,peTTM=values,adjustflag=['3']*5))
        else:
            frame=pd.DataFrame(dict(TRADE_DATE=['2021-01-04']*5,
                SECUCODE=[x[3:]+'.'+x[:2].upper() for x in codes],PE_TTM=values))
        receipt=dict(parquet_sha256='a'*64,response_sha256=['b'*64],
            observed_at='2026-11-08T01:00:00Z',ingested_at='2026-11-08T01:00:05Z')
        f=normalize(frame,'2021-01-04',receipt,identity,provider)
        p=tmp_path/f'normalized/{provider}/2021-01-04.parquet';p.parent.mkdir(parents=True)
        f.to_parquet(p,index=False)
    files=[dict(relative_path=str(p.relative_to(tmp_path)),sha256=sha(p)) for p in tmp_path.rglob('*.parquet')]
    write_json(tmp_path/'FULL_MANIFEST.json',files)
    write_json(tmp_path/'COMPLETE.json',dict(full_manifest_sha256=sha(tmp_path/'FULL_MANIFEST.json'),
        identity_snapshot_observed_at='2026-11-08T00:00:00Z'))
    return tmp_path

def test_provider_isolation(release):
    d=D2TTMPEDataset(release)
    assert d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy').value==20
    assert d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy',provider='baostock').value==10

@pytest.mark.parametrize('quality',['PIT-certified','PIT-reconstructed','UNKNOWN/BLOCKED'])
def test_strict_never_returns_vendor_values(release,quality):
    d=D2TTMPEDataset(release)
    r=d.get_asof('SH600000','vendor_pe_ttm','2021-01-04 15:00',quality_tier=quality)
    assert r.value is None and pd.isna(r.records[0]['vendor_pe_ttm']) and pd.isna(r.records[0]['pe_ttm'])
    assert d.universe_asof('2021-01-04 15:00',quality_tier=quality).empty

def test_default_strict(release):
    assert D2TTMPEDataset(release).get_asof('SH600000','pe_ttm','2021-01-04 15:00').value is None

@pytest.mark.parametrize('time,expected',[('2021-01-04 14:59:59','2020-12-31'),('2021-01-04 15:00','2021-01-04'),('2021-01-05 10:00','2021-01-04'),('2021-01-09 16:00','2021-01-08')])
def test_close_boundary_and_weekend(release,time,expected):
    assert D2TTMPEDataset(release).session(time)==pd.Timestamp(expected)

def test_no_stale_fill(release):
    d=D2TTMPEDataset(release)
    r=d.get_asof('SH600000','pe_ttm','2021-01-05 15:00',quality_tier='Historical-proxy')
    assert r.value is None and r.reason=='NO_EXACT_SESSION_DATA'

def test_missing_and_observed_queries_have_same_provenance_schema(release):
    d=D2TTMPEDataset(release)
    sid=d.identity.inventory.loc[d.identity.inventory.instrument.eq('SH600000'),'security_id'].item()
    u=pd.DataFrame({'security_id':[sid]})
    a=d.join_universe(u,'2021-01-04 15:00',quality_tier='Historical-proxy')
    b=d.join_universe(u,'2021-01-05 15:00',quality_tier='Historical-proxy')
    c=d.join_universe(u,'2021-01-04 15:00')
    assert set(a.columns)==set(b.columns)==set(c.columns)
    assert pd.isna(b.source_observed_at.iloc[0]) and pd.isna(c.source_observed_at.iloc[0])

def test_before_first_session_and_after_cutoff(release):
    d=D2TTMPEDataset(release)
    assert d.session('2017-01-03 09:30') is None
    assert d.session('2026-10-22 15:00') is None
    f=d.universe_asof('2026-10-22 15:00',quality_tier='Historical-proxy')
    assert f.empty and f.attrs['population_status']=='OUTSIDE_FROZEN_CALENDAR'

def test_historical_download_not_known_at(release):
    d=D2TTMPEDataset(release)
    r=d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy')
    assert pd.isna(r.records[0]['pe_known_at'])
    a=d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy',mode='archived')
    assert a.value is None and a.reason=='NOT_YET_ARCHIVED'
    assert d.universe_asof('2021-01-04 15:00',quality_tier='Historical-proxy',mode='archived').empty

@pytest.mark.parametrize('code,reason,raw',[('SZ000001','NONPOSITIVE_EARNINGS_PROXY',-6),('SH600004','ZERO_OR_UNDEFINED',0),('SH600006','MISSING',None),('SH600007','NONFINITE',None)])
def test_nonpositive_and_invalid_not_expansion(release,code,reason,raw):
    d=D2TTMPEDataset(release)
    r=d.get_asof(code,'pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy')
    assert r.value is None and r.reason==reason
    r=d.get_asof(code,'vendor_pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy')
    assert r.value==raw

def test_historical_code_change_intervals(release):
    d=D2TTMPEDataset(release)
    a=d.identity.mapping('2018-12-25');b=d.identity.mapping('2018-12-26')
    assert 'SZ000022' in set(a.instrument) and 'SZ000022' not in set(b.instrument)
    assert a.loc[a.instrument.eq('SZ000022'),'security_id'].item()==b.loc[b.instrument.eq('SZ001872'),'security_id'].item()

def test_vendor_retroactive_codes_preserve_historical_identity(release):
    identity=Identity(release/'inputs')
    frame=pd.DataFrame(dict(TRADE_DATE=['2021-01-04'],SECUCODE=['302132.SZ'],PE_TTM=[10.]))
    receipt=dict(parquet_sha256='a'*64,response_sha256=['b'*64],observed_at='2026-11-08T00:00Z',ingested_at='2026-11-08T00:01Z')
    f=normalize(frame,'2021-01-04',receipt,identity,'eastmoney')
    assert f.iloc[0].provider_instrument=='SZ302132'
    assert f.iloc[0].instrument=='SZ300114'
    assert f.iloc[0].identity_status=='RETROSPECTIVE_VENDOR_CODE_MAPPED_BY_REVIEWED_ALIAS'

@pytest.mark.parametrize('values,expected', [([10.,10.],10.),([10.,11.],None)])
def test_source_alias_duplicates_agree_or_quarantine(release,values,expected):
    identity=Identity(release/'inputs')
    frame=pd.DataFrame(dict(date=['2021-01-04']*2,code=['sz.300114','sz.302132'],peTTM=values,adjustflag=['3']*2))
    receipt=dict(parquet_sha256='a'*64,response_sha256=['b'*64],observed_at='2026-11-08T00:00Z',ingested_at='2026-11-08T00:01Z')
    f=normalize(frame,'2021-01-04',receipt,identity)
    assert len(f)==1 and f.iloc[0].alias_rows==2
    if expected is None:
        assert pd.isna(f.iloc[0].pe_ttm) and f.iloc[0].pe_status=='ALIAS_VALUE_CONFLICT'
    else:
        assert f.iloc[0].pe_ttm==expected
        assert f.iloc[0].provider_instrument=='SZ300114'

def test_universe_keeps_missing_and_excludes_future_listings(release):
    d=D2TTMPEDataset(release)
    f=d.universe_asof('2021-01-04 15:00',quality_tier='Historical-proxy')
    assert len(f)>4000 and f.pe_ttm.notna().sum()==1
    assert f.pe_status.eq('NO_SECURITY_OBSERVATION').sum()>3900
    assert pd.to_datetime(f.listing_date).dropna().le('2021-01-04').all()

def test_duplicate_input_id_rejected(release):
    d=D2TTMPEDataset(release)
    with pytest.raises(ValueError):
        d.join_universe(pd.DataFrame({'security_id':['x','x']}),'2021-01-04 15:00')

@pytest.mark.parametrize('case',['wrong_date','duplicate','adjusted'])
def test_bad_source_rejected(release,case):
    frame=pd.DataFrame(dict(date=['2021-01-04'],code=['sh.600000'],peTTM=[10],adjustflag=['3']))
    if case=='wrong_date':frame['date']='2021-01-05'
    if case=='duplicate':frame=pd.concat([frame,frame])
    if case=='adjusted':frame['adjustflag']='2'
    with pytest.raises(ValueError):normalize(frame,'2021-01-04',{},Identity(release/'inputs'))

def test_corrupted_partition_rejected(release):
    d=D2TTMPEDataset(release)
    p=release/'normalized/eastmoney/2021-01-04.parquet'
    with p.open('ab') as f:f.write(b'changed')
    with pytest.raises(ValueError):d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy')

def test_offline_reader(release):
    with patch('socket.socket',side_effect=AssertionError('network forbidden')):
        d=D2TTMPEDataset(release)
        assert d.get_asof('SH600000','pe_ttm','2021-01-04 15:00',quality_tier='Historical-proxy').value==20

@pytest.mark.parametrize('bad',[np.nan,0,-1,np.inf])
def test_multiscale_windows_do_not_cross_missing_or_nonpositive_days(bad):
    f=pd.DataFrame({'a':[10.,11.,bad,13.,14.,15.]})
    v=valid_window(f,2).a.tolist()
    assert v==[False,False,False,False,False,True]

def test_window_does_not_use_future_values():
    f=pd.DataFrame({'a':np.arange(1.,101.)})
    first=valid_window(f,21)
    f.loc[60:,'a']=np.nan
    assert first.loc[:59].equals(valid_window(f,21).loc[:59])

@pytest.mark.parametrize('message',['黑名单用户，请与管理员联系','BLACKLIST USER','访问受限','权限不足'])
def test_explicit_access_denial_is_not_retriable_network_error(message):
    assert access_denied(message)
