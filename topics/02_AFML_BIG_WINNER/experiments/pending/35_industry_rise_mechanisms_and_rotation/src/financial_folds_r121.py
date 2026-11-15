"""Frozen financial feature cohorts and all annual task-fold qualification records."""
import pandas as pd
from common import *
from train_r02 import target,train_masks
from versioned_observations import digest_json
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']
K=KEY+['date']
def run():
    out=ROOT/'outputs/r121';out.mkdir(exist_ok=True)
    paths=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'data/r54_market_controls.parquet',ROOT/'outputs/r120/industry_changes.parquet']
    p=pd.concat([pd.read_parquet(x) for x in paths[:2]],ignore_index=True);p['log_members']=np.log(p.members)
    p=p.merge(pd.read_parquet(paths[2])[K+['size_control']],on=K,how='left',validate='one_to_one').merge(pd.read_parquet(paths[3])[K+['market_beta126','residual_vol126']],on=K,how='left',validate='one_to_one')
    f=pd.read_parquet(paths[4]);p=p.drop(columns=[c for c in p.columns if c in f.columns and c not in K])
    j=f.merge(p,on=K,how='left',validate='many_to_one')
    j['baseline_ready']=j.price_ready.eq(True)&np.isfinite(j[BASE]).all(axis=1)
    j['main80']=j.baseline_ready&j.status.eq('eligible_subset')&np.isfinite(j.mean_change)
    j['strict100']=j.main80&j.strict_complete.eq(True)
    j.to_parquet(out/'joined_panel.parquet',index=False)
    folds=[];targets=[];coverage=[]
    for (era,level,clock),base in j.groupby(['era','level','clock'],sort=True):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]].copy()
        for date,z in g.groupby('date'):coverage.append(dict(era=era,level=level,clock=clock,cohort=cohort,date=date,industries=len(z),nonzero_change=int(z.mean_change.ne(0).sum()),distinct_change=z.mean_change.nunique()))
        for task in ['return','onset','reversal']:
          for h in [20,60]:
            y,ok=target(g,task,h);q=g[ok].copy();q['y']=y[ok]
            t=q[K+['clock','mean_change','y',f'maturity{h}']].rename(columns={f'maturity{h}':'maturity'}).copy();t['cohort']=cohort;t['task']=task;t['horizon']=h;targets.append(t)
            for year in range(2020,2027):
                fit,cal,test=train_masks(q,year,h,task);tr=q[fit];ca=q[cal];te=q[test]
                train_minor=int(tr.y.value_counts().reindex([0.,1.],fill_value=0).min()) if task!='return' else None
                cal_minor=int(ca.y.value_counts().reindex([0.,1.],fill_value=0).min()) if task!='return' else None
                bad=dict(no_test_rows=te.empty,insufficient_train_months_or_rows=tr.date.nunique()<18 or len(tr)<300,insufficient_train_classes=task!='return' and train_minor<30,insufficient_calibration=task!='return' and (ca.date.nunique()<4 or len(ca)<100 or cal_minor<10))
                reason=next((k for k,v in bad.items() if v),'eligible')
                row=dict(era=era,level=level,clock=clock,cohort=cohort,task=task,horizon=h,year=year,status='eligible' if reason=='eligible' else 'skipped',reason=reason,**bad)
                for name,a in [('fit',tr),('cal',ca),('test',te)]:
                    row.update({f'n_{name}':len(a),f'{name}_months':a.date.nunique(),f'{name}_industries':a.industry_code.nunique(),f'{name}_max_maturity':a[f'maturity{h}'].max(),f'{name}_identity_sha256':digest_json(a[K].astype(str).to_dict('records'))})
                row.update(train_class_min=train_minor,cal_class_min=cal_minor,n_test_known=int(te.y.notna().sum()),n_test_unknown=int(te.y.isna().sum()))
                folds.append(row)
    ledger=pd.DataFrame(folds);assert len(ledger)==840
    ledger.to_csv(out/'fold_ledger.csv',index=False)
    pd.concat(targets,ignore_index=True).to_parquet(out/'task_membership.parquet',index=False)
    pd.DataFrame(coverage).to_csv(out/'cross_section_counts.csv',index=False)
    j.groupby(['era','level','clock']).agg(rows=('date','size'),baseline=('baseline_ready','sum'),main80=('main80','sum'),strict100=('strict100','sum')).reset_index().to_csv(out/'coverage.csv',index=False)
    ledger.groupby(['era','level','clock','cohort','task','status','reason']).size().rename('folds').reset_index().to_csv(out/'summary.csv',index=False)
    paths +=[Path(__file__),ROOT/'protocols/r121.json',ROOT/'src/train_r02.py',ROOT/'src/common.py',ROOT/'src/versioned_observations.py']
    names=['joined_panel.parquet','fold_ledger.csv','task_membership.parquet','cross_section_counts.csv','coverage.csv','summary.csv']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={n:sha(out/n) for n in names},folds=len(ledger),eligible=int(ledger.status.eq('eligible').sum()),joined_rows=len(j),target_rows=sum(len(x) for x in targets),model_fitted=False))
    print(ledger[ledger.status.eq('eligible')][['era','level','clock','cohort','task','horizon','year','n_fit','n_test']].to_string(index=False));print(ledger.reason.value_counts().to_string())
if __name__=='__main__':run()
