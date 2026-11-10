"""Evidence admission for a future append-only research prediction snapshot.

This checks metadata and hashes; it does not certify source truth or generate
predictions. No current EP32 input release passes the required PIT/data checks.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import math
import pandas as pd

REQUIRED = ['prices', 'membership', 'market_index', 'model_training', 'feature_availability']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(snapshot, contract, now):
    reasons = []
    identity = hashlib.sha256(json.dumps({k:v for k,v in contract.items() if k!='identity_sha256'},
        sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if identity != contract.get('identity_sha256'):
        reasons.append('CONTRACT_CONTENT_HASH_MISMATCH')
    decision = pd.Timestamp(snapshot['decision_time'])
    now = pd.Timestamp(now)
    frozen = pd.Timestamp(contract['frozen_at'])
    if decision.tzinfo is None or now.tzinfo is None:
        return ['TIMEZONE_REQUIRED']
    if decision < frozen:
        reasons.append('PREDATES_FREEZE')
    if decision > now:
        reasons.append('FUTURE_DECISION')
    if now - decision > pd.Timedelta(days=contract['maximum_recording_delay_days']):
        reasons.append('LATE_RECONSTRUCTED_RECORD_NOT_PROSPECTIVE')
    if snapshot.get('contract_sha256') != contract['identity_sha256']:
        reasons.append('CONTRACT_ID_MISMATCH')
    for name in REQUIRED:
        receipt = snapshot.get('evidence', {}).get(name, {})
        if receipt.get('status') != 'PASS':
            reasons.append(name + ':NOT_CERTIFIED')
        path = Path(receipt.get('path', '/nonexistent'))
        if not path.is_file() or digest(path) != receipt.get('sha256'):
            reasons.append(name + ':EVIDENCE_MISSING_OR_HASH_MISMATCH')
        known_at = pd.Timestamp(receipt.get('known_at'))
        if pd.isna(known_at) or known_at.tzinfo is None or known_at > decision:
            reasons.append(name + ':NOT_AVAILABLE_AT_DECISION')
    latest = pd.Timestamp(snapshot.get('latest_price_date'))
    if pd.isna(latest) or latest.date() != decision.date():
        reasons.append('STALE_OR_FUTURE_PRICE_DATE')
    training = pd.Timestamp(snapshot.get('latest_training_label_known_at'))
    quarter_start = pd.Timestamp(year=decision.year, month=((decision.month-1)//3)*3+1, day=1, tz=decision.tz)
    if pd.isna(training) or training.tzinfo is None or training >= quarter_start:
        reasons.append('TRAINING_LABEL_NOT_MATURE_BEFORE_QUARTER')
    predictions = snapshot.get('predictions', [])
    keys = [(p.get('frequency'),p.get('threshold'),p.get('benchmark'),p.get('level'),p.get('era'),p.get('industry_code')) for p in predictions]
    if not predictions or len(keys) != len(set(keys)):
        reasons.append('EMPTY_OR_DUPLICATE_PREDICTIONS')
    if any(any(k in p for k in ['future_return','peak_date','y','label']) for p in predictions):
        reasons.append('FUTURE_OUTCOME_IN_PREDICTION_FILE')
    for row in predictions:
        risk, diffusion, market = row.get('risk_score'),row.get('diffusion_score'),row.get('market_return126')
        if risk is None or diffusion is None or market is None or not all(math.isfinite(x) for x in [risk,diffusion,market]) or not (0 <= risk <= 1 and 0 <= diffusion <= 1):
            reasons.append('INVALID_SCORE');continue
        expected = risk >= contract['score_cutoff'] and diffusion >= contract['score_cutoff'] and market > 0
        if row.get('selected') != expected:
            reasons.append('SELECTION_RULE_MISMATCH')
    return sorted(set(reasons))


def append(snapshot_path, contract_path, destination, now):
    snapshot = json.loads(Path(snapshot_path).read_text())
    contract = json.loads(Path(contract_path).read_text())
    reasons = validate(snapshot, contract, now)
    if reasons:
        raise ValueError(json.dumps(reasons))
    raw = (json.dumps(snapshot,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n').encode()
    checksum = hashlib.sha256(raw).hexdigest()
    destination = Path(destination); destination.mkdir(parents=True,exist_ok=True)
    name = pd.Timestamp(snapshot['decision_time']).strftime('%Y%m%dT%H%M%S%z')
    # One file per decision timestamp: no silent revisions to an existing record.
    path = destination / (name+'.json')
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw)
    return dict(path=str(path),sha256=checksum)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('snapshot');parser.add_argument('contract');parser.add_argument('destination')
    args=parser.parse_args()
    print(json.dumps(append(args.snapshot,args.contract,args.destination,pd.Timestamp.now(tz='Asia/Shanghai')),ensure_ascii=False))
