from common import *
import pandas as pd

def run():
 o=ROOT/'outputs/r283';o.mkdir(exist_ok=True);pred=pd.read_parquet(ROOT/'outputs/r281/predictions.parquet');keys=KEY+['date','horizon'];unique=pred[keys+['target','maturity']].drop_duplicates();assert not unique.duplicated(keys).any();daily_path=ROOT/'outputs/r129/daily_2026-10-21.parquet';benchmark_path=CACHE/'forecast_v5/CSI_ALL.parquet';legacy_path=CACHE/'forecast_v5/daily_industries.parquet';d=pd.read_parquet(daily_path);b=pd.read_parquet(benchmark_path).close.sort_index();calendar=b.index;assert calendar.is_unique;rows=[]
 for _,x in unique.iterrows():
  g=d.copy()
  for k in KEY:g=g[g[k]==x[k]]
  g=g.sort_values('date').set_index('date');assert g.index.is_unique;i=calendar.get_indexer([x.date])[0];assert i>=0;entrypos=i+1;exitpos=i+1+int(x.horizon);entry=calendar[entrypos] if entrypos<len(calendar) else pd.NaT;exit=calendar[exitpos] if exitpos<len(calendar) else pd.NaT;remaining=max(0,exitpos-(len(calendar)-1));available_path=calendar[entrypos:min(exitpos+1,len(calendar))];path=g.reindex(available_path);missing=int(path.nav.isna().sum());blocks=path.block.dropna().nunique();ready=pd.notna(exit) and missing==0 and blocks==1 and path.nav.gt(0).all() and b.reindex(available_path).gt(0).all()
  value=(g.at[exit,'nav']/g.at[entry,'nav']-1)-(b.loc[exit]/b.loc[entry]-1) if ready else None
  old=pd.notna(x.target)
  if old:assert ready and abs(value-x.target)<1e-12 and exit==x.maturity
  rows.append(dict(**{k:x[k] for k in keys},original_target=x.target,original_maturity=x.maturity,entry=entry,exit=exit,calendar_last=calendar.max(),industry_last=g.index.max(),observed_path_sessions=len(available_path),required_path_sessions=int(x.horizon)+1,additional_sessions_needed=remaining,missing_nav_on_observed_calendar=missing,observed_blocks=int(blocks),status='reproduced_existing' if old else 'newly_reconstructable' if ready else 'calendar_or_price_incomplete',reconstructed_target=value))
 table=pd.DataFrame(rows);table.to_parquet(o/'unique_labels.parquet',index=False);table.to_csv(o/'unique_labels.csv',index=False)
 legacy=pd.read_parquet(legacy_path,columns=KEY+['date']);inventory=[]
 for ident,g in legacy[legacy.industry_code.isin(['801737.SI','857371.SI'])&legacy.era.eq('SW2021')].groupby(KEY):inventory.append(dict(zip(KEY,ident),last=g.date.max(),role='Legacy uncorrected basket; date coverage only, not substituted'))
 summary=dict(status='PASS',prediction_rows=len(pred),unique_industry_date_horizons=len(table),unique_missing=int(table.original_target.isna().sum()),newly_reconstructed=int(table.status.eq('newly_reconstructable').sum()),reproduced_existing=int(table.status.eq('reproduced_existing').sum()),calendar_last=calendar.max(),legacy_coverage=inventory,models_refit=0,predictions_changed=0,strict_pit=False);js(o/'summary.json',summary)
 inputs=[daily_path,benchmark_path,legacy_path,ROOT/'outputs/r281/predictions.parquet',ROOT/'src/battery_label_coverage_r283.py',ROOT/'protocols/r283.json'];js(o/'receipt.json',dict(inputs={str(f):sha(f) for f in inputs},outputs={f.name:sha(f) for f in o.iterdir() if f.is_file() and f.name!='receipt.json'}));print(summary);print(table[table.original_target.isna()][['level','date','horizon','entry','additional_sessions_needed']].to_string(index=False))
if __name__=='__main__':run()
