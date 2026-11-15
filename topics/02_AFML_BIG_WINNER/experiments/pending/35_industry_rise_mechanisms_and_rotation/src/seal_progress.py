"""Seal this progress snapshot without claiming completion or publishing private data."""
import platform
import subprocess
import pandas,sklearn,scipy
from common import *


def run():
    files=[]
    for folder in ['src','tests','protocols','reports','outputs']:
        for p in sorted((ROOT/folder).rglob('*')):
            if not p.is_file() or '__pycache__' in str(p) or p.name=='progress_manifest.json':continue
            files.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size))
    for name in ['GOAL.md','STATUS.md','README.md','RESEARCH_LOG.md','.gitignore']:
        p=ROOT/name;files.append(dict(path=name,sha256=sha(p),bytes=p.stat().st_size))
    referenced=json.loads((ROOT/'outputs/completion_audit.json').read_text())
    for item in referenced['items']:
        for evidence in item['evidence']:assert (ROOT/evidence).is_file(),evidence
    js(ROOT/'outputs/progress_manifest.json',dict(status='active_not_complete',as_of='2026-11-13',files=files,
        base_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_state='local EP35 additions identified by SHA256, not a published commit',
        runtime=dict(python=platform.python_version(),pandas=pandas.__version__,sklearn=sklearn.__version__,scipy=scipy.__version__),
        private_data='data/ is gitignored, file identities recorded in per-round receipts',external_publication=False))
    print('SEALED PROGRESS',len(files),'files; overall goal remains active')

if __name__=='__main__':run()
