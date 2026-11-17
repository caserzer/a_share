import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
import pytest
from e1_reversal_validation import extract_sleeve,forward_eligibility

def test_isolate_overlap_without_changing_retained_budget():
 o=pd.Series({'A':.3,'B':.2,'C':.5});a=pd.Series({'A':.3,'D':.2,'C':.5});s=pd.Series({'A':.6,'B':.4})
 rev,rest=extract_sleeve(o,a,s,.5)
 assert rev.to_dict()=={'A':.6,'D':.4}
 assert np.isclose(rest.sum(),.5) and rest['C']==.5

def test_changed_retained_holding_rejected():
 with pytest.raises(ValueError):
  extract_sleeve(pd.Series({'A':.5,'B':.5}),pd.Series({'A':1.}),pd.Series({'A':1.}),.5)

def record():
 return dict(signal_date='2026-12-04',signal_decision_at='2026-12-04T15:00:00+08:00',generated_at='2026-12-04T16:00:00+08:00',entry_at='2026-12-07T09:30:00+08:00',inputs_known_at='2026-12-04T15:00:00+08:00',model_frozen_at='2026-10-01T00:00:00+08:00',protocol_sha256='protocol',input_manifest_sha256='a'*64,model_sha256='b'*64,predictions_sha256='c'*64,targets_sha256='d'*64,future_outcomes_seen=False,phase=1)

def test_forward_gate_rejects_historical_signal_and_late_registration():
 r=record();assert forward_eligibility(r,'2026-11-17','protocol')[0]
 r['signal_date']='2025-02-07';assert not forward_eligibility(r,'2026-11-17','protocol')[0]
 r=record();r['generated_at']='2026-12-08T16:00:00+08:00';assert not forward_eligibility(r,'2026-11-17','protocol')[0]

def test_forward_gate_does_not_assume_unseen_returns():
 r=record();r.pop('future_outcomes_seen');assert not forward_eligibility(r,'2026-11-17','protocol')[0]
 r=record();r['inputs_known_at']='2026-12-04T17:00:00+08:00';assert not forward_eligibility(r,'2026-11-17','protocol')[0]

def test_strict_gate_rejects_relabelled_past_decision():
 from e1_reversal_forward_gate import validate_metadata
 r=record();r['signal_decision_at']='2025-12-04T15:00:00+08:00';r['model_frozen_at']='2025-10-01T00:00:00+08:00';r['inputs_known_at']='2025-12-04T15:00:00+08:00'
 assert not validate_metadata(r,'2026-11-17','protocol','2026-11-17T00:00:00+08:00')[0]
 r=record();assert validate_metadata(r,'2026-11-17','protocol','2026-11-17T00:00:00+08:00')[0]
