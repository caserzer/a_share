"""All catalog dates: evaluator readiness, not generated alerts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP, sha
from post_alert_evaluation import registered_rules,post_alert_result,label_neighborhood_known


def main():
    source=EP/'outputs/r00_coverage/evaluation_coverage.parquet'
    q=pd.read_parquet(source).sort_values(['era','industry_code','date']).reset_index(drop=True)
    asof=int(q.day_i.max());c=registered_rules()
    out=q[['era','industry_code','date','day_i','status','no_price_identity']].rename(columns={'status':'price_status'}).copy()
    out['post_status']='UNKNOWN_PRICE_PATH';out['label_neighborhood_known']=False
    out['calendar_mature']=asof-out.day_i>=c['uniform_alert_label_delay_sessions']
    era_last=out.groupby('era').day_i.transform('max')
    out['crosses_classification_boundary']=out.era.eq('SW2014')&(out.day_i+c['post_alert_horizon']>era_last)
    out.loc[out.day_i+c['post_alert_horizon']>era_last,'post_status']='UNKNOWN_MISSING_DATES'
    metrics=['peak_return','terminal_return','retained_days','floor_return','max_drawdown']
    for name in metrics:out[name]=np.nan
    for _,g in q[q.nav.notna()].groupby(['era','industry_code','block'],sort=True):
        g=g.sort_values('day_i');idx=g.index.to_numpy();prices=g.nav.to_numpy(float);n=len(g)
        assert np.all(np.diff(g.day_i)==1)
        if n>=61:
            w=np.lib.stride_tricks.sliding_window_view(prices,61);f=w[:,1:]/w[:,[0]]-1
            v=dict(peak_return=f[:,:20].max(axis=1),terminal_return=f[:,-1],retained_days=(f>=.02).sum(axis=1),
                   floor_return=f.min(axis=1),max_drawdown=(w/np.maximum.accumulate(w,axis=1)-1).min(axis=1))
            passed=(v['peak_return']>=c['post_alert_peak_min_return'])&(v['terminal_return']>=c['post_alert_terminal_min_return'])
            passed&=(v['retained_days']>=c['post_alert_retained_min_days'])&(v['floor_return']>=c['post_alert_floor_return'])&(v['max_drawdown']>=-c['post_alert_max_drawdown'])
            selected=idx[:len(w)]
            out.loc[selected,'post_status']=np.where(passed,'POST_VALID','POST_FAILED')
            for name in metrics:out.loc[selected,name]=v[name]
        # Exact support for all potential origins [t-10,t+5], each with +/-60.
        if n>=136:out.loc[idx[70:n-65],'label_neighborhood_known']=True
    out.loc[~out.calendar_mature,'post_status']='IMMATURE'
    out.loc[~out.calendar_mature,'label_neighborhood_known']=False
    out.loc[~out.calendar_mature,metrics]=np.nan
    assert len(out)==len(q) and not out.duplicated(['era','industry_code','date']).any()
    groups={k:g for k,g in q.groupby(['era','industry_code'])};checks=0
    for _,s in out.groupby(['post_status','label_neighborhood_known']):
        for r in s.sample(min(40,len(s)),random_state=3405).itertuples():
            g=groups[(r.era,r.industry_code)]
            b=g.block.to_numpy(dtype=float,na_value=np.nan)
            ref=post_alert_result(g.day_i.to_numpy(),g.nav.to_numpy(),b,r.day_i,asof)
            # Missing date rows are explicitly present in the full grid; block ends are unknown paths.
            assert ref['status']==r.post_status,(ref,r)
            assert label_neighborhood_known(g.day_i.to_numpy(),g.nav.to_numpy(),b,r.day_i,asof)==r.label_neighborhood_known
            if ref['status'] in ['POST_VALID','POST_FAILED']:
                for name in metrics:assert np.isclose(ref[name],getattr(r,name))
            checks+=1
    folder=EP/'outputs/r00_evaluation_support';folder.mkdir(exist_ok=True)
    out.to_parquet(folder/'all_catalog_dates.parquet',index=False)
    annual=[dict(era=era,year=int(year),rows=len(g),post_status=g.post_status.value_counts().to_dict(),label_neighborhood_known=int(g.label_neighborhood_known.sum())) for (era,year),g in out.groupby(['era',out.date.dt.year])]
    result=dict(status='EVALUATOR_SUPPORT_ONLY_NOT_SIGNAL_RESULTS',rows=len(out),asof_day=asof,asof_date=str(q.date.max().date()),
                post_status=out.post_status.value_counts().to_dict(),label_neighborhood_known=int(out.label_neighborhood_known.sum()),
                direct_sample_checks=checks,annual=annual,
                inputs={str(f):sha(f) for f in [source,EP/'configs/evaluation_registration.json',EP/'src/post_alert_evaluation.py',Path(__file__)]},
                output_sha256=sha(folder/'all_catalog_dates.parquet'))
    (folder/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['rows','post_status','label_neighborhood_known','direct_sample_checks']},ensure_ascii=False))


if __name__=='__main__':main()
