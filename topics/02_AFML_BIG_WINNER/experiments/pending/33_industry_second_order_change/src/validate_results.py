"""Validate present receipts, numerical comparisons, and completion artifacts."""
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from price_experiment import EP,digest


def main():
    checks=[];verified={}
    for round_id in ['r01','r02','r03','r04','r05']:
        receipt=json.loads((EP/f'outputs/{round_id}/receipt.json').read_text())
        inputs=receipt.get('inputs',receipt.get('sources',{}))
        for name,expected in inputs.items():
            path=Path(name)
            actual=verified.setdefault(name,digest(path))
            assert actual==expected,(round_id,name)
        checks.append({'check':round_id+'_input_hashes','count':len(inputs),'status':'PASS'})
    receipt=json.loads((EP/'outputs/final/global_receipt.json').read_text())
    for name,expected in receipt['inputs'].items():assert digest(Path(name))==expected,name
    checks.append({'check':'global_input_hashes','status':'PASS'})
    f=pd.read_csv(EP/'outputs/final/global_date_pairs.csv',parse_dates=['date'])
    c=f[f.complete];m=c.groupby(c.date.dt.to_period('M')).delta.mean()
    summary=json.loads((EP/'outputs/final/global_summary.json').read_text())
    assert np.isclose(m.mean(),summary['delta'])
    assert len(c)==summary['complete_dates']
    s=pd.read_csv(EP/'outputs/final/global_selected.csv.gz',parse_dates=['date'],low_memory=False)
    for date,g in s.groupby('date'):
        a=g[g.arm.eq('policy')];b=g[g.arm.eq('global_velocity')]
        assert len(a)==len(b) and 0<len(a)<=10
        r=f[f.date.eq(date)].iloc[0]
        if r.complete:
            assert np.isclose(a.excess126.mean()-b.excess126.mean(),r.delta)
    checks.append({'check':'global_pairs_recomputed_from_selected_rows','dates':int(s.date.nunique()),'status':'PASS'})
    cards=json.loads((EP/'outputs/final/candidate_cards.json').read_text())
    assert len(cards)==10
    assert all(c['date']=='2026-10-16' and c['outcome_status']=='CENSORED' for c in cards)
    assert all(c['hypothesis'] and c['competing_explanation'] and c['next_research'] and c['invalidation'] for c in cards)
    checks.append({'check':'candidate_contract_and_no_fabricated_outcomes','count':len(cards),'status':'PASS'})
    test=subprocess.run([sys.executable,'-m','pytest','-q',str(EP/'tests')],capture_output=True,text=True)
    assert test.returncode==0,test.stdout+test.stderr
    checks.append({'check':'temporal_contract_tests','status':'PASS','output':test.stdout.strip()})
    for round_id in ['r00','r01','r02','r03','r04','r05']:
        assert (EP/f'rounds/{round_id}_plan.md').exists()
        assert (EP/f'rounds/{round_id}_reflection.md').exists()
    checks.append({'check':'all_six_round_plans_and_reflections','status':'PASS'})
    for name in ['GOAL.md','README.md','reports/stage_report.md','reports/candidate_cards.md']:
        path=EP/name
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if not link.startswith(('http','#')):assert (path.parent/link.split('#')[0]).exists(),(name,link)
    checks.append({'check':'markdown_local_links','status':'PASS'})
    output={'status':'PASS','checks':checks,'unique_hashed_inputs':len(verified),
        'limits':['No independent forward performance verified','No vendor PIT certification',
                  'Bootstrap intervals do not correct adaptive-search bias','Missing-path sensitivity remains material']}
    (EP/'reports/validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    env={'python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','pyarrow','pytest','tabulate']}}
    (EP/'outputs/final/environment.json').write_text(json.dumps(env,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
