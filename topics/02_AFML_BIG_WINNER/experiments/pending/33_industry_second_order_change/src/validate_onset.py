"""Read-only validation of sampling, chronology, labels and reported process counts."""
import json
import subprocess
import sys
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from onset_replay import EP,SOURCE,sha,stable,load,observation


def main():
    checks=[];root=EP/'outputs/r06'
    history=json.loads((EP/'outputs/onset_source_history.json').read_text())
    historical={(r['source'],r['sha256']):Path(r['snapshot']) for r in history}
    verified=set()
    def verify(path,expected):
        path=Path(path)
        if sha(path)!=expected:
            archived=historical.get((str(path),expected));assert archived is not None,(path,expected)
            assert sha(archived)==expected
        verified.add((str(path),expected))
    receipt=json.loads((root/'sampling_receipt.json').read_text())
    for path,h in receipt['inputs'].items():verify(path,h)
    assert sha(root/'cases.csv')==receipt['cases_sha256'];assert sha(root/'sample_registry.csv')==receipt['registry_sha256']
    cases=pd.read_csv(root/'cases.csv');registry=pd.read_csv(root/'sample_registry.csv')
    for period,g in registry.groupby('period'):
        av=g[g.status.ne('NO_ENTRY_DATA')].sort_values('sample_hash');ready=av[av.status.eq('READY')]
        expected=[]
        if len(av):
            first=(ready if len(ready) else av).iloc[0];expected.append(first.industry_code)
            rem=av[av.industry_code.ne(first.industry_code)];ins=rem[rem.status.ne('READY')]
            second=ins if len(ins) else rem
            if len(second):expected.append(second.iloc[0].industry_code)
        assert expected==cases[cases.period.eq(period)].industry_code.tolist()
    checks.append({'name':'entry-stratified deterministic sample identities','cases':len(cases),'registry_rows':len(registry),'status':'PASS'})
    total=0
    for _,case in cases.iterrows():
        lines=(root/'replay'/f'{case.case_id}.jsonl').read_text().splitlines();prev='GENESIS';dates=[]
        for i,line in enumerate(lines):
            row=json.loads(line);h=row.pop('record_hash');assert row['previous_hash']==prev
            assert hashlib.sha256(stable(row).encode()).hexdigest()==h
            assert row['step']==i+1;prev=h;dates.append(row['asof'])
        assert dates==sorted(set(dates));total+=len(lines)
        for step in [4,8,12,18,26,27]:
            cp=json.loads((root/f'checkpoint_{step:02d}.json').read_text());prefix='\n'.join(lines[:step])+'\n'
            assert hashlib.sha256(prefix.encode()).hexdigest()==cp['ledger_hashes'][f'{case.case_id}.jsonl']
    checks.append({'name':'immutable per-week chains and all checkpoint prefixes','records':total,'status':'PASS'})
    d,m,weeks=load();grouped={k:g for k,g in d.groupby(['era','industry_code'])}
    for _,c in cases.iterrows():
        lines=(root/'replay'/f'{c.case_id}.jsonl').read_text().splitlines()
        expected_dates=weeks[(weeks>=pd.Timestamp(c.entry))&(weeks<=pd.Timestamp(c.end))]
        assert len(lines)==len(expected_dates),'unreplayed tail'
        for j in sorted(set([0,len(lines)//2,len(lines)-1])):
            row=json.loads(lines[j]);date=pd.Timestamp(row['asof']);g=grouped[(c.era,c.industry_code)];g=g[g.date.le(date)]
            recalc=observation(g,m.loc[:date],date)
            for key,val in recalc.items():assert row[key]==val,(c.case_id,j,key)
    checks.append({'name':'all cases replayed through intended interval; prefix recomputation','samples':len(cases)*3,'status':'PASS'})
    for name in ['r07/receipt.json','r08/receipt.json','r08/secondary_receipt.json']:
        r=json.loads((EP/'outputs'/name).read_text())
        for path,h in r['inputs'].items():verify(path,h)
    checks.append({'name':'all process input hashes/current or archived source versions','unique_inputs':len(verified),'status':'PASS'})
    episodes=pd.read_csv(EP/'outputs/r07/episodes.csv.gz',parse_dates=['date'])
    summary=pd.read_csv(EP/'outputs/r07/development_summary.csv')
    for _,r in summary.iterrows():
        e=episodes[episodes.method.eq(r.method)]
        if r.scope=='outside_sample':e=e[~e.sample_case]
        k=e[e.followup_known]
        assert len(e)==r.episodes and len(k)==r.known
        assert k.development.eq('SUSTAINED_6_OF_8').sum()==r.sustained
    p=pd.read_parquet('/tmp/ep33_onset_panel.parquet');groups={k:g.sort_values('date').reset_index(drop=True) for k,g in p.groupby(['era','industry_code','block'])}
    pairs=pd.read_csv(EP/'outputs/r08/common_endpoint_episodes.csv.gz',parse_dates=['date'])
    dated={}
    for (era,code,b),g in groups.items():
        for i,date in enumerate(g.date):
            key=(era,code,date)
            assert key not in dated
            dated[key]=(g,i)
    for _,r in pairs.iterrows():
        g,i=dated[(r.era,r.industry_code,r.date)];tail=g.iloc[i+5:i+9]
        assert len(tail)==4 and int(tail.rate20.gt(0).sum())>=0
        assert (tail.rate20.gt(0).sum()>=3)==r.sustained_final4
    cs=pd.read_csv(EP/'outputs/r08/common_endpoint_summary.csv')
    for _,r in cs.iterrows():
        g=pairs if r.scope=='all' else pairs[~pairs.sample_case]
        a=g if r.method=='early_all' else g[g[r.method+'_accepted']]
        assert len(a)==r.accepted and a.sustained_final4.sum()==r.positive_retained
        assert g.sustained_final4.sum()-a.sustained_final4.sum()==r.positive_missed
    checks.append({'name':'development and common-endpoint outcomes independently recomputed','paired_events':len(pairs),'status':'PASS'})
    # Re-running a checkpoint must be read-only.
    before={p.name:sha(p) for p in root.glob('checkpoint_*.json')}
    subprocess.run([sys.executable,str(EP/'src/onset_replay.py'),'--advance','4'],check=True,capture_output=True,text=True)
    assert before=={p.name:sha(p) for p in root.glob('checkpoint_*.json')}
    tests=subprocess.run([sys.executable,'-m','pytest','-q',str(EP/'tests')],capture_output=True,text=True)
    assert tests.returncode==0,tests.stdout+tests.stderr
    checks.append({'name':'temporal tests and repeat-checkpoint immutability','status':'PASS','test_output':tests.stdout.strip()})
    result={'status':'PASS','checks':checks,'scope':'R06-R08 execution evidence, not full goal achievement or independent PIT/causal proof'}
    (EP/'outputs/onset_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
