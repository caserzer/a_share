from pathlib import Path
import json,hashlib,re
r=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation');o=r/'outputs/r230'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((o/'requirements_audit.json').read_text());b=json.loads((r/'outputs/r183/requirements_audit.json').read_text());assert {x['id'] for x in a['items']}=={x['id'] for x in b['items']};assert all(not x['completion_proven'] for x in a['items']);assert set(a['explicit_target_crosswalk']['three_tasks'])=={'onset','relative_return','reversal'};assert len(a['explicit_target_crosswalk']['four_deliverables'])==4
checks=0
for x in a['items']:
 for item in x['evidence']+x['regime_evidence']:
  assert sha(r/item['path'])==item['sha256'];checks+=1
f=json.loads((o/'family_catalog.json').read_text());reg=json.loads((r/'outputs/r195/experiment_registry.json').read_text());assert {x['family'] for x in f['families']}=={x['family'] for x in reg['families']}
for x in f['families']:
 assert not x['adoption']
 for e in x['evidence']:assert sha(r/e['path'])==e['sha256'];checks+=1
report=r/'reports/r230_complete_research_crosswalk.md';links=re.findall(r'\]\(([^)]+)\)',report.read_text());assert all((report.parent/link).is_file() for link in links)
cur=json.loads((r/'outputs/current_sources.json').read_text());assert cur['selected']['corrected_research_entry']['path']=='outputs/r183/release.json';assert (r/'README.md').read_text().startswith('# 当前研究入口：R230')
(o/'independent_verification.json').write_text(json.dumps({'status':'PASS','requirements':len(a['items']),'families':len(f['families']),'linked_evidence_hash_checks':checks,'report_links':len(links),'default_release':'R183','whole_goal_complete':False,'scope':'Exact requirement/family sets, source hashes, explicit task/deliverable maps, report links and unchanged release pointer'},indent=2)+'\n')
files=[report,r/'protocols/r230.json']+list(o.glob('*'))+list((r/'src').glob('*r230.py'));(o/'snapshot_manifest.json').write_text(json.dumps({str(p.relative_to(r)):sha(p) for p in files if p.is_file() and p.name!='snapshot_manifest.json'},indent=2)+'\n');print('PASS',checks,'linked evidence',len(links),'links')
