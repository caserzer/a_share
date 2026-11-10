import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from forward_gate import validate,append,digest,REQUIRED


def setup(tmp_path):
    evidence=tmp_path/'evidence.json';evidence.write_text('{"fixture":true}')
    contract=dict(frozen_at='2026-11-08T09:00:00+08:00',maximum_recording_delay_days=1,score_cutoff=.11)
    contract['identity_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    snapshot=dict(decision_time='2026-11-09T15:00:00+08:00',contract_sha256=contract['identity_sha256'],
        latest_price_date='2026-11-09',latest_training_label_known_at='2026-09-30T15:00:00+08:00',
        evidence={k:dict(status='PASS',path=str(evidence),sha256=digest(evidence),known_at='2026-11-09T15:00:00+08:00') for k in REQUIRED},
        predictions=[dict(frequency='W',threshold=.15,benchmark='CSI_ALL',level='L3',era='SW2021',industry_code='TEST',risk_score=.12,diffusion_score=.15,market_return126=.05,selected=True)])
    return contract,snapshot


def test_valid_fixture_and_no_overwrite(tmp_path):
    c,s=setup(tmp_path);now='2026-11-09T16:00:00+08:00'
    assert validate(s,c,now)==[]
    cp=tmp_path/'contract.json';sp=tmp_path/'snapshot.json'
    cp.write_text(json.dumps(c));sp.write_text(json.dumps(s))
    result=append(sp,cp,tmp_path/'records',now)
    assert digest(result['path'])==result['sha256']
    with pytest.raises(FileExistsError):append(sp,cp,tmp_path/'records',now)


def test_stale_prices_and_unmatured_training_rejected(tmp_path):
    c,s=setup(tmp_path);s['latest_price_date']='2026-10-21';s['latest_training_label_known_at']='2026-10-01T00:00:00+08:00'
    errors=validate(s,c,'2026-11-09T16:00:00+08:00')
    assert 'STALE_OR_FUTURE_PRICE_DATE' in errors and 'TRAINING_LABEL_NOT_MATURE_BEFORE_QUARTER' in errors


def test_future_or_reconstructed_snapshots_rejected(tmp_path):
    c,s=setup(tmp_path)
    assert 'FUTURE_DECISION' in validate(s,c,'2026-11-08T16:00:00+08:00')
    assert 'LATE_RECONSTRUCTED_RECORD_NOT_PROSPECTIVE' in validate(s,c,'2026-11-12T16:00:00+08:00')
    s['evidence']['prices']['known_at']='2026-11-10T09:00:00+08:00'
    assert 'prices:NOT_AVAILABLE_AT_DECISION' in validate(s,c,'2026-11-09T16:00:00+08:00')


def test_tampering_outcomes_and_rule_mismatch_rejected(tmp_path):
    c,s=setup(tmp_path);c['score_cutoff']=.5
    errors=validate(s,c,'2026-11-09T16:00:00+08:00')
    assert 'CONTRACT_CONTENT_HASH_MISMATCH' in errors and 'SELECTION_RULE_MISMATCH' in errors
    c,s=setup(tmp_path);s['predictions'][0]['future_return']=.2
    assert 'FUTURE_OUTCOME_IN_PREDICTION_FILE' in validate(s,c,'2026-11-09T16:00:00+08:00')
    s['evidence']['prices']['sha256']='0'*64
    assert 'prices:EVIDENCE_MISSING_OR_HASH_MISMATCH' in validate(s,c,'2026-11-09T16:00:00+08:00')
