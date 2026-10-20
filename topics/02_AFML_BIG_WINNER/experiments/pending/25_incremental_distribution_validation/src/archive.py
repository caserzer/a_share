"""Hash reviewable deliverables and explicitly local-only full distributions."""
import json
from core import *


def main():
    lock=json.loads((OUT/'preregistration.json').read_text())
    supporting=[p for folder in [EP/'src',EP/'tests'] for p in sorted(folder.glob('*.py')) if str(p.relative_to(EP)) not in lock['files']]
    write_json(OUT/'supporting_code_manifest.json',dict(scope='post-registration report, validation, archive and prospective utilities; core registered scoring/model code unchanged',files={str(p.relative_to(EP)):digest(p) for p in supporting}))
    files=[]
    for p in sorted(EP.rglob('*')):
        if not p.is_file() or p.name=='delivery_manifest.json' or any(s in p.parts for s in ['__pycache__','.pytest_cache']):continue
        local='local_cache' in p.parts
        files.append(dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p),storage='local_only_ignored' if local else 'reviewable_deliverable'))
    write_json(OUT/'delivery_manifest.json',dict(files=files,file_count=len(files),
        local_only_bytes=sum(r['bytes'] for r in files if r['storage']=='local_only_ignored'),
        reviewable_bytes=sum(r['bytes'] for r in files if r['storage']=='reviewable_deliverable'),
        github_commit_created=False,github_push_performed=False))
    print('delivery manifest',len(files),'files',flush=True)

if __name__=='__main__':main()
