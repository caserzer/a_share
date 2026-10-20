"""Seal prospective protocol and hash publishable/local-only EP26 artifacts."""
from core import *


def main():
    reg=json.loads((OUT/'preregistration.json').read_text())
    assert all(digest(EP/k)==v for k,v in reg['files'].items())
    future=[EP/'validation_protocol.md',EP/'src/prospective.py',EP/'tests/test_prospective.py']
    prospective=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),scope='before any actual prospective forecast; supplementary to historical registration',
        files={str(p.relative_to(EP)):digest(p) for p in future},historical_preregistration_sha256=digest(OUT/'preregistration.json'))
    lock=OUT/'prospective_protocol_lock.json'
    if lock.exists():
        old=json.loads(lock.read_text());assert all(digest(EP/k)==v for k,v in old['files'].items())
    else:write_json(lock,prospective)
    extra=[p for folder in [EP/'src',EP/'tests'] for p in sorted(folder.glob('*.py')) if str(p.relative_to(EP)) not in reg['files']]
    write_json(OUT/'supporting_code_manifest.json',dict(scope='post-registration reporting/attribution/validation/prospective tools; registered candidate/model/scoring/filter code unchanged',files={str(p.relative_to(EP)):digest(p) for p in extra}))
    files=[]
    for p in sorted(EP.rglob('*')):
        if not p.is_file() or p.name=='delivery_manifest.json' or any(s in p.parts for s in ['__pycache__','.pytest_cache']):continue
        files.append(dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p),storage='local_only_ignored' if 'local_cache' in p.parts else 'github_deliverable'))
    write_json(OUT/'delivery_manifest.json',dict(files=files,file_count=len(files),local_only_bytes=sum(r['bytes'] for r in files if r['storage']=='local_only_ignored'),github_deliverable_bytes=sum(r['bytes'] for r in files if r['storage']=='github_deliverable'),
        github_repository='caserzer/a_share',publication='verify remote HEAD after exact-scope commit/push; manifest alone is not publication proof'))
    print('EP26 archive manifest',len(files),'files',flush=True)

if __name__=='__main__':main()
