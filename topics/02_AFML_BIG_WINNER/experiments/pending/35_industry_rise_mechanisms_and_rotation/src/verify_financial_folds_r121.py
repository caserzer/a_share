"""Independent frozen-source, label, maturity and all840 fold reconstruction."""
import pandas as pd
from common import *
from versioned_observations import digest_json
K=KEY+['date']
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']
def run():
    out=ROOT/'outputs/r121';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    j=pd.read_parquet(out/'joined_panel.parquet');f=pd.read_parquet(ROOT/'outputs/r120/industry_changes.parquet')
    pd.testing.assert_frame_equal(j[f.columns],f)
    raw=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True)
    raw['log_members']=np.log(raw.members)
    raw=raw.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet')[K+['size_control']],on=K,how='left',validate='one_to_one').merge(pd.read_parquet(ROOT/'data/r54_market_controls.parquet')[K+['market_beta126','residual_vol126']],on=K,how='left',validate='one_to_one')
    cols=[c for c in raw.columns if c not in f.columns or c in K]
    expected=f[K].merge(raw[cols],on=K,how='left',validate='many_to_one')
    pd.testing.assert_frame_equal(j[expected.columns],expected)
    ready=j.price_ready.eq(True)&np.isfinite(j[BASE]).all(axis=1);main=ready&f.status.eq('eligible_subset')&np.isfinite(f.mean_change)
    assert ready.equals(j.baseline_ready) and main.equals(j.main80) and (main&f.strict_complete.eq(True)).equals(j.strict100)
    records=[];targets=[];cross=[]
    for (era,level,clock),base in j.groupby(['era','level','clock'],sort=True):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]]
        for date,z in g.groupby('date'):cross.append(dict(era=era,level=level,clock=clock,cohort=cohort,date=date,industries=len(z),nonzero_change=int(z.mean_change.ne(0).sum()),distinct_change=z.mean_change.nunique()))
        for task in ['return','onset','reversal']:
          for h in [20,60]:
            if task=='return':ok=pd.Series(True,index=g.index);y=g[f'excess{h}']
            elif task=='onset':
                ok=g.past_excess20<=0
                y=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(g[f'excess{h}'].notna())
            else:
                ok=(g.past_excess60>0)&(g.mom60>0)
                y=(g[f'rel_trough{h}']<=(-.08 if h==20 else -.12)).astype(float).where(g[f'excess{h}'].notna()&g[f'rel_trough{h}'].notna())
            q=g.loc[ok].copy();q['y']=y.loc[ok]
            t=q[K+['clock','mean_change','y',f'maturity{h}']].rename(columns={f'maturity{h}':'maturity'}).copy();t['cohort']=cohort;t['task']=task;t['horizon']=h;targets.append(t)
            for year in range(2020,2027):
                start=pd.Timestamp(year,1,1);half=pd.Timestamp(year-1,7,1);m=q[f'maturity{h}'];known=q.y.notna()
                fit=known&(m<(start if task=='return' else half))&(q.date<(start if task=='return' else half))
                cal=known&(m<start)&(q.date>=half)&(q.date<start) if task!='return' else pd.Series(False,index=q.index)
                tr,ca,te=q[fit],q[cal],q[q.date.dt.year==year]
                a=min(int(tr.y.eq(0).sum()),int(tr.y.eq(1).sum())) if task!='return' else None
                b=min(int(ca.y.eq(0).sum()),int(ca.y.eq(1).sum())) if task!='return' else None
                flags=dict(no_test_rows=len(te)==0,insufficient_train_months_or_rows=len(tr)<300 or tr.date.nunique()<18,insufficient_train_classes=task!='return' and a<30,insufficient_calibration=task!='return' and (len(ca)<100 or ca.date.nunique()<4 or b<10))
                reason=next((k for k,v in flags.items() if v),'eligible')
                z=dict(era=era,level=level,clock=clock,cohort=cohort,task=task,horizon=h,year=year,status='eligible' if reason=='eligible' else 'skipped',reason=reason,**flags)
                for name,part in [('fit',tr),('cal',ca),('test',te)]:
                    z.update({f'n_{name}':len(part),f'{name}_months':part.date.nunique(),f'{name}_industries':part.industry_code.nunique(),f'{name}_max_maturity':part[f'maturity{h}'].max(),f'{name}_identity_sha256':digest_json(part[K].astype(str).to_dict('records'))})
                z.update(train_class_min=a,cal_class_min=b,n_test_known=int(te.y.notna().sum()),n_test_unknown=int(te.y.isna().sum()));records.append(z)
    ledger=pd.DataFrame(records);actual=pd.read_csv(out/'fold_ledger.csv',parse_dates=['fit_max_maturity','cal_max_maturity','test_max_maturity'])
    pd.testing.assert_frame_equal(actual,ledger,check_dtype=False)
    assert len(ledger)==840 and not ledger.duplicated(['era','level','clock','cohort','task','horizon','year']).any()
    pd.testing.assert_frame_equal(pd.read_parquet(out/'task_membership.parquet'),pd.concat(targets,ignore_index=True))
    pd.testing.assert_frame_equal(pd.read_csv(out/'cross_section_counts.csv',parse_dates=['date']),pd.DataFrame(cross),check_dtype=False)
    cov=j.groupby(['era','level','clock']).agg(rows=('date','size'),baseline=('baseline_ready','sum'),main80=('main80','sum'),strict100=('strict100','sum')).reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(out/'coverage.csv'),cov,check_dtype=False)
    summary=ledger.groupby(['era','level','clock','cohort','task','status','reason']).size().rename('folds').reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(out/'summary.csv'),summary,check_dtype=False)
    js(out/'verification.json',dict(status='PASS',joined_rows=len(j),folds=len(ledger),eligible=int(ledger.status.eq('eligible').sum()),skipped=int(ledger.status.eq('skipped').sum()),target_rows=sum(map(len,targets)),model_fitted=False,strict_PIT=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
