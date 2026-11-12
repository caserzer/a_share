"""Signal-blind minimal duration mechanism; not production labels."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha
from v2_path_probe03_symmetric_calendar_corrected import excursions


def d8(y,reference=8):
    y=np.asarray(y,float)
    results=[]
    for i in range(reference+8,len(y)):
        a=y[i-7:i-3];b=y[i-3:i+1]
        known=bool(np.isfinite(y[reference]) and np.isfinite(np.r_[a,b]).all())
        hold=known and bool((np.r_[a,b]>y[reference]).all())
        increment=float(np.median(b)-np.median(a)) if known else None
        level=float(np.median(b)-y[reference]) if known else None
        hit=bool(hold and increment>=.002 and level>=.002)
        results.append(dict(i=i,known=known,all_above_reference=bool(hold),block_increment=increment,level_gain=level,confirmed=hit))
    return results


def main():
    out=EP/'outputs/v2_s10_duration_mechanism';out.mkdir(exist_ok=False)
    # Fixed high-variation decline ending at zero, no tuned synthetic amplitudes.
    prior=np.array([.16,.12,.15,.09,.12,.06,.09,.03,0.])
    future={
      'mild_monotone':.003*np.arange(1,17),
      'mild_with_retracement':.003*np.arange(1,17)+np.tile([.001,-.001],8),
      'strong_monotone':.02*np.arange(1,17),
      'pulse_back_to_base':np.r_[.05,np.zeros(15)],
      'jump_then_flat':np.full(16,.01),
      'stationary_alternation':np.tile([.01,.03],8),
      'flat':np.zeros(16),
      'declining':-.003*np.arange(1,17),
    }
    positives={'mild_monotone','mild_with_retracement','strong_monotone'}
    records=[]
    for name,after in future.items():
        y=np.r_[prior,after];r=d8(y);hits=[z['i'] for z in r if z['confirmed']]
        shifted=d8(y+2);assert [z['confirmed'] for z in shifted]==[z['confirmed'] for z in r]
        expected=name in positives;passed=bool(hits)==expected
        records.append(dict(name=name,expected_duration_confirmation=expected,actual_duration_confirmation=bool(hits),first_confirmation=None if not hits else hits[0],semantic_pass=passed,scale_invariant=True,old_amplitude_confirmed=sum(p['status']=='CONFIRMED' for p in excursions(y)),log_prices=y.tolist(),duration_checks=r))
    short=d8(np.r_[prior,.003*np.arange(1,8)]);assert not short
    (out/'synthetic_checks.json').write_text(json.dumps(records,indent=2)+'\n')
    assert all(r['semantic_pass'] for r in records), 'Keep failed mechanism; do not change settings'
    pathsfile=EP/'outputs/v2_s09_mild_paths/selected_case_paths.parquet';casefile=EP/'outputs/v2_s09_mild_paths/selected_cases.csv'
    paths=pd.read_parquet(pathsfile);cases=pd.read_csv(casefile);rows=[]
    for c in cases.itertuples():
        key=f'{c.era}/{c.industry_code}/{c.date}';p=paths[paths.case_key.eq(key)].sort_values('wi');assert len(p)==17
        y=p.y.to_numpy();checks=d8(y);assert len(checks)==1
        row=dict(case_key=key,industry_name=c.industry_name,era=c.era,code=c.industry_code,reference_date=c.date,check_date=c.end,old_full_history_confirmed_overlap=bool(c.overlap),**checks[0])
        row['old_on_truncated_context_confirmed']=sum(r['status']=='CONFIRMED' for r in excursions(y))
        rows.append(row)
    pd.DataFrame(rows).to_csv(out/'all_fixed_cases.csv',index=False)
    summary={'synthetic_cases':len(records),'synthetic_pass':all(r['semantic_pass'] for r in records),'short_history_unknown':True,'fixed_real_cases':len(rows),'duration_confirmed':sum(r['confirmed'] for r in rows),'limits':'Local duration mechanism only. Anchoring, interruption, identity and full-history labels not implemented. No method outcomes used.'}
    inputs=[Path(__file__),EP/'src/v2_path_probe03_symmetric_calendar_corrected.py',EP/'protocols/v2_s10/plan.md',pathsfile,casefile]
    (out/'receipt.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in inputs},'summary':summary,'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False));print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':main()
