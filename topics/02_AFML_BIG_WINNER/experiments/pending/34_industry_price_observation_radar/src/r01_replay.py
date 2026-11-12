"""Prepare/seal past-only baseline, then replay without importing future evaluators."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from r01_features import PRICE_COLUMNS,features,complete_week_reviews
from r01_pool import ObservationPool

OUT=EP/'outputs/r01'


def sources():
    receipt=json.loads((PRIOR/'receipt.json').read_text())
    calendar=next(Path(p) for p in receipt['inputs'] if p.endswith('/calendar.parquet'))
    return PRIOR/'daily_industries.parquet',calendar,EP/'outputs/r00_coverage/catalog.json'


def prepare():
    OUT.mkdir(exist_ok=True)
    if (OUT/'prediction_seal.json').exists():raise FileExistsError('R01 already sealed')
    subprocess.run([sys.executable,str(EP/'src/seal_r00.py'),'verify'],check=True)
    daily,calendar,catalog=sources()
    raw=pd.read_parquet(daily,columns=PRICE_COLUMNS);f=features(raw)
    checks=[]
    for cutoff in ['2019-06-28','2021-11-26','2023-06-30','2025-06-30']:
        prefix=features(raw[raw.date.le(cutoff)])
        expected=f[f.date.le(cutoff)].reset_index(drop=True)
        pd.testing.assert_frame_equal(prefix,expected)
        checks.append(dict(cutoff=cutoff,rows=len(prefix)))
    f.to_parquet(OUT/'past_only_features.parquet',index=False)
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(EP/'tests'),'-p','test_r01_baseline.py','-v'],capture_output=True,text=True)
    (OUT/'preflight_tests.log').write_text(tests.stdout+tests.stderr)
    if tests.returncode:raise RuntimeError('R01 preflight failed')
    inputs=[daily,calendar,catalog,EP/'configs/r01_baseline.json',EP/'rounds/R01_simple_price_baseline_plan.md',
            EP/'src/r01_features.py',EP/'src/r01_pool.py',Path(__file__),EP/'tests/test_r01_baseline.py',
            EP/'protocols/r00_v1/seal.json',OUT/'past_only_features.parquet',OUT/'preflight_tests.log']
    seal=dict(status='PREDICTION_RULES_SEALED_BEFORE_REPLAY',prefix_checks=checks,
              files={str(p):sha(p) for p in inputs},scope='No labels or predictions evaluated')
    (OUT/'prediction_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status=seal['status'],prefix_rows=sum(x['rows'] for x in checks),feature_rows=len(f))))


def replay():
    if (OUT/'replay_receipt.json').exists():raise FileExistsError('R01 replay already exists')
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for p,h in seal['files'].items():
        if sha(Path(p))!=h:raise ValueError('prediction seal drift: '+p)
    subprocess.run([sys.executable,str(EP/'src/seal_r00.py'),'verify'],check=True)
    daily,calendar,catalog=sources()
    f=pd.read_parquet(OUT/'past_only_features.parquet');cat=pd.read_json(catalog)
    c=json.loads((EP/'configs/r01_baseline.json').read_text());pool=ObservationPool(c)
    days=pd.DatetimeIndex(pd.read_parquet(calendar).date).sort_values();day_map={d:i for i,d in enumerate(days)}
    asof=f.date.max();reviews=complete_week_reviews(days,asof)
    bydate={(era,date):g for (era,date),g in f.groupby(['era','date'])}
    records=[];events=[];weekly=[];transition=[]
    boundary=pd.Timestamp('2021-11-30')
    for date in reviews:
        if date<pd.Timestamp('2017-01-01'):continue
        era='SW2014' if date<=boundary else 'SW2021' if date>=pd.Timestamp('2022-01-01') else None
        if pool.era=='SW2014' and date>boundary:
            events.extend(pool.close_era(boundary,day_map[boundary]))
        if era is None:
            transition.append(str(date.date()));continue
        base=cat[cat.era.eq(era)].copy()
        current=bydate.get((era,date))
        if current is None:
            rows=base.assign(eligible=False,score=np.nan,history_proxy=np.nan,price_status='NO_LOCAL_PRICE_ROW')
        else:
            rows=base.merge(current[['industry_code','eligible','score','history_proxy','price_status']],on='industry_code',how='left',validate='one_to_one')
            rows['eligible']=rows.eligible.eq(True);rows['price_status']=rows.price_status.fillna('NO_LOCAL_PRICE_ROW')
        state,ev=pool.step(era,date,day_map[date],rows.to_dict('records'));events.extend(ev)
        event_ids={e['industry_code']:e for e in ev}
        for r in rows.to_dict('records'):
            code=r['industry_code'];s=state[code];e=event_ids.get(code,{})
            records.append(dict(**r,date=date,day_i=day_map[date],input_asof=date,rule_version=c['version'],
                                first_hint_date=e.get('entry_date'),**s))
        new=sum(e['event']=='NEW' for e in ev)
        weekly.append(dict(era=era,date=date,new_industries=new,in_pool=len(pool.active),
                           exits=sum(e['event']=='EXIT' for e in ev),data_insufficient=sum(x['state']=='DATA_INSUFFICIENT' for x in state.values())))
    report=pd.DataFrame(records);ev=pd.DataFrame(events);w=pd.DataFrame(weekly)
    assert not report.duplicated(['era','industry_code','date']).any()
    expected=sum(int(cat.era.eq(r.era).sum()) for r in w.itertuples())
    assert len(report)==expected
    assert w.new_industries.le(c['weekly_new_cap']).all() and w.in_pool.le(c['pool_cap']).all()
    new=ev[ev.event.eq('NEW')];assert new.observation_id.is_unique
    assert not new.assign(week=new.date.dt.to_period('W-SUN')).duplicated(['era','industry_code','week']).any()
    for name,frame in [('weekly_catalog',report),('events',ev),('weekly_workload',w)]:frame.to_parquet(OUT/f'{name}.parquet',index=False)
    latest=report[report.date.eq(report.date.max())]
    latest.to_json(OUT/'latest_observation_catalog.json',orient='records',force_ascii=False,date_format='iso',indent=2)
    result=dict(status='HISTORICAL_REPLAY_NOT_VALIDATED_METHOD',data_asof=str(asof.date()),latest_review=str(report.date.max().date()),
                catalog_rows=len(report),review_weeks=len(w),new_observations=len(new),
                max_weekly_new=int(w.new_industries.max()),max_in_pool=int(w.in_pool.max()),
                latest_state_counts=latest.state.value_counts().to_dict(),transition_weeks=transition,
                pool_cap_provenance=c['pool_cap_provenance'],prediction_seal_sha256=sha(OUT/'prediction_seal.json'),
                artifacts={p.name:sha(p) for p in [OUT/'weekly_catalog.parquet',OUT/'events.parquet',OUT/'weekly_workload.parquet',OUT/'latest_observation_catalog.json']})
    (OUT/'replay_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='replay':replay()
    else:raise ValueError('use prepare or replay')
