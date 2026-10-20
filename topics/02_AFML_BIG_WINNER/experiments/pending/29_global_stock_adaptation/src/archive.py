"""Byte inventories and a separate immutable prospective implementation lock."""
from common import *
from global_model import freeze


def main():
    freeze()
    assert json.loads((AUDIT/'delivery_check.json').read_text())['passed']
    paths=sorted(p for p in CACHE.rglob('*') if p.is_file())
    pd.DataFrame([dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p),
        storage='local_ignored_not_on_GitHub') for p in paths]).to_csv(MANIFEST/'local_cache_manifest.csv',index=False)
    lockpath=MANIFEST/'prospective_lock.json'
    if lockpath.exists():
        lock=json.loads(lockpath.read_text())
        for p,h in lock['files'].items():assert digest(EP/p)==h,p
    else:
        locked=['validation_protocol.md','configs/preregistration.yaml','configs/target_cohort.yaml',
            'outputs/manifests/preregistration.json','outputs/manifests/correctness_amendments.json']
        locked+=['src/'+s+'.py' for s in ['forward','common','global_model','issuer_adaptation','peer_prior','local_baseline','hierarchical_model','diagnostics']]
        locked+=['outputs/local_cache/real_'+f+'_all.parquet' for f in ['M_R','L2']]
        locked+=['../28_literature_guided_tail_risk/outputs/manifests/prospective_lock.json']
        write_json(lockpath,dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),first_forecast_not_yet_created=True,
            historical_research_not_independent_confirmation=True,files={p:digest(EP/p) for p in locked}))
    excluded={'outputs/manifests/public_manifest.csv'}
    public=sorted(p for p in EP.rglob('*') if p.is_file() and 'local_cache' not in p.parts
        and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts and str(p.relative_to(EP)) not in excluded)
    pd.DataFrame([dict(path=str(p.relative_to(EP)),bytes=p.stat().st_size,sha256=digest(p)) for p in public]).to_csv(MANIFEST/'public_manifest.csv',index=False)
    print('Archived',len(public),'public files and',len(paths),'local cache files; prior lock preserved')


if __name__=='__main__':main()
