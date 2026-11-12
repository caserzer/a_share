"""Independent feature, workload and whole-directory checks on B06 outputs."""
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
out=EP/'outputs/v2_b07';r=json.loads((out/'replay_receipt.json').read_text())
for p,h in r['inputs'].items():assert sha(Path(p))==h
for p,h in r['artifacts'].items():assert sha(out/p)==h
raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['date','day_i','era','industry_code','nav','block'])
lookup={(x.era,x.industry_code,int(x.day_i)):(x.nav,x.block) for x in raw.itertuples()}
cal=raw[['date','day_i']].drop_duplicates().set_index('date').day_i.to_dict()
cat=pd.read_parquet(EP/'outputs/r01/weekly_catalog.parquet',columns=['date','era','industry_code'])
keys=pd.MultiIndex.from_frame(cat)
new_count=0
for path in sorted(out.glob('seed*/q5_d0/[AB]/events.parquet')):
    arm=path.parent.name;seed=int(path.parents[2].name[4:]);identity=json.loads((path.parent/'run_identity.json').read_text());assert identity['run_id']==str(path.parent.relative_to(EP/'outputs'));ev=pd.read_parquet(path);assert ev.event_id.is_unique
    pool=set();exits={}
    for row in ev.sort_values(['date','event_id']).itertuples():
        k=(row.era,row.industry_code)
        if row.kind=='EXIT':assert k in pool;pool.remove(k);exits[k]=row.week
        elif row.kind=='NEW':
            assert k not in pool and row.week-exits.get(k,-100)>=4;pool.add(k)
            day=int(cal[row.date]);current,block=lookup[(*k,day)]
            for h in (5,20,40):
                old,b=lookup[(*k,day-h)];assert b==block==row.block and old>0 and current>0
                if h in (5,20):assert np.isclose(current/old-1,getattr(row,f'r{h}'),atol=1e-12)
            assert row.r5>0 and row.r20>0
            expected_random=int.from_bytes(hashlib.sha256(f'{seed}|{row.date:%Y-%m-%d}|{row.era}|{row.industry_code}'.encode()).digest()[:8],'big')/2**64
            assert np.isclose(row.score,row.r20 if arm=='A' else expected_random,atol=1e-12)
            new_count+=1
        else:assert k in pool
        assert len(pool)<=20
    st=pd.read_parquet(path.parent/'catalog_states.parquet')
    assert not st.duplicated(['date','era','industry_code']).any()
    assert pd.MultiIndex.from_frame(st[['date','era','industry_code']]).sort_values().equals(keys.sort_values())
    assert set(st.state)<=set(['NEW','TRACKING','EXIT','DATA_INSUFFICIENT','NOT_TRIGGERED'])
for grid in sorted(out.glob('seed*/q5_d0')):
    a=pd.read_csv(grid/'A/weekly_burden.csv');b=pd.read_csv(grid/'B/weekly_burden.csv')
    assert a.date.equals(b.date) and a.new.equals(b.new)
    assert a.new.le(int(grid.name[1])).all()
res=dict(runs=16,new_features_checked=new_count,catalog_rows_per_run=len(cat),
    checks=['original input and output hashes','all NEW features from current and earlier same-chain prices',
    '20d score or independent fixed random key matches registered arm','run-qualified identity includes seed','pool membership and reentry cooldown','5/20 capacity','all weekly paired admissions identical',
    'full-directory five-state identity coverage'],script_sha256=sha(Path(__file__)))
(out/'replay_verification.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
