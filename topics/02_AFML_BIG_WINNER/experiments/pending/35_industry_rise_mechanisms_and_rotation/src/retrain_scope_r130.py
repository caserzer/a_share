"""Derive exact refit/evaluation scope from audited payload deltas."""
import pandas as pd
from common import *
FK=['era','level','cohort','task','horizon','year']

def run():
    out=ROOT/'outputs/r130';dp=out/'fold_payload_deltas.json';lp=out/'fold_ledger.csv';mp=ROOT/'outputs/r02/model_parameters.json'
    rows=json.loads(dp.read_text());models=json.loads(mp.read_text());mapping={tuple(m[k] for k in FK)+(m['method'],):m for m in models};groups={}
    for x in rows:
        if not(x['added'] or x['removed'] or x['changed_common']):continue
        key=tuple(x[k] for k in FK);groups.setdefault(key,[]).append(x)
    scope=[]
    for key,changes in sorted(groups.items()):
        trained=any(x['old_status']=='fit' or x['new_status']=='fit' for x in changes)
        if not trained:continue
        roles=sorted({x['role'] for x in changes});action='refit_and_evaluate' if set(roles)&{'fit','cal'} else 'reevaluate_fixed_model'
        methods=['F'] if key[2]=='F' else ['F',key[2]]
        for method in methods:assert key+(method,) in mapping
        scope.append(dict(zip(FK,key),changed_roles=roles,action=action,methods=methods,model_count=len(methods)))
    pairs=pd.read_parquet(out/'label_pairs.parquet');changed=np.zeros(len(pairs),bool)
    for h in [20,60]:
        a=pairs[f'maturity{h}_old'];b=pairs[f'maturity{h}_new'];changed|=pairs._merge.eq('both').to_numpy()&~(a.eq(b)|(a.isna()&b.isna())).to_numpy()
    pairs.loc[changed].to_parquet(out/'changed_label_rows.parquet',index=False)
    js(out/'retrain_scope.json',dict(reads={str(p):sha(p) for p in [dp,lp,mp,out/'label_pairs.parquet',Path(__file__)]},folds=scope,affected_trained_folds=len(scope),refit_folds=sum(x['action']=='refit_and_evaluate' for x in scope),refit_models=sum(x['model_count'] for x in scope if x['action']=='refit_and_evaluate'),reevaluate_only_folds=sum(x['action']=='reevaluate_fixed_model' for x in scope),changed_label_rows=int(changed.sum()),state='required_not_executed',scope_boundary='R02 only; downstream model and strategy dependencies still require propagation'))
    print('SCOPE',len(scope),'trained folds; refit models',sum(x['model_count'] for x in scope if x['action']=='refit_and_evaluate'))

if __name__=='__main__':run()
