"""Validate bounded inventory paths, hashes, pointers and reviewed receipts."""
from common import *

def run():
    out=ROOT/'outputs/r132';a=json.loads((out/'dependency_inventory.json').read_text());targets={}
    for name,item in a['seeds'].items():
        assert sha(item['path'])==item['sha256'];targets[item['path']]=name+':path';targets[item['sha256']]=name+':sha256'
    targets['data/monthly_panel.parquet']='old_monthly:relative_path';targets['forecast_v5/daily_industries.parquet']='old_daily:relative_path'
    expected=[];files=sorted((ROOT/'src').glob('*.py'));assert len(files)==a['python_files']
    for p in files:
        for n,line in enumerate(p.read_text().splitlines(),1):
            if 'monthly_panel.parquet' in line or 'daily_industries.parquet' in line:expected.append((str(p.relative_to(ROOT)),n,line.strip()))
    assert expected==[(x['path'],x['line'],x['text']) for x in a['source_lines']]
    for x in a['source_lines']:assert sha(ROOT/x['path'])==x['sha256']
    paths=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'outputs').rglob('*.json') if out not in p.parents and p.name!='progress_manifest.json');assert paths==a['json_files'];assert not a['parse_errors']
    actual={x['path']:x for x in a['provenance']};found=0
    for path in paths:
        obj=json.loads((ROOT/path).read_text());stack=[('',obj)];hits=[]
        while stack:
            pointer,value=stack.pop()
            if isinstance(value,dict):
                for k,v in value.items():
                    child=pointer+'/'+k.replace('~','~0').replace('/','~1')
                    if k in targets:hits.append((child,'key',targets[k]))
                    stack.append((child,v))
            elif isinstance(value,list):stack.extend((pointer+'/'+str(i),v) for i,v in enumerate(value))
            elif isinstance(value,str) and value in targets:hits.append((pointer,'value',targets[value]))
        if hits:
            found+=1;rec=actual[path];assert sha(ROOT/path)==rec['sha256'];assert sorted(hits)==sorted((x['pointer'],x['location'],x['target']) for x in rec['matches'])
        else:assert path not in actual
    assert found==len(actual)==a['provenance_reference_files']
    for x in a['reviewed_consumers']:
        assert sha(ROOT/x['script'])==x['script_sha256'] and sha(ROOT/x['receipt'])==x['receipt_sha256']
        assert {y['target'] for y in x['exact_old_source_evidence']} >= {'old_daily:sha256','old_monthly:sha256'}
    js(out/'dependency_verification.json',dict(status='PASS',source_reference_files=a['source_reference_files'],provenance_reference_files=found,reviewed_consumers=len(a['reviewed_consumers']),limitation='Bounded literal and retained provenance evidence, not runtime/global completeness'))
    print('PASS DEPENDENCIES',a['source_reference_files'],found)

if __name__=='__main__':run()
