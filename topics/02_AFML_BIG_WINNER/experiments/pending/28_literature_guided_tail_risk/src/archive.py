"""Publishable/local boundaries and future-protocol seal, with immutable history."""
from core import *
from run import freeze


def main():
    freeze();assert json.loads((EP/'outputs/audits/validation.json').read_text())['passed']
    manifest=EP/'outputs/manifests'
    registration=json.loads((manifest/'preregistration.json').read_text())
    supporting=[p for p in (EP/'src').glob('*.py') if str(p.relative_to(EP)) not in registration['files']]
    supporting+= [p for p in (EP/'tests').glob('*.py') if str(p.relative_to(EP)) not in registration['files']]
    write_json(manifest/'supporting_code.json',dict(timing='added after historical registration, before prospective predictions',
        files={str(p.relative_to(EP)):digest(p) for p in sorted(supporting)}))
    paths=[EP/'validation_protocol.md',EP/'configs/preregistered_experiments.yaml']+sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))
    value=dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),first_possible_origin='2026-10-30',
        files={str(p.relative_to(EP)):digest(p) for p in paths},EP27_lock_sha256=digest(EP27/'outputs/prospective_protocol_lock.json'),
        actual_prospective_predictions_created=False)
    lock=manifest/'prospective_lock.json'
    if lock.exists():
        old=json.loads(lock.read_text());assert old['files']==value['files'],'Do not overwrite a prior future-protocol lock'
    else:write_json(lock,value)
    rows=[]
    for p in sorted(CACHE.rglob('*')):
        if p.is_file():rows.append(dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p)))
    pd.DataFrame(rows).to_csv(manifest/'local_cache_manifest.csv',index=False)
    pub=[]
    for p in sorted(EP.rglob('*')):
        if not p.is_file() or CACHE in p.parents or '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
        if p==manifest/'delivery_manifest.json':continue
        pub.append(dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p)))
    write_json(manifest/'delivery_manifest.json',dict(files=pub,public_files=len(pub),local_cache_files=len(rows),
        local_cache_bytes=sum(r['bytes'] for r in rows),original_EP24_to_EP27_preserved=True,
        cache_publication='local only; not included in GitHub',independent_confirmation=False))
    print(json.dumps(dict(public_files=len(pub),local_cache_files=len(rows),local_cache_bytes=sum(r['bytes'] for r in rows))),flush=True)


if __name__=='__main__':main()
