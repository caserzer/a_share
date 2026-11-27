"""Expand EP41's frozen weekly left-tail setup to its symmetric right-tail label."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
OLD = next(HERE.parents[1].glob('41_*'))
sys.path.insert(0, str(OLD/'models'))
from ep41inputs import CACHE, COLS, KEY, TAIL, ep, pd, np
from fit import metrics, PARAM
import lightgbm as lgb
OUT = HERE/'results'
def run():
    from model_cache import ensure
    ensure()
    cols = list(dict.fromkeys(KEY+COLS+TAIL+['h10','sigma','m10','weekly','outer','y10']))
    panel = pd.read_parquet(CACHE/'panel.parquet',columns=cols)
    panel['right'] = ((panel.h10-panel.groupby('signal_date').h10.transform('median'))>2*panel.sigma).where(panel.h10.notna() & panel.sigma.gt(0)).astype(float)
    weekly = pd.read_parquet(OLD/'models/results/weekly_oof.parquet')
    weekly = weekly.merge(panel[KEY+['right']],on=KEY,validate='1:1')
    quarters = panel.signal_date.dt.to_period('Q')
    ext=[]; inner=[]
    for q in sorted(weekly.signal_date.dt.to_period('Q').unique()):
        tr=panel[panel.weekly & panel.m10.lt(q.start_time) & panel.y10.notna()].dropna(subset='right')
        test=panel[quarters.eq(q) & (panel.outer|panel.weekly)]
        row=test[KEY].copy(); row['rh']=tr.right.mean()
        for name,features in [('rinc',COLS),('rtail',COLS+TAIL)]:
            tree=lgb.train(dict(PARAM,objective='binary',boost_from_average=True),lgb.Dataset(tr[features],label=tr.right),num_boost_round=80)
            row[name]=tree.predict(test[features],num_threads=1)
        inner.append(row[test.weekly.to_numpy()])
        if test.outer.any():ext.append(row[test.outer.to_numpy()])
    weekly=weekly.merge(pd.concat(inner),on=KEY,validate='1:1')
    daily=pd.concat(ext).merge(pd.read_parquet(OLD/'models/results/quarterly_scores.parquet',columns=KEY+['risk','entry_idx','R','h10','event']),on=KEY,validate='1:1')
    daily=daily.merge(panel[KEY+['right']],on=KEY,validate='1:1')
    gates=[];enabled=[]
    for q in sorted(daily.signal_date.dt.to_period('Q').unique()):
        data=weekly[weekly.in_core & weekly.m10.lt(q.start_time)].copy()
        passed={}
        for side,cols in [('left',['tail','inc','history']),('right',['rtail','rinc','rh'])]:
            sub=data.copy()
            if side=='right':sub['event']=sub.right
            sub=sub.dropna(subset=['event'])
            vals=[metrics(sub,k) for k in cols]
            (a,b,c),(ab,bb,cb),(_,bh,_)=vals
            counts=sub.event.value_counts().reindex([0,1],fill_value=0)
            passed[side]=bool(min(counts)>=20 and sub.groupby('event').signal_date.nunique().min()>=4 and a>=.55 and a>ab and b<min(bb,bh) and c<cb)
            for model,(auc,brier,ece) in zip(cols,vals):
                gates.append(dict(quarter=str(q),side=side,model=model,auc=auc,brier=brier,ece=ece,n=len(sub),events=int(sub.event.sum()),passed=passed[side],last_label=sub.m10.max()))
        if all(passed.values()):enabled.append(str(q))
    ga=pd.DataFrame(gates)
    assert set(ga.query("side=='left' & passed").quarter)=={'2022Q3','2022Q4','2023Q2'}
    daily['enabled']=daily.signal_date.dt.to_period('Q').astype(str).isin(enabled)
    ga.to_csv(OUT/'dual_gate.csv',index=False); daily.to_parquet(OUT/'dual_scores.parquet',index=False);weekly.to_parquet(OUT/'dual_weekly.parquet',index=False)
    print('dual gate quarters',enabled,flush=True)
if __name__=='__main__': run()
