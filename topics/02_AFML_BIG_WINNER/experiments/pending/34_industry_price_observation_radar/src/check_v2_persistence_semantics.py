"""Counterexamples to the old midpoint occupancy criterion, no tuned replacement."""
import json
from pathlib import Path
import numpy as np
from audit_local_inputs import EP,sha
from v2_label_probe02_persistence import retained

out=EP/'outputs/r00_v2_family_audit/persistence_counterexamples.json'
if out.exists():
    raise FileExistsError('Preserve diagnostic')
paths={
    'steady_rise': .003*np.arange(80),
    'continuous_rise_then_heating': np.r_[.003*np.arange(40),.120+.009*np.arange(40)],
    'smooth_acceleration': .0001*np.arange(80)**2,
    'one_week_pulse': np.where(np.arange(80)==40,.15,0.)
}
rows=[]
for name,z in paths.items():
    mono=bool((np.diff(z)>0).all())
    expected=name!='one_week_pulse'
    result=retained(z)
    rows.append(dict(path=name,strictly_increasing=mono,
        expected_persistence=expected,old_whole_retained=result,
        first_half_retained=retained(z[:40]),second_half_retained=retained(z[40:]),
        expectation_met=result==expected,log_prices=z.tolist()))
assert all(x['strictly_increasing'] for x in rows[:3])
assert rows[1]['first_half_retained'] and rows[1]['second_half_retained']
assert not rows[1]['old_whole_retained']
result=dict(scope='Semantic falsification of L02 midpoint occupancy as general persistence definition',
            no_new_label_or_method_selected=True,
            source_hashes={str(p):sha(p) for p in [Path(__file__),EP/'src/v2_label_probe02_persistence.py']},
            cases=rows)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='log_prices'} for r in rows],indent=2))
