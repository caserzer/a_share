"""Rebuild labels and audit all original R02 cohorts without refitting."""
import pandas as pd
from common import *
from build_panel import price_features,delayed_labels
from train_r02 import F,EXTRA,target,train_masks
from inference_bundle_r101 import INPUT

LABELS=['entry_date']+[f'{c}{h}' for h in [20,60] for c in ['maturity','return','market_return','excess','rel_trough']]
KEYS=KEY+['date']


def payload_diff(a,b,columns):
    a=a.set_index(KEYS).sort_index();b=b.set_index(KEYS).sort_index();ix=a.index.intersection(b.index)
    changed={};mask=np.zeros(len(ix),bool)
    for c in columns:
        av=a.loc[ix,c];bv=b.loc[ix,c]
        if pd.api.types.is_datetime64_any_dtype(av):bad=~(av.eq(bv)|(av.isna()&bv.isna())).to_numpy()
        else:bad=~np.isclose(av.to_numpy(float),bv.to_numpy(float),rtol=1e-12,atol=1e-12,equal_nan=True)
        changed[c]=int(bad.sum());mask|=bad
    return dict(old_rows=len(a),new_rows=len(b),added=len(b.index.difference(a.index)),removed=len(a.index.difference(b.index)),changed_common=int(mask.sum()),fields=changed)


def gate(q,year,h,task):
    masks=train_masks(q,year,h,task);tr,ca,te=[q[x] for x in masks]
    reason=''
    if not len(te):reason='no_test'
    elif tr.date.nunique()<18 or len(tr)<300:reason='insufficient_train_months_or_rows'
    elif task!='return':
        if tr.y.value_counts().reindex([0.,1.],fill_value=0).min()<30:reason='insufficient_train_classes'
        elif ca.date.nunique()<4 or len(ca)<100 or ca.y.value_counts().reindex([0.,1.],fill_value=0).min()<10:reason='insufficient_calibration'
    rec=dict(n_fit=len(tr),n_cal=len(ca),n_test=len(te),train_months=tr.date.nunique(),cal_months=ca.date.nunique(),fit_max_maturity=tr[f'maturity{h}'].max(),cal_max_maturity=ca[f'maturity{h}'].max(),status='fit' if not reason else 'skipped',reason=reason)
    return rec,(tr,ca,te)


def audit_folds(old,new):
    ledgers=[];deltas=[]
    for p in [old,new]:p['log_members']=np.log(p.members.where(p.members.gt(0)))
    for era,level in sorted(set(map(tuple,old[['era','level']].to_numpy()))|set(map(tuple,new[['era','level']].to_numpy()))):
      for cohort,ext in EXTRA.items():
        columns=F+ext;prepared=[]
        for p in [old,new]:
            g=p[p.era.eq(era)&p.level.eq(level)&p.price_ready].dropna(subset=columns).copy()
            ranks=g.groupby('date')[columns].transform(centered_rank)
            for c in columns:g['rank_'+c]=ranks[c]
            prepared.append(g)
        for task in ['return','onset','reversal']:
          for h in [20,60]:
            qs=[]
            for g in prepared:
                y,eligible=target(g,task,h);q=g[eligible].copy();q['y']=y[eligible];qs.append(q)
            for year in range(2020,2027):
                ident=dict(era=era,level=level,cohort=cohort,task=task,horizon=h,year=year)
                a,roles_a=gate(qs[0],year,h,task);b,roles_b=gate(qs[1],year,h,task)
                for side,rec in [('old',a),('new',b)]:ledgers.append(dict(ident,version=side,**rec))
                for role,ra,rb in zip(['fit','cal','test'],roles_a,roles_b):
                    diff=payload_diff(ra,rb,['y',f'maturity{h}','entry_date']+['rank_'+c for c in columns])
                    deltas.append(dict(ident,role=role,old_status=a['status'],new_status=b['status'],**diff))
        print('FOLDS',era,level,cohort,flush=True)
    return pd.DataFrame(ledgers),deltas


def run():
    out=ROOT/'outputs/r130';out.mkdir(exist_ok=True)
    dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';ep=CACHE/'joint_pe_v35/daily_expansion.parquet';op=ROOT/'data/monthly_panel.parquet'
    d=pd.read_parquet(dp);market=pd.read_parquet(bp).close;calendar=pd.Series(market.index,index=market.index);ends=calendar.groupby(calendar.index.to_period('M')).max();ends=ends[[p.end_time.normalize()<=market.index.max() for p in ends.index]]
    pieces=[]
    for _,g in d.groupby(KEY+['block'],sort=False):
        f=delayed_labels(price_features(g),market);pieces.append(f[f.date.isin(ends.values)])
    p=pd.concat(pieces,ignore_index=True);p['price_ready']=p[['mom20','mom60','vol20','dd60']].notna().all(axis=1)&p.coverage.ge(.8)&p.members.ge(5)
    fields=['turn_rank504','pe_rank504','pe_known_fraction','pe_positive_fraction'];e=pd.read_parquet(ep,columns=KEYS+fields)
    p=p.merge(e,on=KEYS,how='left',validate='one_to_one').sort_values(KEYS).reset_index(drop=True);p['year']=p.date.dt.year
    pp=out/'monthly_panel.parquet';p.to_parquet(pp,index=False)
    old=pd.read_parquet(op);labeldiff=payload_diff(old,p,LABELS)
    # Full row-level outer ledger distinguishes new synthetic origins from changed existing outcomes.
    pair=old[KEYS+LABELS+['price_ready']].merge(p[KEYS+LABELS+['price_ready']],on=KEYS,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
    pair.to_parquet(out/'label_pairs.parquet',index=False)
    ledger,deltas=audit_folds(old,p);ledger.to_csv(out/'fold_ledger.csv',index=False);js(out/'fold_payload_deltas.json',deltas)
    reads={str(x):sha(x) for x in [dp,bp,ep,op,Path(__file__),ROOT/'src/build_panel.py',ROOT/'src/train_r02.py',ROOT/'src/common.py',ROOT/'protocols/r130.json']}
    affected=[x for x in deltas if x['added'] or x['removed'] or x['changed_common']]
    js(out/'receipt.json',dict(reads=reads,panel_sha256=sha(pp),rows=len(p),price_ready=int(p.price_ready.sum()),label_diff=labeldiff,folds_per_version=len(ledger)//2,affected_roles=len(affected),status_changes=int(ledger.pivot(index=['era','level','cohort','task','horizon','year'],columns='version',values='status').eval('old != new').sum()),quality='Historical-proxy; no retraining'))
    print('DONE',len(p),'affected roles',len(affected),flush=True)

if __name__=='__main__':run()
