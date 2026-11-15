"""Seven fixed arms: full paired grid plus independent 5/20 replays."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha
import v3_m02_replay as engine

ARMS=['ORIGINAL20','DATE_COVER','DATE_EARLY','DATE_BALANCED','PROCESS_COVER','PROCESS_EARLY','PROCESS_BALANCED']


def main():
    source=EP/'outputs/v3_m04_models';out=EP/'outputs/v3_m04_replay'
    if out.exists():raise FileExistsError(out)
    receipt=json.loads((source/'receipt.json').read_text())
    for rel,digest in receipt['artifacts'].items():assert sha(source/rel)==digest,rel
    cols=['date','era','industry_code','industry_name','block','r5','r20','r40','week','enhance','eligible','confirmed','eligible_original','confirmed_original']+['score_'+a for a in ARMS if a!='ORIGINAL20']
    c=pd.read_parquet(source/'scored_catalog.parquet',columns=cols);c['score_ORIGINAL20']=c.r20
    out.mkdir();summary=[]
    engine.ARMS=ARMS
    for q in [1,3,5]:
        for delay in [0,1]:
            rows=engine.replay(c,q,delay,out)
            for arm,row in zip(ARMS,rows):
                file=out/row['run_id']/'events.parquet';e=pd.read_parquet(file);e.event_id=e.event_id.str.replace('M02-','M04-paired-',regex=False);e.to_parquet(file,index=False)
                row.update(mode='paired',arm=arm,quota=q,delay=delay);summary.append(row)
            print('M04 paired',q,delay,flush=True)
    for arm in ARMS:
        engine.ARMS=[arm];temp=out/('_building_'+arm);temp.mkdir();row=engine.replay(c,5,0,temp)[0]
        dest=out/('solo_'+arm);(temp/row['run_id']).rename(dest);temp.rmdir()
        file=dest/'events.parquet';e=pd.read_parquet(file);e.event_id=e.event_id.str.replace('M02-',f'M04-solo-',regex=False);e.to_parquet(file,index=False)
        row.update(run_id=dest.name,mode='solo',arm=arm,quota=5,delay=0);summary.append(row);print('M04 independent',arm,flush=True)
    pd.DataFrame(summary).to_csv(out/'run_inventory.csv',index=False)
    support=EP/'outputs/v3_m02_replay/calendar_coverage.csv';pd.read_csv(support).to_csv(out/'calendar_coverage.csv',index=False)
    inputs=[source/'receipt.json',source/'scored_catalog.parquet',support,EP/'src/v3_m02_replay.py',EP/'protocols/v3_r00/m04_process_weight_plan.md',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
