"""Exact common-control training scope; no models are fit here."""
import pandas as pd
from common import *
from train_r02 import target
from style_models_r55 import METHODS
from label_fold_audit_r130 import gate,payload_diff,LABELS
K=KEY+['date'];FK=['era','level','task','horizon','year']


def run():
    out=ROOT/'outputs/r134';out.mkdir(exist_ok=True);panels={};paths=[]
    for side,mp in [('old',ROOT/'data/monthly_panel.parquet'),('new',ROOT/'outputs/r130/monthly_panel.parquet')]:
        cp=ROOT/f'outputs/r133/cohort_{side}.parquet';lp=ROOT/'data/l1_monthly_panel.parquet';paths.extend([cp,mp,lp])
        labels=pd.concat([pd.read_parquet(p,columns=K+LABELS) for p in [mp,lp]],ignore_index=True)
        panel=pd.read_parquet(cp).merge(labels,on=K,how='left',validate='one_to_one');panel.to_parquet(out/f'common_panel_{side}.parquet',index=False);panels[side]=panel
    ledgers=[];deltas=[];groups=sorted(set(map(tuple,panels['old'][['era','level']].to_numpy()))|set(map(tuple,panels['new'][['era','level']].to_numpy())))
    for era,level in groups:
      for task in ['return','onset','reversal']:
       for h in [20,60]:
        qs={}
        for side,p in panels.items():
            g=p[p.era.eq(era)&p.level.eq(level)].copy();y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible];qs[side]=q
        for year in range(2020,2027):
            ident=dict(era=era,level=level,task=task,horizon=h,year=year);roles={};records={}
            for side,q in qs.items():
                rec,parts=gate(q,year,h,task);records[side]=rec;roles[side]=parts;ledgers.append(dict(ident,version=side,**rec))
            for role,a,b in zip(['fit','cal','test'],roles['old'],roles['new']):
                diff=payload_diff(a,b,['y',f'excess{h}',f'maturity{h}','entry_date']+['rank_'+c for c in METHODS['FSMD']])
                deltas.append(dict(ident,role=role,old_status=records['old']['status'],new_status=records['new']['status'],**diff))
    ledger=pd.DataFrame(ledgers);ledger.to_csv(out/'fold_ledger.csv',index=False);js(out/'payload_deltas.json',deltas)
    maps={}
    for family in ['r55','r56']:
        p=ROOT/f'outputs/{family}/model_parameters.json';paths.append(p);models=json.loads(p.read_text())
        maps[family]={tuple(m.get(k,'return' if k=='task' else None) for k in FK)+(m['method'],) for m in models}
    affected={}
    for d in deltas:
        if not(d['added'] or d['removed'] or d['changed_common']):continue
        affected.setdefault(tuple(d[k] for k in FK),[]).append(d)
    scope=[]
    for key,changes in sorted(affected.items()):
        if not any(x['old_status']=='fit' or x['new_status']=='fit' for x in changes):continue
        roles=sorted({x['role'] for x in changes});family='r55' if key[2]=='return' else 'r56';methods=list(METHODS)
        for method in methods:assert key+(method,) in maps[family]
        scope.append(dict(zip(FK,key),family=family,changed_roles=roles,methods=methods,action='refit_and_evaluate' if set(roles)&{'fit','cal'} else 'reevaluate_fixed_model',model_count=len(methods)))
    js(out/'retrain_scope.json',dict(folds=scope,required_models=sum(x['model_count'] for x in scope),refit_models=sum(x['model_count'] for x in scope if x['action']=='refit_and_evaluate'),reevaluate_only_models=sum(x['model_count'] for x in scope if x['action']=='reevaluate_fixed_model'),state='required_not_executed'))
    paths += [Path(__file__),ROOT/'src/train_r02.py',ROOT/'src/style_models_r55.py',ROOT/'src/label_fold_audit_r130.py',ROOT/'protocols/r134.json']
    pivot=ledger.pivot(index=FK,columns='version',values='status')
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in dict.fromkeys(paths)},folds_per_version=len(ledger)//2,affected_roles=sum(bool(x['added'] or x['removed'] or x['changed_common']) for x in deltas),status_changes=int(pivot.old.ne(pivot.new).sum()),affected_formal_folds=len(scope),scope_by_task=pd.DataFrame(scope).groupby('task').agg(folds=('task','size'),models=('model_count','sum')).reset_index().to_dict('records'),quality='Historical-proxy; exact-scope audit only'))
    print('SCOPE',len(scope),sum(x['model_count'] for x in scope),flush=True)

if __name__=='__main__':run()
