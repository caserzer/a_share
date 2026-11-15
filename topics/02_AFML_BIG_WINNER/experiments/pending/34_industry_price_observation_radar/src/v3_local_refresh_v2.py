"""Local-only raw-price inference and full-history replay of frozen candidates."""
import argparse,json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from v3_m01_prepare import feature_group,FEATURES_CHANGE
from v3_m06_replay import replay


def build_signals(raw,cat,calendar,model_dir,cutoff):
    cutoff=pd.Timestamp(cutoff);raw=raw[raw.date.le(cutoff)].copy();cat=cat[cat.date.le(cutoff)].copy()
    assert not raw.duplicated(['date','era','industry_code']).any()
    assert not cat.duplicated(['date','era','industry_code']).any()
    assert cat.date.min()<pd.Timestamp('2020-01-01'),'Require original directory history, not a new-period empty-pool restart'
    cal=calendar.copy();cal['week']=cal.date.dt.to_period('W-SUN');reviews=cal.groupby('week').date.max()
    if cal.date.max().weekday()<4:reviews=reviews.iloc[:-1]
    cat=cat[cat.date.isin(reviews[reviews.le(cutoff)])]
    parts=[feature_group(g) for _,g in raw.groupby(['era','industry_code'],sort=True)]
    panel=cat.merge(pd.concat(parts),on=['date','era','industry_code'],how='left',validate='one_to_one')
    panel['eligible']=panel.r5.gt(0)&panel[FEATURES_CHANGE].notna().all(axis=1)
    panel['week']=panel.date.map({d:i for i,d in enumerate(sorted(cat.date.unique()))})
    panel=panel.sort_values(['era','industry_code','date'])
    prev=panel.groupby(['era','industry_code'])[['week','block','r20']].shift(1)
    panel['enhance']=panel.week.sub(prev.week).eq(1)&panel.block.eq(prev.block)&panel.r20.gt(prev.r20)
    panel['eligible_original']=panel.eligible&panel.r20.gt(0)
    panel=panel[panel.date.ge('2020-01-01')].copy()
    receipt=json.loads((model_dir/'receipt.json').read_text());fitpath=model_dir/'fit_audit.csv'
    assert sha(fitpath)==receipt['artifacts']['fit_audit.csv']
    audit=pd.read_csv(fitpath);used=[]
    for year,g in panel.groupby(panel.date.dt.year):
        for model in ['LR_COVER','LR_EARLY_UNION']:
            file=model_dir/str(year)/(model+'.joblib');rel=str(file.relative_to(model_dir))
            if not file.exists() or rel not in receipt['artifacts']:raise ValueError(f'No registered model for {year}/{model}; do not silently reuse older year')
            assert sha(file)==receipt['artifacts'][rel]
            fit=audit[audit.year.eq(year)&audit.model.eq(model)];assert len(fit)==1
            cut=pd.Timestamp(year=int(year),month=1,day=1)
            assert pd.Timestamp(fit.latest_label_available.iloc[0])<cut and pd.Timestamp(fit.fitted_before.iloc[0])==cut
            estimator=joblib.load(file);mask=g.eligible;panel.loc[g.index,'score_'+model]=np.nan
            if mask.any():panel.loc[g.index[mask],'score_'+model]=estimator.predict_proba(g.loc[mask,FEATURES_CHANGE])[:,1]
            used.append(file)
    rank=panel.groupby('date')[['score_LR_COVER','score_LR_EARLY_UNION']].rank(pct=True,method='average')
    panel['score_BALANCED']=rank.mean(axis=1,skipna=False);panel['score_BROAD20']=panel.r20
    support=pd.DataFrame({'date':reviews[(reviews>=pd.Timestamp('2020-01-01'))&reviews.le(cutoff)]})
    support['directory_count']=support.date.map(panel.groupby('date').size());support['state']=np.where(support.directory_count.notna(),'SUPPORTED_DIRECTORY','DIRECTORY_UNAVAILABLE_UNKNOWN')
    return panel,support,used


def main():
    old=json.loads((PRIOR/'receipt.json').read_text());cal=Path(next(k for k in old['inputs'] if k.endswith('/calendar.parquet')))
    parser=argparse.ArgumentParser();parser.add_argument('--as-of',required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--raw',type=Path,default=PRIOR/'daily_industries.parquet');parser.add_argument('--catalog',type=Path,default=EP/'outputs/r01/weekly_catalog.parquet');parser.add_argument('--calendar',type=Path,default=cal);parser.add_argument('--models',type=Path,default=EP/'outputs/v3_m02_models')
    a=parser.parse_args();assert not a.out.exists()
    raw=pd.read_parquet(a.raw,columns=['date','day_i','era','industry_code','block','nav']);cat=pd.read_parquet(a.catalog,columns=['date','era','industry_code','industry_name']);calendar=pd.read_parquet(a.calendar)
    assert pd.Timestamp(a.as_of)<=raw.date.max(),'Requested cutoff is beyond local data; no fabricated fresh observation'
    panel,support,used=build_signals(raw,cat,calendar,a.models,a.as_of)
    assert len(panel) and panel.date.max()<=pd.Timestamp(a.as_of)
    a.out.mkdir(parents=True);panel.to_parquet(a.out/'signal_catalog.parquet',index=False);support.to_csv(a.out/'calendar_coverage.csv',index=False)
    # Explicit whitelist prevents inference from training/evaluation metadata.
    fields=['date','era','industry_code','industry_name','block','r5','r20','r40','week','enhance','eligible','eligible_original','score_BALANCED','score_BROAD20']
    rows=[]
    for arm in ['BALANCED_COMPETE','BROAD20_COMPETE']:rows.extend(replay(panel[fields],[arm],5,a.out,'solo'))
    pd.DataFrame(rows).to_csv(a.out/'run_inventory.csv',index=False)
    inputs=[a.raw,a.catalog,a.calendar,a.models/'receipt.json',a.models/'fit_audit.csv',Path(__file__),EP/'src/v3_m01_prepare.py',EP/'src/v3_m06_replay.py']+used
    (a.out/'receipt.json').write_text(json.dumps(dict(requested_as_of=a.as_of,latest_review=str(panel.date.max().date()),mode='FULL_HISTORY_REPLAY_NOT_EMPTY_POOL_INCREMENT',inputs={str(p):sha(p) for p in inputs},artifacts={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file()},limits='Existing local historical proxy only. Source revisions can change old signals and require explicit version migration. No final labels read, no fitting, no deployment.'),indent=2)+'\n')
    print('Local refresh',a.as_of,'latest review',panel.date.max().date(),'rows',len(panel),flush=True)

if __name__=='__main__':main()
