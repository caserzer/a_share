"""Feature-only R54 rebuild with repaired L2/L3 and unchanged L1."""
import pandas as pd
from common import *
from market_controls_r54 import features
from train_r02 import F
from label_fold_audit_r130 import payload_diff
K=KEY+['date'];M=['market_beta126','residual_vol126'];D=['breadth21','breadth63'];C=F+['size_control']+M+D


def cohort(controls,monthly_paths):
    breadth=pd.concat([pd.read_parquet(p,columns=K+D) for p in monthly_paths],ignore_index=True)
    p=controls.merge(breadth,on=K,how='left',validate='one_to_one');p=p[p.price_ready].dropna(subset=C).copy()
    ranks=p.groupby(['era','level','date'])[C].transform(centered_rank)
    for c in C:p['rank_'+c]=ranks[c]
    return p


def run():
    out=ROOT/'outputs/r133';dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';l1d=ROOT/'data/l1_daily.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';mp=ROOT/'outputs/r130/monthly_panel.parquet';l1m=ROOT/'data/l1_monthly_panel.parquet';size=ROOT/'data/r30_size_control.parquet';oldp=ROOT/'data/r54_market_controls.parquet'
    market=pd.read_parquet(bp,columns=['close']).close
    cols=K+['price_ready','members']+F[:-1];monthly=pd.concat([pd.read_parquet(p,columns=cols) for p in [mp,l1m]],ignore_index=True);monthly['log_members']=np.log(monthly.members)
    dates=set(monthly.date);parts=[]
    for p in [dp,l1d]:
        d=pd.read_parquet(p,columns=K+['block','nav'])
        for _,g in d.groupby(KEY+['block'],sort=False):
            x=features(g,market);parts.append(x[x.date.isin(dates)][K+['block']+M+['paired_returns126']])
    calculated=pd.concat(parts,ignore_index=True);assert not calculated.duplicated(K).any()
    p=monthly.merge(calculated,on=K,how='left',validate='one_to_one').merge(pd.read_parquet(size,columns=K+['size_control']),on=K,how='left',validate='one_to_one')
    p['price_complete']=p.price_ready&p[F].notna().all(axis=1);p['market_controls_complete']=p[M].notna().all(axis=1);p['joint_complete']=p.price_complete&p.market_controls_complete&p.size_control.notna();p=p.sort_values(K).reset_index(drop=True)
    dest=out/'market_controls.parquet';p.to_parquet(dest,index=False);old=pd.read_parquet(oldp)
    fields=M+['paired_returns126','price_complete','market_controls_complete','joint_complete'];diff=payload_diff(old,p,fields)
    old.merge(p,on=K,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one').to_parquet(out/'control_pairs.parquet',index=False)
    a=cohort(old,[ROOT/'data/monthly_panel.parquet',l1m]);b=cohort(p,[mp,l1m]);a.to_parquet(out/'cohort_old.parquet',index=False);b.to_parquet(out/'cohort_new.parquet',index=False)
    cd=payload_diff(a,b,C+['rank_'+c for c in C]);coverage=[]
    for side,frame in [('old',old),('new',p)]:
        z=frame.groupby(['era','level']).agg(rows=('date','size'),price_complete=('price_complete','sum'),controls_complete=('market_controls_complete','sum'),joint_complete=('joint_complete','sum')).reset_index();z['version']=side;coverage+=z.to_dict('records')
    js(out/'coverage.json',coverage)
    reads={str(x):sha(x) for x in [dp,l1d,bp,mp,l1m,size,oldp,ROOT/'data/monthly_panel.parquet',ROOT/'src/market_controls_r54.py',ROOT/'src/label_fold_audit_r130.py',Path(__file__),ROOT/'protocols/r133.json']}
    js(out/'receipt.json',dict(reads=reads,sha256=sha(dest),rows=len(p),control_differences=diff,fsmd_differences=cd,outcomes_read=False,quality='Historical-proxy; L1 retained unchanged'))
    print('CONTROLS',diff,'COHORT',cd,flush=True)

if __name__=='__main__':run()
