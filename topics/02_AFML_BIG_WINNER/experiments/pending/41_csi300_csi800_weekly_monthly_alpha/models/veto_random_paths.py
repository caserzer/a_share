"""Two hundred deterministic same-count veto controls using the validated funded book."""
from pathlib import Path
from hashlib import sha256
import sys
import json
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p1'))
from engine import load,pack,simulate

def main():
    m=load(False);out=HERE/'results'
    qlist={p.name[:6] for p in out.glob('*_fold.json') if json.loads(p.read_text())['veto']}
    data=pd.read_parquet(next(HERE.parents[1].glob('40_*'))/'lightgbm/followup/results/daily_scores.parquet',columns=['signal_date','instrument','entry_idx','R'])
    base={};active={}
    for (day,entry),g in data.groupby(['signal_date','entry_idx']):
        names=g.sort_values(['R','instrument'],ascending=False).instrument.to_numpy()
        k=len(g)//10;indices=m.symbols.get_indexer(names);base[entry]=indices[:k]
        if str(day.to_period('Q')) in qlist:active[entry]=(day,names[:k],indices[:k],indices[k:k+3])
    rows=[]
    for seed in range(1,201):
        plans=[base.copy(),base.copy()]
        for entry,(day,names,ids,add) in active.items():
            sort=sorted(range(len(ids)),key=lambda j:sha256(f'{day.date()}|{seed}|{names[j]}'.encode()).digest())
            for count,plan in zip([2,3],plans):
                plan[entry]=np.r_[np.delete(ids,sort[:count]),add[:count]]
        for count,plan in zip([2,3],plans):
            packed=pack(m,plan)
            for seg,a,b in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
                nav=simulate(m,packed,(a,b,b)).nav
                months=nav.groupby(nav.index.to_period('M')).last().pct_change().iloc[1:-1]
                for month,net in months.items():rows.append((seed,count,seg,str(month),net))
    pd.DataFrame(rows,columns='seed count segment month net'.split()).to_parquet(out/'veto_random_months.parquet',index=False)
if __name__=='__main__':main()
