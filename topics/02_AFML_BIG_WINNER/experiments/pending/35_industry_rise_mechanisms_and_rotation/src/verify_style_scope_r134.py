"""Independent targets, calendar masks, eligibility and payload scope audit."""
import pandas as pd
from common import *
K=KEY+['date']; FK=['era','level','task','horizon','year']
C=['mom20','mom60','vol20','dd60','past_excess20','past_excess60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']

def run():
    out=ROOT/'outputs/r134'; receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h,p
    panels={s:pd.read_parquet(out/f'common_panel_{s}.parquet') for s in ['old','new']}
    ledger=pd.read_csv(out/'fold_ledger.csv').fillna(''); deltas=json.loads((out/'payload_deltas.json').read_text()); dm={tuple(d[k] for k in FK)+(d['role'],):d for d in deltas}
    expected={}; checked=0
    for key,g in ledger.groupby(FK):
        era,level,task,h,year=key; parts={}
        for side in ['old','new']:
            p=panels[side];q=p[p.era.eq(era)&p.level.eq(level)].copy(); valid=q[f'excess{h}'].notna()
            if task=='return':q['y']=q[f'excess{h}']
            elif task=='onset':
                q['y']=((q[f'return{h}']>=(.05 if h==20 else .10))&(q[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(valid);q=q[q.past_excess20.le(0)]
            else:
                q['y']=q[f'rel_trough{h}'].le(-.08 if h==20 else -.12).astype(float).where(valid&q[f'rel_trough{h}'].notna());q=q[q.past_excess60.gt(0)&q.mom60.gt(0)]
            start=pd.Timestamp(year,1,1);cut=pd.Timestamp(year-1,7,1);m=q[f'maturity{h}'];known=q.y.notna()
            tr=q[q.date.lt(start if task=='return' else cut)&m.lt(start if task=='return' else cut)&known]
            ca=q.iloc[:0] if task=='return' else q[q.date.ge(cut)&q.date.lt(start)&m.lt(start)&known]
            te=q[q.date.dt.year.eq(year)];parts[side]=[tr,ca,te]
            reason=''
            if not len(te):reason='no_test'
            elif len(tr)<300 or tr.date.nunique()<18:reason='insufficient_train_months_or_rows'
            elif task!='return':
                if min((tr.y==0).sum(),(tr.y==1).sum())<30:reason='insufficient_train_classes'
                elif ca.date.nunique()<4 or len(ca)<100 or min((ca.y==0).sum(),(ca.y==1).sum())<10:reason='insufficient_calibration'
            row=g[g.version.eq(side)].iloc[0]
            assert [len(tr),len(ca),len(te),tr.date.nunique(),ca.date.nunique()]==[row.n_fit,row.n_cal,row.n_test,row.train_months,row.cal_months]
            assert row.reason==reason and row.status==('skipped' if reason else 'fit')
        changed=[]
        for role,a,b in zip(['fit','cal','test'],parts['old'],parts['new']):
            a=a.set_index(K);b=b.set_index(K);ix=a.index.intersection(b.index);fields={};union=set()
            for c in ['y',f'excess{h}',f'maturity{h}','entry_date']+['rank_'+c for c in C]:
                x=a.loc[ix,c];y=b.loc[ix,c]
                same=(x.eq(y)|(x.isna()&y.isna())) if c in ['entry_date',f'maturity{h}'] else pd.Series(np.isclose(x,y,rtol=1e-12,atol=1e-12,equal_nan=True),index=ix)
                bad=set(ix[~same]);fields[c]=len(bad);union.update(bad)
            diff=dict(old_rows=len(a),new_rows=len(b),added=len(b.index.difference(a.index)),removed=len(a.index.difference(b.index)),changed_common=len(union),fields=fields)
            d=dm[key+(role,)]
            for c,v in diff.items():assert d[c]==v,(key,role,c)
            if diff['added'] or diff['removed'] or union:changed.append(role)
            checked+=1
        if changed and g.status.eq('fit').any():expected[key]=sorted(changed)
    legacy_count=0
    for family in ['r55','r56']:
        old=pd.read_csv(ROOT/f'outputs/{family}/fold_ledger.csv').fillna('')
        if family=='r55':old['task']='return'
        for _,r in old.iterrows():
            match=ledger.version.eq('old')
            for k in FK:match &= ledger[k].eq(r[k])
            v=ledger[match];assert len(v)==1;v=v.iloc[0]
            mapping={'train_rows':'n_fit','test_rows':'n_test','train_months':'train_months'} if family=='r55' else {c:c for c in ['n_fit','n_cal','n_test','train_months','cal_months']}
            for a,b in mapping.items():assert r[a]==v[b],(family,a)
            assert (r.status=='fit')==(v.status=='fit');legacy_count+=1
        assert len(old)==len(ledger[ledger.version.eq('old')&ledger.task.isin(['return'] if family=='r55' else ['onset','reversal'])&ledger.n_test.gt(0)])
    scope=json.loads((out/'retrain_scope.json').read_text());assert len(scope['folds'])==len(expected)
    for f in scope['folds']:
        k=tuple(f[c] for c in FK);assert f['changed_roles']==expected[k];assert set(f['methods'])=={'FS','FSD','FSM','FSMD'}
        assert f['action']==('refit_and_evaluate' if set(expected[k])&{'fit','cal'} else 'reevaluate_fixed_model')
    assert scope['required_models']==4*len(expected)
    js(out/'verification.json',dict(status='PASS',independent_roles=checked,original_ledger_rows=legacy_count,formal_folds=len(expected),required_models=scope['required_models'],reads={str(p):sha(p) for p in [Path(__file__),out/'receipt.json',out/'fold_ledger.csv',out/'payload_deltas.json',out/'retrain_scope.json']}))
    print('PASS',checked,legacy_count,scope['required_models'])
if __name__=='__main__':run()
