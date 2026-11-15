"""Independently validate exact required refit scope against all deltas."""
from common import *

def run():
    out=ROOT/'outputs/r130';scope=json.loads((out/'retrain_scope.json').read_text())
    for p,h in scope['reads'].items():assert sha(p)==h,p
    deltas=json.loads((out/'fold_payload_deltas.json').read_text());keys=['era','level','cohort','task','horizon','year'];expected={}
    for d in deltas:
        if max(d['added'],d['removed'],d['changed_common'])==0 or (d['old_status']!='fit' and d['new_status']!='fit'):continue
        expected.setdefault(tuple(d[k] for k in keys),set()).add(d['role'])
    assert len(scope['folds'])==len(expected)==scope['affected_trained_folds']
    counts={'refit_folds':0,'refit_models':0,'reevaluate_only_folds':0}
    for f in scope['folds']:
        key=tuple(f[k] for k in keys);assert set(f['changed_roles'])==expected.pop(key)
        methods=['F'] if f['cohort']=='F' else ['F',f['cohort']];assert f['methods']==methods and f['model_count']==len(methods)
        need=set(f['changed_roles'])&{'fit','cal'};assert f['action']==('refit_and_evaluate' if need else 'reevaluate_fixed_model')
        if need:counts['refit_folds']+=1;counts['refit_models']+=len(methods)
        else:counts['reevaluate_only_folds']+=1
    assert not expected
    for k,v in counts.items():assert scope[k]==v
    js(out/'scope_verification.json',dict(status='PASS',affected_trained_folds=scope['affected_trained_folds'],**counts,work_executed=False))
    print('PASS',counts)

if __name__=='__main__':run()
