"""Hash-checked local corrected research entry; no implicit legacy fallback."""
import argparse
from common import *
ENTRY='corrected_research_entry'

def checked(root,item):
    path=(root/item['path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('research path outside root')
    if not path.is_file() or sha(path)!=item['sha256']:raise ValueError('research artifact missing or changed: '+item['path'])
    return path

def load(root=ROOT,key=None,manifest_item=None):
    root=Path(root);current=json.loads((root/'outputs/current_sources.json').read_text());pointer=current['selected'][ENTRY] if manifest_item is None else manifest_item;manifest_path=checked(root,pointer);manifest=json.loads(manifest_path.read_text())
    if manifest['quality']!='Historical-proxy' or manifest['overall_status']!='active_not_complete':raise ValueError('unexpected research boundary')
    for name,item in manifest['routes'].items():
        checked(root,item);proof=checked(root,item['verification'])
        if json.loads(proof.read_text()).get('status')!='PASS':raise ValueError('verification not passed: '+name)
    if key is not None:
        if key not in manifest['routes']:raise KeyError('not adopted in corrected entry: '+key)
        return dict(manifest['routes'][key],quality=manifest['quality'],overall_status=manifest['overall_status'])
    return manifest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--key');args=parser.parse_args();m=load(key=args.key)
    if args.key:print(json.dumps(m,ensure_ascii=False,indent=2))
    else:print(json.dumps(dict(revision=m['revision'],quality=m['quality'],overall_status=m['overall_status'],dates=m['monitor_dates'],verified_evidence_routes=len(m['routes']),unreviewed_legacy_routes=len(m['unreviewed_legacy_routes']),monitor=m['routes']['integrated_historical_task_evidence']['path'],requirements_audit=m['routes'].get('current_requirements_audit',{}).get('path','historical entry: see original audit'),next=m['next'],research_extensions=m.get('research_extensions',{})),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
