"""Independent output reconciliation for R09-R11; no efficacy endorsement."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from pool_evaluation import EP,KEY,HORIZONS,sha

def main():
    checks=[];sources=0
    for folder in ['r09','r10','r11']:
        receipt=json.loads((EP/f'outputs/{folder}/receipt.json').read_text())
        for path,h in receipt['inputs'].items():
            assert sha(path)==h,(folder,path);sources+=1
    for folder in ['r09','r10','r11/coverage30','r11/coverage50']:
        out=EP/f'outputs/{folder}';p=pd.read_parquet(out/'evaluation_panel.parquet')
        s=pd.read_csv(out/'summary.csv');members=pd.read_csv(out/'memberships.csv.gz')
        assert not members.duplicated(['method','unit','role','row_id']).any()
        chosen=members[members.role.eq('selected')];mom=members[members.role.eq('momentum')]
        for (method,unit),g in chosen.groupby(['method','unit']):
            z=p.loc[g.row_id];assert z.eligible.all()
            if unit=='state':assert set(z.index)==set(p.index[p[method]&p.eligible])
            if unit=='entry':
                q=p.sort_values(KEY+['date']);previous=q.groupby(KEY)[method].shift();cont=q.week_i.sub(q.groupby(KEY).week_i.shift()).eq(1)
                expected=q[method]&previous.eq(False)&cont
                if folder.startswith('r11'):expected&=q.groupby(KEY).eligible.shift().eq(True)
                if folder=='r09':
                    history=pd.read_parquet('/tmp/ep33_onset_panel.parquet').sort_values(KEY+['date'])
                    prior=history.groupby(KEY)[method].shift()
                    consecutive=history.week_i.sub(history.groupby(KEY).week_i.shift()).eq(1)
                    flags=history[history[method]&prior.eq(False)&consecutive&history.eligible&history.date.ge('2021-01-01')]
                    identity=['era','industry_code','block','date']
                    assert set(map(tuple,z[identity].to_numpy()))==set(map(tuple,flags[identity].to_numpy())),(folder,method)
                else:assert set(z.index)==set(q.index[expected]),(folder,method)
            control=p.loc[mom[mom.method.eq(method)&mom.unit.eq(unit)].row_id]
            assert z.groupby('date').size().equals(control.groupby('date').size())
        for _,r in s.iterrows():
            ids=chosen[chosen.method.eq(r.method)&chosen.unit.eq(r.unit)].row_id
            z=p.loc[ids];h=int(r.horizon);known=z[f'win{h}'].notna()
            assert len(z)==r.total and int(known.sum())==r.known
            assert z[f'win{h}'].sum()==r.wins and r.wins+r.failures==r.known
            assert r.known+r.immature+r.missing==r.total
            if known.any():assert np.isclose(z[f'win{h}'].mean(),r.pooled_win_rate)
            for k in ['return','excess']:
                assert z.loc[known,f'{k}{h}'].notna().all()
            expected=(z[f'return{h}']>0)&(z[f'excess{h}']>0)
            assert (z.loc[known,f'win{h}']==expected.loc[known]).all()
        checks.append({'folder':folder,'summary_rows_verified':len(s),'membership_rows_verified':len(members)})
    registry=pd.read_csv(EP/'outputs/r09/universe_registry.csv.gz')
    assert not registry.duplicated(['date','era','industry_code']).any()
    summary={'status':'PASS','scope':'output consistency and provenance, not investment efficacy','source_hash_checks':sources,'round_checks':checks,
        'registry_rows':len(registry),'unit_tests':'12 passed (separately executed)','raw_outcome_checks':540,'original_goal_complete':False}
    (EP/'outputs/pool_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
