from ep41inputs import *
import json
from fit import metrics
from collections import Counter
from scipy.stats import rankdata

def monthly(daily):
    rows=[];segments=[]
    for (arm,h,seg),g in daily.groupby(['arm','hold','segment']):
        g=g.sort_values('date').copy()
        assert g.date.is_unique
        g['prev']=g.nav.shift(fill_value=1.)
        np.testing.assert_allclose(g.nav-g.prev,g.gross_pnl-g.fee,atol=1e-12)
        for month,frame in g.groupby(g.date.dt.to_period('M')):
            if month in [g.date.iloc[0].to_period('M'),g.date.iloc[-1].to_period('M')]:continue
            start=frame.prev.iloc[0]
            rows.append((arm,h,seg,str(month),frame.nav.iloc[-1]/start-1,frame.fee.sum()/start,frame.gross_pnl.sum()/start,frame.buy.sum()/start,frame.sell.sum()/start))
        segments.append((arm,h,seg,g.nav.iloc[-1]-1,(g.nav/g.nav.cummax().clip(lower=1)-1).min(),g.fee.sum(),g.cash.mean()))
    m=pd.DataFrame(rows,columns='arm hold segment month net fee gross buy sell'.split())
    ref=m.query("arm=='R' and hold==10")[['segment','month','net']].rename(columns={'net':'base_net'})
    m=m.merge(ref,on=['segment','month'],validate='m:1');m['gap_bp']=(m.net-m.base_net)*10000
    m.to_csv(OUT/'complete_months.csv',index=False)
    g=m.groupby(['arm','hold','segment'])
    result=g.agg(months=('month','size'),bp_vs_R=('gap_bp','mean'),positive=('gap_bp',lambda x:(x>0).sum()),ex_best3=('gap_bp',lambda x:x.sort_values().iloc[:-3].mean())).reset_index()
    result.merge(pd.DataFrame(segments,columns='arm hold segment return_net max_dd fees cash_mean'.split()),on=['arm','hold','segment']).to_csv(OUT/'model_accounts.csv',index=False)
    return m

def equiv():
    d=pd.read_parquet(CACHE/'panel.parquet');global_rank=pd.read_parquet(CACHE/'global.parquet');ind_rank=pd.read_parquet(CACHE/'industry.parquet')
    pairs=[('mom1','ret_lag0')]+[(f'xsret_lag{i}',f'ret_lag{i}') for i in range(20)]
    rows=[]
    for r,groups,rep in [('global',[d.signal_date],global_rank),('industry',[d.signal_date,d.l1_name],ind_rank)]:
        for a,b in pairs:
            both=d[a].notna()&d[b].notna()
            shared=pct(d.loc[both,[a,b]],[z[both] for z in groups])
            rows.append((r,a,b,len(d),both.sum(),(d[a].isna()!=d[b].isna()).sum(),(shared[a]-shared[b]).abs().max(),(rep[a]-rep[b]).abs().max()))
    pd.DataFrame(rows,columns='input a b rows common unmatched_masks common_rank_max actual_rank_max'.split()).to_csv(OUT/'rank_equivalence.csv',index=False)
    return d

def oos(d):
    scores=pd.concat([pd.read_parquet(p) for p in sorted(CACHE.glob('*_pred.parquet'))]).sort_values(KEY)
    assert not scores.duplicated(KEY).any()
    # Save enough columns to regenerate every list, including cuts tested only in account sensitivities.
    scores.to_parquet(OUT/'quarterly_scores.parquet',index=False,compression='zstd')
    check=scores.merge(pd.concat([pd.read_parquet(p,columns=KEY+['T69']) for p in (ep.DEST/'folds').glob('*.parquet')]),on=KEY,validate='1:1')
    np.testing.assert_allclose(check.M1_raw,check.T69,atol=1e-10,rtol=0)
    scores['y']=pct(scores.h10,scores.signal_date)
    rows=[]
    for day,g in scores.groupby('signal_date'):
        k=len(g)//10;r=g.R;y=g.y
        for col in ['M2_global_res','M2_raw_res']:
            e=g[col]-r;final=g[col]
            rows.append((day,col,y.std(),r.std(),(y-r).std(),e.std(),e.std()/r.std(),r.cov(e),
                        y.corr(y-r),r.corr(e),r.corr(final,method='spearman'),e.corr(final,method='spearman'),
                        len(set(final.nlargest(k).index)&set(r.nlargest(k).index))/k,
                        len(set(final.nlargest(k).index)&set(e.nlargest(k).index))/k,
                        ((y-r)**2).mean()-((y-final)**2).mean()))
    pd.DataFrame(rows,columns='date arm sd_y sd_R sd_residual sd_e sd_ratio cov_R_e corr_y_residual corr_R_e rank_R_final rank_e_final top_R_overlap top_e_overlap mse_gain'.split()).to_csv(OUT/'residual_diagnostics.csv',index=False)
    oof=pd.read_parquet(OUT/'weekly_oof.parquet');oof=oof[oof.in_core]
    v=[];splits=[];valid=[]
    for f in sorted(OUT.glob('*_fold.json')):
        a=json.loads(f.read_text());q=pd.Period(a['fold']);c=q.start_time
        for model,metrics_ in a['veto_metrics'].items():
            v.append((str(q),model,a['events'],a['non_events'],*metrics_,a['veto']))
        for arm,tree in a['trees'].items():
            vals=pd.DataFrame(tree['splits'],columns=['column','threshold'])
            for col,group in vals.groupby('column'):
                splits.append((str(q),arm,col,len(group),tree['n'],group.threshold.min(),group.threshold.median(),group.threshold.max()))
        valid.append((str(q),a['train_rows'],a['train_weeks'],a['common_rows'],a['common_weeks'],a['first_oof'],a['max_maturity'],a['outer_start'],a['joint_rows'],a['joint_latest']))
    pd.DataFrame(v,columns='quarter model events non_events auc brier ece challenger_pass'.split()).to_csv(OUT/'veto_gates.csv',index=False)
    pd.DataFrame(splits,columns='quarter arm feature split_count trees min_threshold median_threshold max_threshold'.split()).to_csv(OUT/'tree_splits.csv',index=False)
    pd.DataFrame(valid,columns='quarter train_rows train_weeks shared_rows shared_weeks first_oof latest_mature first_scored three_horizon_rows latest_h20'.split()).to_csv(OUT/'fold_coverage.csv',index=False)
    event=d[d.outer].groupby(d.loc[d.outer,'signal_date'].dt.year)[['event','event_direct']].agg(['mean','count'])
    event.to_csv(OUT/'left_tail_labels.csv')
    return len(check)

def compare(daily):
    checks={}
    for arm,ref,filename in [('R','R','stagger'),('M1_raw','X1169','market_challenge_stagger'),('top_M1_raw','T69','market_challenge_stagger')]:
        prior=pd.read_parquet(ep.DEST/(filename+'.parquet'))
        if 'netting' in prior:prior=prior[prior.netting]
        prior=prior[prior.arm==ref].rename(columns={'scope':'segment'})
        g=daily[daily.arm.eq(arm)].merge(prior,on=['segment','date'],validate='1:1',suffixes=('','_ref'))
        assert len(g)==len(prior)>0
        for key in ['nav','fee','cash','crossed']:
            err=(g[key]-g[key+'_ref']).abs().max()
            assert err<1e-9,(arm,key,err)
            checks[arm+'_'+key]=err
    return checks

if __name__=='__main__':
    daily=pd.read_parquet(OUT/'funded_daily.parquet');checks=compare(daily)
    m=monthly(daily);panel=equiv();checks['frozen_69_scores_checked']=oos(panel)
    (OUT/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
