"""Seal predeclared confirmation predictions before evaluating any outcomes."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha
from r01_delay_pool import DelayedPool


def main():
    out=EP/'outputs/r01_delay';out.mkdir(exist_ok=True)
    if (out/'prediction_seal.json').exists():raise FileExistsError('delay already sealed')
    base=json.loads((EP/'configs/r01_baseline.json').read_text())
    seal=json.loads((EP/'outputs/r01/prediction_seal.json').read_text())
    for f,h in seal['files'].items():assert sha(Path(f))==h
    wfile=EP/'outputs/r01/weekly_catalog.parquet';hfile=EP/'outputs/r01/past_only_features.parquet'
    receipt=json.loads((EP/'outputs/r01/replay_receipt.json').read_text())
    assert sha(wfile)==receipt['artifacts'][wfile.name]
    w=pd.read_parquet(wfile,columns=['era','date','day_i','industry_code','eligible','score'])
    history=pd.read_parquet(hfile,columns=['era','industry_code','day_i','eligible','score'])
    daily={era:{code:g.sort_values('day_i') for code,g in h.groupby('industry_code')} for era,h in history.groupby('era')}
    artifacts={}
    for delay in [0,5,10]:
        pool=DelayedPool(base,delay);events=[];weeks=[]
        for (era,date,day),g in w.groupby(['era','date','day_i'],sort=True):
            states,ev=pool.step(era,date,int(day),g[['industry_code','eligible','score']].to_dict('records'),daily[era])
            events.extend(ev);weeks.append(dict(era=era,date=date,new_industries=sum(x['event']=='NEW' for x in ev),in_pool=len(pool.pool.active),pending=len(pool.pending)))
        events=pd.DataFrame(events);weeks=pd.DataFrame(weeks)
        if delay==0:
            old=pd.read_parquet(EP/'outputs/r01/events.parquet');cols=list(old.columns)
            def canon(x):return x[x.reason.ne('CLASSIFICATION_BOUNDARY')][cols].sort_values(['date','industry_code','event']).reset_index(drop=True)
            pd.testing.assert_frame_equal(canon(events),canon(old),check_dtype=False)
            oldw=pd.read_parquet(EP/'outputs/r01/weekly_workload.parquet')
            pd.testing.assert_frame_equal(weeks[['era','date','new_industries','in_pool']],oldw[['era','date','new_industries','in_pool']],check_dtype=False)
        for name,df in [(f'delay{delay}_events.parquet',events),(f'delay{delay}_weeks.parquet',weeks)]:
            df.to_parquet(out/name,index=False);artifacts[name]=sha(out/name)
        new=events[events.event.eq('NEW')]
        print(json.dumps(dict(delay=delay,new=len(new),wait_median=float(new.confirmation_wait.median()),wait_max=float(new.confirmation_wait.max()))),flush=True)
    inputs=[wfile,hfile,EP/'configs/r01_baseline.json',EP/'src/r01_pool.py',EP/'src/r01_delay_pool.py',Path(__file__),EP/'tests/test_r01_delay.py',EP/'rounds/R01_delay_control_plan.md']
    (out/'prediction_seal.json').write_text(json.dumps(dict(delays=[0,5,10],main_reproduced=True,inputs={str(x):sha(x) for x in inputs},artifacts=artifacts),indent=2)+'\n')


if __name__=='__main__':main()
