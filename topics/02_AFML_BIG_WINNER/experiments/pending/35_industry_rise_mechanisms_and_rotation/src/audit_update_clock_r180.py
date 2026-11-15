"""Follow up schema audit: original capture omitted repaired known_at clock."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle


def run():
    out=ROOT/'outputs/r180';rp=ROOT/'outputs/r179/runs.json';runs=json.loads(rp.read_text());rows=[];summary=[];reads={str(rp):sha(rp)}
    for r in runs:
        if r['version']!='repaired':continue
        p=Path(r['snapshot']);m=verify_bundle(p);source=m['sources']['daily_0'];d=pd.read_parquet(source['path']);cut=pd.Timestamp(r['asof'])
        leak=d[(d.date<=cut)&(d.known_at>cut)].copy();leak['asof']=cut;rows.append(leak)
        observed=pd.read_parquet(p/'observations.parquet')
        summary.append(dict(asof=r['asof'],future_known_prefix_rows=len(leak),future_known_on_observation_date=int(leak.date.eq(cut).sum()),all_anchors=bool(leak.source_kind.eq('anchor').all()),l2_l3_membership_dates_present=int(observed[observed.level.isin(['L2','L3'])].membership_asof.notna().sum())))
        reads[str(p/'manifest.json')]=sha(p/'manifest.json');reads[source['path']]=source['sha256']
    pd.concat(rows,ignore_index=True).to_parquet(out/'future_known_rows.parquet',index=False)
    js(out/'clock_audit.json',dict(status='INPUT_CLOCK_FAILURE_CONFIRMED',summary=summary,reads=reads,interpretation='R179 engineering replay preserved, not an admissible as-of observation. Next adapter must enforce known_at and reconstruct provenance without filling old dates.'))
    print(summary)


if __name__=='__main__':run()
