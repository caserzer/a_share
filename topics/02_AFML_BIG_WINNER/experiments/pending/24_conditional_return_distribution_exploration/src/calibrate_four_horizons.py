"""R11: prequential PIT recalibration, only matured prior OOS labels.

Fixed 50% identity shrinkage; trailing 36 prediction months; >=12 months.
Reweights the entire CDF, preserving coherent interval and direction probabilities.
"""
import numpy as np
import pandas as pd
from run_four_horizons import DEST, CACHE, GRID, probability_stats


def recalibrated_atoms(atoms, historical_pit, shrink=.5):
    pit = np.sort(np.asarray(historical_pit))
    edges = np.linspace(0,1,atoms.shape[1]+1)
    empirical = np.searchsorted(pit, edges, side='right') / len(pit)
    mapped = (1-shrink)*edges + shrink*empirical
    mapped[0], mapped[-1] = 0., 1.
    raw_levels = np.interp(GRID, mapped, edges)
    return np.stack([np.interp(raw_levels, GRID, row) for row in atoms])


def run():
    audit=[]
    for h in [1,3,6,12]:
        path=DEST/f'predictions_{h}m.parquet'
        data=pd.read_parquet(path)
        data=data[~data.model.str.endswith('_pitcal')].copy()
        results=[]
        for model in ['peers_risk_size','peers_full','catboost_full']:
            source=data[data.model==model]
            quarter_atoms={}
            for date,g in source.groupby('date',sort=True):
                g=g.reset_index(drop=True)
                history=source[(source.label_end<date)&source.actual.notna()&
                    (source.date>=date-pd.DateOffset(months=36))]
                quarter=str(date.to_period('Q'))
                keys=pd.read_parquet(CACHE/f'{h}_{quarter}_keys.parquet')
                keyindex=pd.MultiIndex.from_frame(keys[['date','instrument']])
                pos=keyindex.get_indexer(pd.MultiIndex.from_frame(g[['date','instrument']]))
                assert (pos>=0).all()
                atoms=np.load(CACHE/f'{h}_{quarter}_{model}.npz')['atoms'][pos]
                used=history.date.nunique()>=12
                calibrated=recalibrated_atoms(atoms,history.pit.to_numpy()) if used else atoms
                if quarter not in quarter_atoms:
                    quarter_atoms[quarter]=np.empty((len(keys),atoms.shape[1]),dtype=np.float32)
                quarter_atoms[quarter][pos]=calibrated
                r=g[['date','instrument','actual','label_end','target_date','months']].copy()
                r=pd.concat([r,probability_stats(calibrated,g.actual)],axis=1)
                r['model']=model+'_pitcal'
                r['calibration_active']=used
                results.append(r)
                audit.append(dict(months=h,model=model,date=str(date.date()),active=used,
                    historical_rows=len(history),historical_months=history.date.nunique(),
                    last_label=str(history.label_end.max())))
            for quarter, atoms in quarter_atoms.items():
                np.savez_compressed(CACHE/f'{h}_{quarter}_{model}_pitcal.npz',atoms=atoms)
        pd.concat([data,*results],ignore_index=True).to_parquet(path,index=False)
    pd.DataFrame(audit).to_csv(DEST/'prequential_calibration_audit.csv',index=False)


if __name__=='__main__':
    run()
