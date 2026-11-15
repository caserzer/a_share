import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
from mechanism_links_r20 import build,eligible


def fixture():
 f=dict(evidence_id='op-auto-sales',ts_code='300124.SZ',period='20260630',published_date='2026-08-29',recorded_at='2026-10-10T05:18:44+00:00',ep35_fetched_at='2026-11-13T09:14:13+00:00',source_sha256='abc')
 m=pd.DataFrame([dict(era='SW2021',level='L3',industry_code='a',month=pd.Period('2026-08'),date=pd.Timestamp('2026-08-31'),instrument='SZ300124',security_id='s',unresolved=1)])
 c=pd.DataFrame([dict(era='SW2021',level='L3',industry_code=k,industry_name=k) for k in ['a','b']])
 return f,m,c


def test_three_clocks_and_local_midnight_boundary():
 f,_,_=fixture()
 assert eligible(f,'2026-09-30','publication_proxy')
 assert not eligible(f,'2026-09-30','inherited_archive')
 assert eligible(f,'2026-10-21','inherited_archive')
 assert not eligible(f,'2026-10-21','ep35_acquisition')
 assert not eligible(f,'2026-08-29','publication_proxy')
 f['ep35_fetched_at']='2026-09-30T16:00:00+00:00'
 assert not eligible(f,'2026-09-30','ep35_acquisition')
 f['ep35_fetched_at']='2026-09-30T15:59:59+00:00'
 assert eligible(f,'2026-09-30','ep35_acquisition')


def test_sample_denominator_missing_catalogue_and_deduplication():
 f,m,c=fixture();m=pd.concat([m,m]);m['next_return']=999
 l,full=build([f],m,c,'2026-09-30','publication_proxy')
 a=full.set_index('industry_code').loc['a'];b=full.set_index('industry_code').loc['b']
 assert a.observed_issuers==1 and a.facts==1 and a.all_member_proxy_sample_fraction==.5
 assert b.facts==0 and pd.isna(b.known_member_sample_fraction)
 assert b.evidence_state=='membership_unknown'
 assert len(full)==2 and l.mapping_status.eq('mapped').sum()==1
 assert 'next_return' not in full and 'next_return' not in l
 assert full.economic_stage.eq('not_established').all()


def test_conflicting_identity_not_chosen_arbitrarily():
 f,m,c=fixture();n=m.copy();n['industry_code']='b';m=pd.concat([m,n])
 l,full=build([f],m,c,'2026-09-30','publication_proxy')
 assert l[l.level.eq('L3')].mapping_status.iloc[0]=='ambiguous_identity'
 assert full.facts.sum()==0


def test_future_membership_rejected_and_exchange_exact():
 f,m,c=fixture();m['date']=pd.Timestamp('2026-09-30')
 with pytest.raises(ValueError,match='future membership'):build([f],m,c,'2026-09-30','publication_proxy')
 m['date']=pd.Timestamp('2026-08-31');m['instrument']='SH300124'
 l,full=build([f],m,c,'2026-09-30','publication_proxy')
 assert l.mapping_status.eq('missing_identity').all() and full.facts.sum()==0
