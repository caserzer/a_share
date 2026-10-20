"""Execute exactly the frozen finite candidate set; checkpoint by horizon/quarter."""
import json
import time
import numpy as np
import pandas as pd
from core import *


def freeze():
    tracked=[EP/'research_plan.md',EP/'config.json']+sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))
    declaration=dict(research_date=CONFIG['research_date'],created_utc=pd.Timestamp.now(tz='UTC').isoformat(),
        files={str(p.relative_to(EP)):digest(p) for p in tracked},input_receipts_sha256=digest(OUT/'input_receipts.json'),
        evidence='retrospective preregistration before EP25 scoring, not independent holdout',formal_candidates=4,baselines=2)
    p=OUT/'preregistration.json'
    if p.exists():
        old=json.loads(p.read_text())
        assert all(digest(EP/k)==v for k,v in old['files'].items()),'frozen source changed'
        assert digest(OUT/'input_receipts.json')==old['input_receipts_sha256']
    else:
        write_json(p,declaration)
    return digest(p)


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    lock_hash=freeze()
    panel=load_panel()
    full_audit=[]
    for h in CONFIG['horizons']:
        frozen=pd.read_parquet(OLD/f'outputs/r10_four_horizons/predictions_{h}m.parquet')
        for quarter in sorted(panel[panel.date>=CONFIG['prediction_start']].date.dt.to_period('Q').unique()):
            stem=f'{h}_{quarter}'
            receipt=OUT/f'checkpoints/{stem}.json'
            if receipt.exists():
                r=json.loads(receipt.read_text())
                assert r['preregistration_sha256']==lock_hash
                for key in ['predictions','atoms']:
                    assert digest(EP/r[key]['path'])==r[key]['sha256']
                full_audit.append(r)
                continue
            train,test=train_test(panel,quarter.start_time,h,quarter)
            assert len(train)>1000 and len(test)
            preds=baselines(train,test,h)
            maxerr=0.
            for name,oldname in [('B0','expanding_empirical'),('B1','peers_risk_size')]:
                original=frozen[frozen.model.eq(oldname)&frozen.date.dt.to_period('Q').eq(quarter)].reset_index(drop=True)
                pd.testing.assert_frame_equal(test[['date','instrument']],original[['date','instrument']])
                np.testing.assert_allclose(test[f'y_{h}'],original.actual,equal_nan=True,rtol=0,atol=0)
                metrics=score(preds[name],test[f'y_{h}'])
                for c in ['crps','brier','p_up','mean','q05','q50','q95','pit']:
                    np.testing.assert_allclose(metrics[c],original[c],rtol=1e-11,atol=1e-12,equal_nan=True)
                    if metrics[c].notna().any():maxerr=max(maxerr,float((metrics[c]-original[c]).abs().max()))
                oldcache=OLD/f'outputs/local_cache/r10_distributions/{h}_{quarter}_{oldname}.npz'
                with np.load(oldcache) as data: np.testing.assert_array_equal(preds[name].astype(np.float32),data['atoms'])
            crossing={};start=time.monotonic()
            for name in CONFIG['candidates']:
                model=fit_model(train,h,name)
                preds[name],crossing[name]=predict_atoms(model,test,name)
                model.save_model(str(CACHE/f'{stem}_{name}.cbm'))
            keys=test[['date','instrument',f'y_{h}',f'end_{h}','board','market_mom126','vol63','log_cap']].rename(columns={f'y_{h}':'actual',f'end_{h}':'label_end'})
            keys['horizon']=h
            keys['regime']=np.where(keys.market_mom126>0,'uptrend','non_uptrend')
            keys['phase']=np.where(keys.date<'2024-01-01','2021-2023','2024-2026')
            keys['size_group']=np.where(keys.log_cap>=keys.groupby('date').log_cap.transform('median'),'large','small')
            keys['risk_group']=np.where(keys.vol63>=keys.groupby('date').vol63.transform('median'),'high','low')
            rows=[]
            for name,s in preds.items():
                for date,g in keys.groupby('date',sort=True):
                    idx=g.index.to_numpy();a=s[idx]
                    r=pd.concat([g.reset_index(drop=True),score(a,g.actual).reset_index(drop=True)],axis=1)
                    r['model']=name
                    rows.append(r)
            frame=pd.concat(rows,ignore_index=True)
            pp=CACHE/f'{stem}_predictions.parquet'; ap=CACHE/f'{stem}_atoms.npz'
            frame.to_parquet(pp,index=False)
            np.savez_compressed(ap,**preds)
            r=dict(horizon=h,quarter=str(quarter),preregistration_sha256=lock_hash,
                training_rows=len(train),training_months=train.date.nunique(),prediction_rows=len(test),
                max_training_label=str(train[f'end_{h}'].max().date()),first_prediction=str(test.date.min().date()),
                train_keys_sha256=hashlib.sha256(train[['date','instrument']].to_csv(index=False).encode()).hexdigest(),
                test_keys_sha256=hashlib.sha256(test[['date','instrument']].to_csv(index=False).encode()).hexdigest(),
                frozen_baseline_max_error=maxerr,frozen_baseline_float32_atoms_bitwise_match=True,
                crossings=crossing,elapsed_seconds=time.monotonic()-start,
                predictions=dict(path=str(pp.relative_to(EP)),sha256=digest(pp)),atoms=dict(path=str(ap.relative_to(EP)),sha256=digest(ap)))
            receipt.parent.mkdir(exist_ok=True)
            write_json(receipt,r);full_audit.append(r)
            print('EP25',stem,'train',len(train),'test',len(test),'seconds',round(r['elapsed_seconds'],1),flush=True)
    write_json(OUT/'fit_audit.json',full_audit)
    pd.DataFrame([{k:v for k,v in r.items() if k not in ['crossings','predictions','atoms']} for r in full_audit]).to_csv(OUT/'fit_audit.csv',index=False)
    print('All preregistered fits completed.',flush=True)

if __name__=='__main__':main()
