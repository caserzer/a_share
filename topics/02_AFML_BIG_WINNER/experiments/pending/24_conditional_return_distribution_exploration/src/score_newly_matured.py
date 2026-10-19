"""R14B: score frozen forecasts with newly observable public price-proxy labels."""
import hashlib
import json
import numpy as np
import pandas as pd
from fetch_walk_forward_extension import DEST,CACHE
from prepare_panel import DATA
from run_four_horizons import OUT,BINS,BIN_NAMES,probability_stats
OLD=OUT/'r10_four_horizons'
MODELS=['expanding_empirical','recent24_empirical','peers_risk_size']


def check_frozen():
    manifest=json.loads((DEST/'frozen_predictions.json').read_text())
    for f in manifest['files']:assert hashlib.sha256(open(f['path'],'rb').read()).hexdigest()==f['sha256']


def run():
    check_frozen()
    calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'SH000001.parquet').date).sort_values()
    prices={};overlap=[]
    for path in sorted(CACHE.glob('*.parquet')):
        stock=path.stem
        if stock=='SH000001':continue
        new=pd.read_parquet(path).set_index('date').close.reindex(calendar)
        old=pd.read_csv(DATA/f'raw/akshare/day/qfq/{stock}.csv',parse_dates=['date']).set_index('date').close.reindex(calendar)
        compare=pd.concat([old.pct_change(fill_method=None).rename('old'),new.pct_change(fill_method=None).rename('new')],axis=1).dropna().tail(60)
        error=float((compare.old-compare.new).abs().max()) if len(compare) else np.nan
        stable=len(compare)>=20 and error<.003
        overlap.append(dict(instrument=stock,overlap_rows=len(compare),max_daily_return_difference=error,source_stable=stable))
        prices[stock]=(new,stable)
    pd.DataFrame(overlap).to_csv(DEST/'source_overlap_audit.csv',index=False)
    labels=[];results=[]
    for h in [1,3,6]:
        old=pd.read_parquet(OLD/f'predictions_{h}m.parquet')
        candidates=old[(old.model=='peers_risk_size')&(old.target_date>'2026-05-29')&(old.target_date<='2026-10-19')]
        for _,r in candidates.iterrows():
            later=calendar[calendar>=r.target_date]
            end=later[0] if len(later) else pd.NaT
            record=dict(months=h,date=r.date,instrument=r.instrument,target_date=r.target_date,label_end=end,actual=np.nan,status='missing_source')
            if pd.isna(end):record['status']='not_mature'
            elif r.instrument in prices:
                price,stable=prices[r.instrument];start=price.get(r.date,np.nan);last=price.get(end,np.nan)
                if not np.isfinite(start) or not np.isfinite(last) or start<=0 or last<=0:record['status']='missing_endpoint'
                else:
                    record['actual']=float(last/start-1);record['status']='valid' if stable else 'source_unstable'
            labels.append(record)
        label=pd.DataFrame([r for r in labels if r['months']==h])
        for model in MODELS:
            selected=old[old.model==model].merge(label,on=['date','instrument','months'],suffixes=('_old',''),validate='one_to_one')
            parts=[]
            for quarter,g in selected.groupby(selected.date.dt.to_period('Q')):
                keys=pd.read_parquet(OUT/f'local_cache/r10_distributions/{h}_{quarter}_keys.parquet')
                positions=pd.MultiIndex.from_frame(keys).get_indexer(pd.MultiIndex.from_frame(g[['date','instrument']]))
                assert (positions>=0).all()
                atoms=np.load(OUT/f'local_cache/r10_distributions/{h}_{quarter}_{model}.npz')['atoms'][positions]
                # Keep uncertain-source outcomes for a separately labeled sensitivity, never silently discard.
                base=g[['date','instrument','months','model','target_date','label_end','actual','status']].reset_index(drop=True)
                stats=probability_stats(atoms,base.actual)
                # Verify these are the original probability forecasts, allowing float32 storage quantization.
                assert np.max(np.abs(stats.p_up.to_numpy()-g.p_up.to_numpy()))<=.0050001
                # Preserve originally published probabilities exactly; atom files were stored float32.
                for col in ['p_up','p_down','p_zero',*[f'p_{name}' for name in BIN_NAMES],'q05','q50','q95']:
                    stats[col]=g[col].to_numpy()
                y=base.actual.to_numpy()
                stats['brier']=(stats.p_up.to_numpy()-(y>0))**2
                probs=stats[[f'p_{name}' for name in BIN_NAMES]].to_numpy()
                stats['multiclass_brier']=((probs-np.eye(5)[np.searchsorted(BINS,y,side='right')])**2).sum(axis=1)
                stats['below_q05']=(y<stats.q05.to_numpy()).astype(float)
                stats['coverage90']=((y>=stats.q05.to_numpy())&(y<=stats.q95.to_numpy())).astype(float)
                stats.loc[~np.isfinite(y),['brier','multiclass_brier','below_q05','coverage90']]=np.nan
                parts.append(pd.concat([base,stats],axis=1))
            results.extend(parts)
    label=pd.DataFrame(labels);label.to_parquet(DEST/'new_labels.parquet',index=False)
    predictions=pd.concat(results,ignore_index=True);predictions.to_parquet(DEST/'scored_frozen_predictions.parquet',index=False)
    label.groupby(['months','date','status']).size().rename('rows').to_csv(DEST/'outcome_coverage.csv')
    metrics=['brier','multiclass_brier','crps','below_q05','coverage90']
    summaries=[]
    for scope,statuses in [('stable_source',['valid']),('including_source_uncertainty',['valid','source_unstable'])]:
        s=predictions[predictions.status.isin(statuses)].copy()
        monthly=s.groupby(['months','date','model'])[metrics].mean().reset_index();monthly['scope']=scope
        summaries.append(monthly)
    monthly=pd.concat(summaries,ignore_index=True);monthly.to_csv(DEST/'monthly_scores.csv',index=False)
    monthly.groupby(['scope','months','model'])[metrics].mean().to_csv(DEST/'summary.csv')
    calibration=[]
    for (h,model),g in predictions[predictions.status=='valid'].groupby(['months','model']):
        classes=np.searchsorted(BINS,g.actual,side='right')
        for event in ['up','down',*BIN_NAMES]:
            observed=(g.actual>0).astype(float) if event=='up' else ((g.actual<0).astype(float) if event=='down' else (classes==BIN_NAMES.index(event)).astype(float))
            for bucket,b in g.assign(observed=observed,bucket=np.floor(g[f'p_{event}']*10).clip(upper=9)).groupby('bucket'):
                calibration.append(dict(months=h,model=model,event=event,bin=int(bucket),rows=len(b),origin_months=b.date.nunique(),predicted=b[f'p_{event}'].mean(),observed=b.observed.mean(),inference='few new origin months; no stability claim'))
    pd.DataFrame(calibration).to_csv(DEST/'probability_calibration.csv',index=False)
    check_frozen()
    print(label.groupby(['months','status']).size().to_string())
    print(monthly.groupby(['scope','months','model'])[metrics].mean().to_string())


if __name__=='__main__':run()
