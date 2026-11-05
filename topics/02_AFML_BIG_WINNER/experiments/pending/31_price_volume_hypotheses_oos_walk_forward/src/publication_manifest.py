"""Hash the reviewable small artifacts; external payloads are indexed separately."""
from common import EP, OUT, sha, utc_now, write_json


def main():
    target=OUT/'manifests/publication.json'
    extensions={'.py','.yaml','.json','.md','.csv','.svg','.png','.txt'}
    records=[]
    for p in sorted(EP.rglob('*')):
        if not p.is_file() or p==target or '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
        if p.suffix not in extensions and p.name!='.gitignore':continue
        if p.stat().st_size>10*1024*1024:raise RuntimeError('oversize repository artifact: '+str(p))
        records.append(dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=sha(p)))
    write_json(target,dict(status='PASS',generated_at=utc_now(),files=records,count=len(records),total_bytes=sum(r['bytes'] for r in records),
               private_large_data_included=False,private_models_included=False,network_publication_performed=False,
               self_excluded_from_hash_manifest=True))
    print('publication manifest',len(records),'files',sum(r['bytes'] for r in records),'bytes')


if __name__=='__main__':main()
