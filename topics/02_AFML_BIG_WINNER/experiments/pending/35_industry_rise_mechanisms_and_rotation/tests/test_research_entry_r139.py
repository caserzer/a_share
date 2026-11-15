import json
import hashlib
import pytest
from research_entry_r139 import load,ENTRY

def setup(tmp_path):
    out=tmp_path/'outputs';out.mkdir();artifact=out/'artifact';artifact.write_text('checked data');proof=out/'proof.json';proof.write_text('{"status":"PASS"}')
    def item(p):return dict(path=str(p.relative_to(tmp_path)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    manifest=out/'release.json';data=dict(quality='Historical-proxy',overall_status='active_not_complete',routes={'monitor':dict(**item(artifact),verification=item(proof))})
    def save():
        manifest.write_text(json.dumps(data));(out/'current_sources.json').write_text(json.dumps({'selected':{ENTRY:item(manifest)}}))
    save();return artifact,proof,data,save

def test_resolves_verified_artifact(tmp_path):
    setup(tmp_path);assert load(tmp_path,'monitor')['path']=='outputs/artifact'

def test_rejects_changed_artifact(tmp_path):
    artifact,_,_,_=setup(tmp_path);artifact.write_text('changed')
    with pytest.raises(ValueError,match='missing or changed'):load(tmp_path)

def test_rejects_missing_verification(tmp_path):
    _,proof,_,_=setup(tmp_path);proof.unlink()
    with pytest.raises(ValueError,match='missing or changed'):load(tmp_path)

def test_rejects_failed_verification_even_with_updated_hash(tmp_path):
    _,proof,data,save=setup(tmp_path);proof.write_text('{"status":"FAIL"}');data['routes']['monitor']['verification']['sha256']=hashlib.sha256(proof.read_bytes()).hexdigest();save()
    with pytest.raises(ValueError,match='not passed'):load(tmp_path)

def test_no_silent_legacy_fallback(tmp_path):
    setup(tmp_path)
    with pytest.raises(KeyError,match='not adopted'):load(tmp_path,'old_branch')

def test_explicit_historical_manifest_preserves_current_pointer(tmp_path):
    setup(tmp_path)
    current=tmp_path/'outputs/current_sources.json';pointer=json.loads(current.read_text())['selected'][ENTRY]
    original=current.read_bytes();assert load(tmp_path,'monitor',manifest_item=pointer)['path']=='outputs/artifact'
    assert current.read_bytes()==original

def test_rejects_manifest_outside_research_root(tmp_path):
    setup(tmp_path)
    with pytest.raises(ValueError,match='outside root'):
        load(tmp_path,manifest_item=dict(path='../outside-release.json',sha256='not-used'))
