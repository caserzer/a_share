import json
from audit_local_inputs import EP,sha
import pandas as pd
from s01_variants import evaluate
from s02_lifetime_repeat import associate

out=EP/'outputs/r04'
pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';p=pd.read_parquet(pfile)
results={}
for arm in ['A','B']:
    source=out/(arm+'_evaluated.parquet')
    late=evaluate('r04_'+arm,source)
    a,l=associate(pd.read_parquet(source),p)
    a.to_parquet(out/(arm+'_lifetime_alerts.parquet'),index=False)
    l.to_parquet(out/(arm+'_lifetime_associations.parquet'),index=False)
    assert a.alert_id.is_unique and a.associations.sum()==len(l)
    joined=a[['alert_id','era','industry_code','day']].merge(p,on=['era','industry_code'])
    joined=joined[joined.day.between(joined.start_day_i,joined.end_day_i)].sort_values(['day','alert_id'])
    assert set(zip(joined.alert_id,joined.process_id))==set(zip(l.alert_id,l.process_id))
    joined['repeat']=joined.duplicated('process_id')
    assert set(joined.loc[joined['repeat']&~joined.left_origin_uncertain,'alert_id'])==set(a.loc[a.known_repeat,'alert_id'])
    results[arm]=dict(late=late,lifetime=dict(total=len(a),known_repeat=int(a.known_repeat.sum()),unknown_only_repeat=int(a.unknown_only_repeat.sum()),mixed_first_repeat=int(a.mixed_first_repeat.sum()),beyond60_known_repeat=int(a.beyond60_known_repeat.sum()),operational_status='NOT_MODELED'))
(out/'supplements.json').write_text(json.dumps(dict(results=results,source_sha256=sha(EP/'src/r04_supplements.py')),ensure_ascii=False,indent=2)+'\n')
