"""Independent cohort, target, gate, rank and penalized fit verification."""
import pandas as pd
from scipy.stats import rankdata
from scipy.special import expit
from common import *
from versioned_observations import digest_json
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63'];ALL=BASE+['leader_spread']
FK=['era','level','cohort','task','horizon','year']

def run():
    out=ROOT/'outputs/r109';receipt=json.loads((out/'receipt.json').read_text())
    for path,h in receipt['reads'].items():assert sha(path)==h
    for path,h in receipt['outputs'].items():assert sha(out/path)==h
    p=pd.read_parquet(out/'joined_panel.parquet');coverage=pd.read_parquet(out/'coverage.parquet');pred=pd.read_parquet(out/'predictions.parquet');folds=pd.read_csv(out/'fold_ledger.csv');models=json.loads((out/'model_parameters.json').read_text())
    original=pd.concat([pd.read_parquet(ROOT/f'data/{n}.parquet') for n in ['monthly_panel','l1_monthly_panel']],ignore_index=True)
    pd.testing.assert_frame_equal(p[list(original)],original)
    for path,cols in [(ROOT/'data/r30_size_control.parquet',['size_control']),(ROOT/'data/r54_market_controls.parquet',['market_beta126','residual_vol126']),(ROOT/'outputs/r108/industry_features.parquet',['leader_spread','strict_complete'])]:
        source=pd.read_parquet(path).set_index(KEY+['date']);selected=source.reindex(pd.MultiIndex.from_frame(p[KEY+['date']]))
        for col in cols:pd.testing.assert_series_equal(p[col].reset_index(drop=True),selected[col].reset_index(drop=True),check_names=False)
    np.testing.assert_allclose(p.log_members,np.log(p.members),equal_nan=True)
    base_ready=p.price_ready&np.isfinite(p[BASE]).all(axis=1);main=base_ready&np.isfinite(p.leader_spread);strict=main&p.strict_complete.eq(True)
    for col,flag in [('baseline_ready',base_ready),('main80',main),('strict100',strict)]:pd.testing.assert_series_equal(p[col],flag,check_names=False)
    source=pd.read_parquet(ROOT/'outputs/r108/industry_features.parquet')
    pd.testing.assert_frame_equal(coverage[KEY+['date','catalogue_identity','observed_panel_row','status']],source[KEY+['date','catalogue_identity','observed_panel_row','status']])
    selected=p.set_index(KEY+['date']).reindex(pd.MultiIndex.from_frame(source[KEY+['date']]))
    for col in ['baseline_ready','main80','strict100']:assert coverage[col].equals(selected[col].reset_index(drop=True).eq(True))
    fm={tuple(row[k] for k in FK):row for row in folds.to_dict('records')};mm={tuple(m[k] for k in FK)+(m['method'],):m for m in models}
    assert len(fm)==len(folds) and len(mm)==len(models)
    assert not pred.duplicated(KEY+['date','cohort','task','horizon','year','method']).any()
    visited=set();verified=0;maxgrad=0.;fitcount=0
    for (era,level),base in p.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]];ranks=pd.DataFrame(index=g.index,columns=ALL,dtype=float)
        for _,v in g.groupby('date'):
            for c in ALL:ranks.loc[v.index,c]=(rankdata(v[c],method='average')-.5)/len(v)-.5
        for task in ['return','onset','reversal']:
          for h in [20,60]:
            valid=g[f'excess{h}'].notna()
            if task=='return':y=g[f'excess{h}'];eligible=pd.Series(True,index=g.index)
            elif task=='onset':y=((g[f'return{h}']>=(.05 if h==20 else .10))&(g[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(valid);eligible=g.past_excess20.le(0)
            else:y=g[f'rel_trough{h}'].le(-.08 if h==20 else -.12).astype(float).where(valid&g[f'rel_trough{h}'].notna());eligible=g.past_excess60.gt(0)&g.mom60.gt(0)
            q=g[eligible].copy();q['y']=y[eligible]
            for year in range(2020,2027):
              te=q[q.date.dt.year.eq(year)]
              if te.empty:continue
              key=(era,level,cohort,task,h,year);visited.add(key);rec=fm[key];boundary=pd.Timestamp(year,1,1);calstart=pd.Timestamp(year-1,7,1);fitend=boundary if task=='return' else calstart
              tr=q[q.date.lt(fitend)&q[f'maturity{h}'].lt(fitend)&q.y.notna()];ca=q.iloc[:0] if task=='return' else q[q.date.ge(calstart)&q.date.lt(boundary)&q[f'maturity{h}'].lt(boundary)&q.y.notna()]
              assert (len(tr),len(ca),len(te),tr.date.nunique(),ca.date.nunique())==(rec['n_fit'],rec['n_cal'],rec['n_test'],rec['train_months'],rec['cal_months'])
              for part,name in [(tr,'fit'),(ca,'cal')]:assert digest_json(part[KEY+['date']].astype(str).to_dict('records'))==rec[name+'_identity_sha256']
              reason=None
              if len(tr)<300 or tr.date.nunique()<18:reason='insufficient_train_months_or_rows'
              elif task!='return':
                if tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='insufficient_train_classes'
                elif len(ca)<100 or ca.date.nunique()<4 or ca.y.value_counts().reindex([0.,1.],fill_value=0).min()<10:reason='insufficient_calibration'
              actual=pred
              for col,value in zip(FK,key):actual=actual[actual[col].eq(value)]
              if reason:
                assert rec['status']=='skipped' and rec['reason']==reason and actual.empty and key+('controls',) not in mm and key+('with_leader',) not in mm;continue
              assert rec['status']=='fit';fitcount+=1
              for method,cols in [('controls',BASE),('with_leader',ALL)]:
                m=mm[key+(method,)];assert m['columns']==cols
                mean=ranks.loc[tr.index,cols].mean().to_numpy();scale=ranks.loc[tr.index,cols].std(ddof=0).to_numpy();scale=np.where(scale==0,1,scale)
                np.testing.assert_allclose(m['scaler_mean'],mean,atol=1e-14);np.testing.assert_allclose(m['scaler_scale'],scale,atol=1e-14)
                x=(ranks.loc[tr.index,cols].to_numpy()-mean)/scale;xt=(ranks.loc[te.index,cols].to_numpy()-mean)/scale;beta=np.asarray(m['coefficient']).ravel();intercept=np.asarray(m['intercept']).item();w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy())
                error=(x@beta+intercept if task=='return' else expit(x@beta+intercept))-tr.y.to_numpy()
                grad=np.r_[x.T@(w*error)+(10 if task=='return' else 1)*beta,np.sum(w*error)]/len(tr);maxgrad=max(maxgrad,float(abs(grad).max()));assert abs(grad).max()<1e-6
                decision=xt@beta+intercept
                if task=='return':value=decision
                else:
                    xc=(ranks.loc[ca.index,cols].to_numpy()-mean)/scale;ds=xc@beta+intercept;a=np.asarray(m['calibration_coefficient']).item();b=np.asarray(m['calibration_intercept']).item();wc=len(ca)/(ca.date.nunique()*ca.groupby('date').date.transform('size').to_numpy());e=expit(ds*a+b)-ca.y.to_numpy();grad=np.array([np.sum(wc*e*ds)+a,np.sum(wc*e)])/len(ca);maxgrad=max(maxgrad,float(abs(grad).max()));assert abs(grad).max()<1e-6;value=expit(decision*a+b)
                expected=te[KEY+['date','entry_date','y','strict_complete',f'maturity{h}',f'excess{h}']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'excess'}).copy();expected['prediction']=value;expected['decision']=decision
                got=actual[actual.method.eq(method)][list(expected)].sort_values(KEY+['date']).reset_index(drop=True);expected=expected.sort_values(KEY+['date']).reset_index(drop=True)
                pd.testing.assert_frame_equal(got,expected,check_exact=False,atol=1e-12,rtol=1e-12);verified+=len(got)
    assert visited==set(fm) and len(models)==2*fitcount and verified==len(pred)
    js(out/'model_verification.json',dict(status='PASS',folds=len(folds),fit_folds=fitcount,skipped_folds=len(folds)-fitcount,models=len(models),prediction_rows=len(pred),max_normalized_gradient=maxgrad,adopted=False));print('PASS models',len(models),'predictions',len(pred),'max gradient',maxgrad)

if __name__=='__main__':run()
