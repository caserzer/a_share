"""Seal R00 artifacts and their directly recorded inputs; not method acceptance."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from audit_local_inputs import EP,sha

RECEIPTS=[
    'outputs/r00_coverage/receipt.json',
    'outputs/r00_price_process_v03/receipt.json',
    'outputs/r00_evaluation_support/receipt.json',
    'outputs/r00_v03_support/receipt.json',
    'outputs/r00_v03_support/capacity_oracle_receipt.json',
    'outputs/r00_metric_denominators/receipt.json',
]


def main(mode):
    folder=EP/'protocols/r00_v1';seal=folder/'seal.json';cache={}
    def digest(p):
        p=Path(p).resolve()
        if str(p) not in cache:cache[str(p)]=sha(p)
        return cache[str(p)]
    if mode=='verify':
        record=json.loads(seal.read_text())
        for filename,expected in record['files'].items():
            if digest(filename)!=expected:raise ValueError('seal drift: '+filename)
        print(json.dumps(dict(status='SEAL_VERIFIED',files=len(record['files']),scope=record['scope'])))
        return
    if mode!='create':raise ValueError('use create or verify')
    if seal.exists():raise FileExistsError('sealed v1 already exists; verify or create an explicit new version')
    folder.mkdir(parents=True,exist_ok=True)
    # Recheck the actual receipt inputs, not merely receipt status strings.
    input_checks=0
    for rel in RECEIPTS:
        path=EP/rel;r=json.loads(path.read_text());digest(path)
        for filename,expected in r.get('inputs',{}).items():
            if digest(filename)!=expected:raise ValueError('receipt input drift: '+filename)
            input_checks+=1
        for filename,expected in r.get('artifacts',{}).items():
            if digest(path.parent/filename)!=expected:raise ValueError('receipt artifact drift: '+filename)
        if 'output_sha256' in r:
            candidates={'r00_evaluation_support':'all_catalog_dates.parquet','r00_metric_denominators':'full_process_registry.parquet'}
            name=candidates.get(path.parent.name)
            if name and digest(path.parent/name)!=r['output_sha256']:raise ValueError('single output drift')
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(EP/'tests'),'-v'],capture_output=True,text=True)
    (folder/'tests.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise RuntimeError('tests failed; not sealed')
    shutil.copyfile(EP/'R00_PROTOCOL.md',folder/'protocol.md')
    for sub in ['configs','rounds','reports','tests']:
        for p in (EP/sub).glob('*'):
            if p.is_file():digest(p)
    for p in (EP/'src').glob('*.py'):digest(p)
    # Evidence artifacts are captured even when a receipt lacks an artifact map.
    for name in ['r00_coverage','r00_price_process_v03','r00_evaluation_support','r00_v03_support','r00_metric_denominators']:
        for p in (EP/'outputs'/name).rglob('*'):
            if p.is_file():digest(p)
    for p in [EP/'GOAL.md',EP/'R00_PROTOCOL.md',folder/'protocol.md',folder/'tests.log']:digest(p)
    record=dict(version='EP34-R00-v1',date='2026-11-11',status='FROZEN_EVALUATION_PROTOCOL',
                scope='Price-process and evaluation protocol only; not a validated method or frozen operational pool',
                direct_receipt_input_checks=input_checks,files=dict(sorted(cache.items())),
                limitations=['Direct reusable inputs checked; original individual-stock data chain not reaudited',
                             'No candidate signals evaluated; missed-process cases remain required after baseline',
                             'Concurrent pool capacity user preference is still pending; register before replay'])
    seal.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=record['status'],files=len(cache),direct_receipt_input_checks=input_checks)))


if __name__=='__main__':main(sys.argv[1])
