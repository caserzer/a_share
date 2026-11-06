"""Stage B may execute only after all Stage A frequency gates fail."""
import json
import pandas as pd
from common import CACHE, OUT, KEY, THRESHOLDS, BENCHMARKS, js, sha
from labels import label_one


def run():
    verdict=json.loads((OUT/'stage_a/verdict.json').read_text())
    assert verdict['advance_to_early_stage'] and not any(x['passed'] for x in verdict['frequency_gates'].values())
    f=pd.read_parquet(CACHE/'features.parquet')
    daily=pd.read_parquet(CACHE/'daily_industries.parquet',columns=KEY+['block','date'])
    ends=daily.groupby(KEY+['block']).date.max().to_dict()
    phases=pd.read_parquet(CACHE/'daily_phases.parquet')
    groups={k:g.to_dict('records') for k,g in phases.groupby(KEY+['block','threshold'])}
    rows=[]
    for key,g in f.groupby(KEY+['block'],sort=False):
        for threshold in THRESHOLDS:
            stages=groups.get((*key,threshold),[])
            for row in g.itertuples():
                for bm in BENCHMARKS:
                    value,available,event,reason=label_one(row.date-pd.DateOffset(months=3),row.date,
                        stages,ends[key],bm)
                    rows.append(dict(row_id=row.row_id,threshold=threshold,benchmark=bm,y=value,
                        label_available_at=available,horizon_end=row.date,event_or_witness_id=event,reason='EARLY_'+reason))
    labels=pd.DataFrame(rows);labels.to_parquet(CACHE/'stage_b_labels.parquet',index=False)
    js(OUT/'stage_b/label_audit.json',dict(trigger_verdict_sha256=sha(OUT/'stage_a/verdict.json'),
        definition='qualified stage low in (t - 3 calendar months, t]; outcome still future-confirmed',
        labels_sha256=sha(CACHE/'stage_b_labels.parquet'),rows=len(labels),known=int(labels.y.notna().sum()),
        positives=int(labels.y.sum()),independent_holdout=False,quality='second-stage exploratory reuse'))
    print('stage B labels',len(labels),'known',labels.y.notna().sum(),flush=True)


if __name__=='__main__':run()
