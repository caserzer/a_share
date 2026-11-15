import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
from integrated_monitor_r93 import build

def inputs():
 key=dict(era='SW2021',level='L3',industry_code='a',industry_name='A',asof='2026-10-21')
 t=pd.DataFrame([dict(**key,task='return',horizon=20,method='F',cohort='F',prediction=float('nan'),last_prediction=.2)])
 e=pd.DataFrame([dict(**key,clock=c,facts=c) for c in ['publication_proxy','inherited_archive','ep35_acquisition']])
 return t,e

def test_clock_isolation_and_old_prediction_not_promoted():
 t,e=inputs();d,clocks,extra=build(t,e)
 assert len(d)==1 and len(clocks)==3 and extra.empty
 assert d.evidence_facts.iloc[0]=='publication_proxy' and pd.isna(d.prediction.iloc[0]) and d.last_prediction.iloc[0]==.2

def test_archive_does_not_replace_missing_publication_view():
 t,e=inputs();d,_,_=build(t,e[e.clock.ne('publication_proxy')]);assert d.evidence_join.iloc[0]=='left_only' and pd.isna(d.evidence_facts.iloc[0])

def test_duplicate_evidence_and_identity_conflict_rejected():
 t,e=inputs()
 with pytest.raises(AssertionError):build(t,pd.concat([e,e.iloc[:1]]))
 e.loc[e.clock.eq('publication_proxy'),'industry_name']='Other'
 with pytest.raises(AssertionError):build(t,e)
