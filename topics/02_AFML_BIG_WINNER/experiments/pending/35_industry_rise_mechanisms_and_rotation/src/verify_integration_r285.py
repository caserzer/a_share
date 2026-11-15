import json,hashlib,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    current=read('outputs/current_sources.json');pointer=current['selected']['corrected_research_entry']
    assert pointer['path']=='outputs/r285/release.json' and digest(ROOT/pointer['path'])==pointer['sha256']
    new=read(pointer['path']);old=read('outputs/r279/release.json');checks=0
    for key,value in old['routes'].items():
        assert new['routes']['requirements_audit_r279' if key=='current_requirements_audit' else key]==value
    for item in new['routes'].values():
        for r in (item,item['verification']):
            p=(ROOT/r['path']).resolve();assert p.is_relative_to(ROOT) and digest(p)==r['sha256'];checks+=1
        assert read(item['verification']['path'])['status']=='PASS'
    a=read('outputs/r285/requirements_audit.json');b=read('outputs/r279/requirements_audit.json')
    assert a['explicit_target_crosswalk']==b['explicit_target_crosswalk']
    assert [i['id'] for i in a['items']]==[i['id'] for i in b['items']] and len(a['items'])==16
    assert all(not i['completion_proven'] for i in a['items']) and not a['full_completion_proven']
    assert '尚待修正正文逐条核验' not in json.dumps(a,ensure_ascii=False)
    assert new['monitor_dates']==old['monitor_dates'] and new['overall_status']=='active_not_complete'
    report=ROOT/'reports/r285_battery_validation_delivery.md';links=re.findall(r'\]\((r28\d[^)]+\.md)\)',report.read_text())
    assert len(links)==5 and all((report.parent/x).is_file() for x in links)
    result=dict(status='PASS',direct_hash_checks=checks,old_routes_preserved=len(old['routes']),new_routes=len(new['routes']),report_links=5,requirements_preserved=16,full_goal_complete=False,verifier_sha256=digest(Path(__file__)))
    (ROOT/'outputs/r285/independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result)
if __name__=='__main__':run()
