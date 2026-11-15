"""Frozen M02 signals, independent and two-arm paired pool replays."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha
import v3_m02_replay as frozen


def main():
    source=EP/'outputs/v3_m02_models';out=EP/'outputs/v3_m03_replay'
    if out.exists():raise FileExistsError(out)
    rec=json.loads((source/'receipt.json').read_text())
    for rel,digest in rec['artifacts'].items():assert sha(source/rel)==digest,rel
    arms=list(frozen.ARMS)
    c=pd.read_parquet(source/'scored_catalog.parquet')
    keep=['date','era','industry_code','industry_name','block','r5','r20','r40','week','enhance','eligible','confirmed','eligible_original','confirmed_original']+['score_'+a for a in arms if a!='ORIGINAL20']
    c=c[keep].copy();c['score_ORIGINAL20']=c.r20
    out.mkdir();summary=[]
    designs=[('solo_'+a,[a]) for a in arms]+[('pair_balance',['ORIGINAL20','BALANCED']),('pair_cover',['ORIGINAL20','LR_COVER'])]
    for design,selected in designs:
        frozen.ARMS=selected
        temporary=out/('_building_'+design);temporary.mkdir()
        result=frozen.replay(c,5,0,temporary)
        for arm,row in zip(selected,result):
            old=temporary/row['run_id'];name=design if design.startswith('solo_') else design+'_'+arm
            dest=out/name;old.rename(dest)
            ev=pd.read_parquet(dest/'events.parquet')
            ev.event_id=ev.event_id.str.replace('M02-',f'M03-{design}-',regex=False)
            ev.to_parquet(dest/'events.parquet',index=False)
            row.update(run_id=name,design=design,arm=arm);summary.append(row)
        temporary.rmdir();print('Replayed',design,flush=True)
    frozen.ARMS=arms
    pd.DataFrame(summary).to_csv(out/'run_inventory.csv',index=False)
    support=pd.read_csv(EP/'outputs/v3_m02_replay/calendar_coverage.csv')
    support.to_csv(out/'calendar_coverage.csv',index=False)
    sources=[source/'receipt.json',source/'scored_catalog.parquet',EP/'src/v3_m02_replay.py',EP/'protocols/v3_r00/m03_independent_plan.md',EP/'outputs/v3_m02_replay/calendar_coverage.csv',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')


if __name__=='__main__':main()
