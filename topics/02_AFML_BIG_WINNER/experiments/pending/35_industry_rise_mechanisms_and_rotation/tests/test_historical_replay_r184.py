import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from historical_replay import checked_manifest,ROLES


def manifest(tmp_path):
    f=tmp_path/'source';f.write_bytes(b'fixture');p=tmp_path/'sources.json'
    m=dict(schema='ep35_repaired_historical_v1',quality='Historical-proxy',max_asof='2026-10-21',sources={k:dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for k in ROLES})
    p.write_text(json.dumps(m));return p,f,m


def test_frozen_hash_and_cutoff_contract(tmp_path):
    p,f,m=manifest(tmp_path)
    assert checked_manifest(p,'2026-10-21')[0]==m
    with pytest.raises(ValueError,match='source maximum'):checked_manifest(p,'2026-10-22')
    with pytest.raises(ValueError,match='explicit date'):checked_manifest(p,'2026-10-21T01:00:00')
    f.write_bytes(b'changed')
    with pytest.raises(ValueError,match='source hash mismatch'):checked_manifest(p,'2026-10-21')


def test_role_and_quality_cannot_be_silently_changed(tmp_path):
    p,f,m=manifest(tmp_path);m['quality']='strict_PIT';p.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='unsupported'):checked_manifest(p,'2026-10-21')
    m['quality']='Historical-proxy';del m['sources']['assignments'];p.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='roles mismatch'):checked_manifest(p,'2026-10-21')
