"""Direct endpoint/trough checks and independent original-fold reconstruction."""
import pandas as pd
from common import *
from inference_bundle_r101 import INPUT
from train_r02 import F,EXTRA

KEYS=KEY+['date'];FK=['era','level','cohort','task','horizon','year']


def prepared(panel,era,level,cohort,task,h):
    cols=F+EXTRA[cohort];p=panel.copy();p['log_members']=np.log(p.members.where(p.members.gt(0)))
    q=p[p.era.eq(era)&p.level.eq(level)&p.price_ready].dropna(subset=cols).copy()
    for c in cols:
        groups=q.groupby('date')[c];q['rank_'+c]=(groups.rank(method='average')-.5)/groups.transform('count')-.5
    if task=='return':q['y']=q[f'excess{h}']
    elif task=='onset':
        q=q[q.past_excess20<=0];q['y']=((q[f'return{h}']>=(.05 if h==20 else .10))&(q[f'excess{h}']>=(.03 if h==20 else .05))).astype(float).where(q[f'excess{h}'].notna())
    else:
        q=q[(q.past_excess60>0)&(q.mom60>0)];q['y']=(q[f'rel_trough{h}']<=(-.08 if h==20 else -.12)).astype(float).where(q[f'excess{h}'].notna()&q[f'rel_trough{h}'].notna())
    return q,cols


def run():
    out=ROOT/'outputs/r130';receipt=json.loads((out/'receipt.json').read_text())
    for p,digest in receipt['reads'].items():assert sha(p)==digest,p
    pp=out/'monthly_panel.parquet';assert sha(pp)==receipt['panel_sha256'];panel=pd.read_parquet(pp)
    ref_features=pd.read_parquet(ROOT/'outputs/r129/features_2026-10-21.parquet');pd.testing.assert_frame_equal(panel[INPUT],ref_features,check_exact=False,atol=1e-12,rtol=1e-12)
    daily=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
    pg=panel.groupby(KEY+['block']);checks=0
    for key,g in daily.groupby(KEY+['block']):
        if key not in pg.groups:continue
        g=g.sort_values('date');dates=pd.DatetimeIndex(g.date);assert np.all(np.diff(market.index.get_indexer(dates))==1)
        nav=g.nav.to_numpy(float);bm=market.reindex(dates).to_numpy(float);relative=nav/bm
        for row in pg.get_group(key).to_dict('records'):
            i=dates.get_loc(row['date']);entry=dates[i+1] if i+1<len(g) else pd.NaT
            assert (pd.isna(entry) and pd.isna(row['entry_date'])) or entry==row['entry_date']
            for h in [20,60]:
                j=i+h+1;known=j<len(g);maturity=dates[j] if known else pd.NaT
                assert (pd.isna(maturity) and pd.isna(row[f'maturity{h}'])) or maturity==row[f'maturity{h}']
                ret=nav[j]/nav[i+1]-1 if known else np.nan;mr=bm[j]/bm[i+1]-1 if known else np.nan
                trough=min(relative[i+2:j+1])/relative[i+1]-1 if known else np.nan
                for name,value in [('return',ret),('market_return',mr),('excess',ret-mr),('rel_trough',trough)]:assert np.isclose(row[f'{name}{h}'],value,atol=1e-12,rtol=1e-12,equal_nan=True),(key,row['date'],name,h)
                checks+=1
    ledger=pd.read_csv(out/'fold_ledger.csv');baseline=pd.read_csv(ROOT/'outputs/r02/fold_ledger.csv');old=ledger[ledger.version.eq('old')&ledger.reason.ne('no_test')]
    cols=FK+['n_fit','n_cal','n_test','train_months','cal_months','status']
    pd.testing.assert_frame_equal(old[cols].sort_values(FK).reset_index(drop=True),baseline[cols].sort_values(FK).reset_index(drop=True))
    deltas=json.loads((out/'fold_payload_deltas.json').read_text());delta_map={tuple(x[k] for k in FK)+(x['role'],):x for x in deltas};panels={'old':pd.read_parquet(ROOT/'data/monthly_panel.parquet'),'new':panel};cache={};role_checks=0
    for key,records in ledger.groupby(FK):
        era,level,cohort,task,h,year=key;roles={}
        for side in ['old','new']:
            ck=(side,era,level,cohort,task,h)
            if ck not in cache:cache[ck]=prepared(panels[side],era,level,cohort,task,h)
            q,columns=cache[ck];jan=pd.Timestamp(year,1,1);jul=pd.Timestamp(year-1,7,1);known=q.y.notna()
            fit=(q.date<(jan if task=='return' else jul))&(q[f'maturity{h}']<(jan if task=='return' else jul))&known
            cal=pd.Series(False,index=q.index) if task=='return' else (q.date>=jul)&(q.date<jan)&(q[f'maturity{h}']<jan)&known
            test=q.date.dt.year.eq(year);parts=[q[fit],q[cal],q[test]];tr,ca,te=parts
            reason='no_test' if len(te)==0 else 'insufficient_train_months_or_rows' if len(tr)<300 or tr.date.nunique()<18 else ''
            if not reason and task!='return':
                if min(int(tr.y.eq(0).sum()),int(tr.y.eq(1).sum()))<30:reason='insufficient_train_classes'
                elif len(ca)<100 or ca.date.nunique()<4 or min(int(ca.y.eq(0).sum()),int(ca.y.eq(1).sum()))<10:reason='insufficient_calibration'
            rec=records[records.version.eq(side)].iloc[0];assert rec.status==('skipped' if reason else 'fit');assert ('' if pd.isna(rec.reason) else rec.reason)==reason
            assert [len(x) for x in parts]==[rec.n_fit,rec.n_cal,rec.n_test]
            roles[side]=parts
        for role,a,b in zip(['fit','cal','test'],roles['old'],roles['new']):
            x=delta_map[key+(role,)];a=a.set_index(KEYS);b=b.set_index(KEYS);common=a.index.intersection(b.index);union_bad=np.zeros(len(common),bool)
            assert x['added']==len(b.index.difference(a.index)) and x['removed']==len(a.index.difference(b.index))
            for c,n in x['fields'].items():
                av=a.loc[common,c];bv=b.loc[common,c]
                eq=(av.eq(bv)|(av.isna()&bv.isna())).to_numpy() if c in ['entry_date',f'maturity{h}'] else np.isclose(av.to_numpy(float),bv.to_numpy(float),rtol=1e-12,atol=1e-12,equal_nan=True)
                assert int((~eq).sum())==n;union_bad|=~eq
            assert int(union_bad.sum())==x['changed_common'];role_checks+=1
    js(out/'verification.json',dict(status='PASS',direct_outcome_checks=checks,baseline_ledger_rows=len(baseline),independent_fold_role_checks=role_checks,scope='All new monthly outcomes and all original R02 cohort/fold payload comparisons; no fit or metric recomputation'))
    print('PASS',checks,len(baseline),role_checks)

if __name__=='__main__':run()
