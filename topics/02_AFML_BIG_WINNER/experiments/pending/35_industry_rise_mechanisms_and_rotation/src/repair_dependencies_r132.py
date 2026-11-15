"""Bounded literal/provenance inventory, not a dynamic dependency graph."""
from common import *


def references(obj,targets,pointer=''):
    rows=[]
    if isinstance(obj,dict):
        for key,value in obj.items():
            child=pointer+'/'+str(key).replace('~','~0').replace('/','~1')
            if key in targets:rows.append(dict(pointer=child,location='key',target=targets[key]))
            rows+=references(value,targets,child)
    elif isinstance(obj,list):
        for i,value in enumerate(obj):rows+=references(value,targets,pointer+'/'+str(i))
    elif isinstance(obj,str) and obj in targets:rows.append(dict(pointer=pointer,location='value',target=targets[obj]))
    return rows


def run():
    out=ROOT/'outputs/r132';out.mkdir(exist_ok=True)
    seeds={'old_monthly':ROOT/'data/monthly_panel.parquet','old_daily':CACHE/'forecast_v5/daily_industries.parquet'};targets={}
    for name,p in seeds.items():
        targets[str(p)]=name+':path';targets[sha(p)]=name+':sha256'
    targets['data/monthly_panel.parquet']='old_monthly:relative_path';targets['forecast_v5/daily_industries.parquet']='old_daily:relative_path'
    source=[];files=sorted((ROOT/'src').glob('*.py'))
    for p in files:
        for n,line in enumerate(p.read_text().splitlines(),1):
            if 'monthly_panel.parquet' in line or 'daily_industries.parquet' in line:
                source.append(dict(path=str(p.relative_to(ROOT)),line=n,text=line.strip(),sha256=sha(p),classification='verifier' if p.name.startswith('verify_') else 'registry' if p.name.startswith('reconcile_') else 'candidate_reference'))
    provenance=[];scanned=[];errors=[]
    for p in sorted((ROOT/'outputs').rglob('*.json')):
        if out in p.parents or p.name=='progress_manifest.json':continue
        scanned.append(str(p.relative_to(ROOT)))
        try:obj=json.loads(p.read_text())
        except (ValueError,UnicodeError) as error:errors.append(dict(path=str(p.relative_to(ROOT)),error=str(error)));continue
        hits=references(obj,targets)
        if hits:provenance.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),matches=hits))
    verified=[]
    for script,receipt in [('portfolio_r04.py','outputs/r04/receipt.json'),('market_controls_r54.py','outputs/r54/receipt.json')]:
        p=ROOT/'src'/script;rp=ROOT/receipt
        assert rp.exists();evidence=references(json.loads(rp.read_text()),targets);assert any(x['target']=='old_daily:sha256' for x in evidence) and any(x['target']=='old_monthly:sha256' for x in evidence)
        verified.append(dict(script=str(p.relative_to(ROOT)),script_sha256=sha(p),receipt=receipt,receipt_exists=rp.exists(),receipt_sha256=sha(rp),exact_old_source_evidence=evidence,role='upstream-read consumer; original artifacts retained',status='requires_input_and_output_impact_review',scope='synthetic portfolio paths' if 'portfolio' in script else 'market beta/residual volatility controls'))
    js(out/'dependency_inventory.json',dict(scope='EP35 src top-level Python literals; all prior outputs JSON except progress_manifest; excludes external/indirect/dynamic path resolution',seeds={k:dict(path=str(p),sha256=sha(p)) for k,p in seeds.items()},python_files=len(files),source_reference_files=len({x['path'] for x in source}),source_lines=source,prior_json_files=len(scanned),json_files=scanned,provenance_reference_files=len(provenance),provenance=provenance,parse_errors=errors,reviewed_consumers=verified,conclusion='References include frozen audits and comparison baselines; not all hits are active consumers or require rerunning. No whole-dependency completion claim.'))
    print('DEPENDENCIES',len(files),len({x['path'] for x in source}),len(scanned),len(provenance),len(errors))

if __name__=='__main__':run()
