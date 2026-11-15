import json,hashlib,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    current=read('outputs/current_sources.json');pointer=current['selected']['corrected_research_entry']
    assert pointer['path']=='outputs/r298/release.json' and digest(ROOT/pointer['path'])==pointer['sha256']
    new=read(pointer['path']);old=read('outputs/r294/release.json');checks=0
    for key,value in old['routes'].items():
        assert new['routes']['requirements_audit_r294' if key=='current_requirements_audit' else key]==value
    for item in new['routes'].values():
        for r in (item,item['verification']):
            p=(ROOT/r['path']).resolve();assert p.is_relative_to(ROOT) and digest(p)==r['sha256'];checks+=1
        assert read(item['verification']['path'])['status']=='PASS'
    a=read('outputs/r298/requirements_audit.json');b=read('outputs/r294/requirements_audit.json')
    assert a['explicit_target_crosswalk']==b['explicit_target_crosswalk']
    assert [i['id'] for i in a['items']]==[i['id'] for i in b['items']] and len(a['items'])==16
    assert all(not i['completion_proven'] for i in a['items']) and not a['full_completion_proven']
    assert read('outputs/r298/remaining_work.json')['next_local']['task']==read('protocols/r298.json')['next']==new['next']
    assert new['monitor_dates']==old['monitor_dates'] and new['overall_status']=='active_not_complete'
    report=ROOT/'reports/r298_calibration_delivery.md';links=re.findall(r'\]\((r29[5-7][^)]+\.md)\)',report.read_text())
    assert len(links)==3 and all((report.parent/x).is_file() for x in links)
    contract=read('outputs/r298/probability_use_contract.json')
    for item in contract['archive_audit']:assert digest(ROOT/item['path'])==item['sha256']
    assert contract['adoption'] is False and contract['future_outcomes_allowed_in_reader'] is False
    result=dict(status='PASS',direct_hash_checks=checks,old_routes_preserved=len(old['routes']),new_routes=len(new['routes']),report_links=3,requirements_preserved=16,full_goal_complete=False,verifier_sha256=digest(Path(__file__)))
    (ROOT/'outputs/r298/independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result)
if __name__=='__main__':run()
