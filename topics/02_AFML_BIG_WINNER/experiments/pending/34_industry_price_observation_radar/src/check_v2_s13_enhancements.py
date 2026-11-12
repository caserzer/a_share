"""Check all inherited fits/candidates and independently recompute support windows."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from audit_local_inputs import EP,PRIOR,sha

def main():
 out=EP/'outputs/v2_s13_duration_enhancements';oldroot=EP/'outputs/r00_v2_enhancement03_recovery'
 bridge=pd.read_csv(EP/'outputs/v2_s12_full_directory_duration/boundary_audit/old_new_interval_bridge.csv');assert bridge.new_id.is_unique and bridge.old_id.is_unique
 mapping=bridge.set_index('new_id').old_id.to_dict()
 newfits=pd.read_parquet(out/'parent_fits.parquet');oldfits=pd.read_parquet(oldroot/'parent_fits.parquet');mapped=newfits[newfits.parent_id.isin(mapping)].copy();mapped['parent_id']=mapped.parent_id.map(mapping)
 pd.testing.assert_frame_equal(mapped.sort_values('parent_id').reset_index(drop=True),oldfits.sort_values('parent_id').reset_index(drop=True))
 new=pd.read_parquet(out/'children.parquet');old=pd.read_parquet(oldroot/'children.parquet');mapped=new.copy();mapped['parent_id']=mapped.parent_id.map(mapping);assert mapped.parent_id.notna().all()
 keys=['era','industry_code','block','start_date','end_date'];assert not old.duplicated(keys).any() and not new.duplicated(keys).any()
 columns=[c for c in old.columns if c!='child_id']
 pd.testing.assert_frame_equal(mapped[columns].sort_values(keys).reset_index(drop=True),old[columns].sort_values(keys).reset_index(drop=True))
 cb=new[keys+['child_id','parent_id']].merge(old[keys+['child_id','parent_id']],on=keys,validate='one_to_one',suffixes=('_new','_old'));cb.to_csv(out/'old_new_child_identity_bridge.csv',index=False)
 raw=pd.read_parquet(PRIOR/'daily_industries.parquet',columns=['era','industry_code','block','date','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN');raw['y']=np.log(raw.nav)
 weekly=raw.groupby(['era','industry_code','block','week']).agg(y=('y','median'),end=('date','max')).reset_index();groups={k:g.sort_values('week') for k,g in weekly.groupby(['era','industry_code','block'])}
 parents=pd.read_parquet(EP/'outputs/v2_s12_full_directory_duration/processes.parquet').set_index('process_id')
 for r in new.itertuples():
  p=parents.loc[r.parent_id];assert p.start_date<=r.start_date<=r.end_date<=p.end_date
  w=groups[(r.era,r.industry_code,r.block)];w=w[w.end.between(pd.Timestamp(p.start_date),pd.Timestamp(p.end_date))].reset_index(drop=True);y=w.y.to_numpy()
  a=int(r.start_i);b=int(r.end_i);matches=[j for j in range(a+4,b+1) if all(y[t]>y[a] for t in range(j-3,j+1))]
  expected=None if not matches else str(w.end.iloc[matches[0]].date())
  assert r.confirm_date==expected
  status='PATH_SUPPORTED' if expected is not None else 'RIGHT_UNKNOWN' if p.right_open and b==len(w)-1 else 'NOT_RETAINED'
  assert r.status==status
 for r in new.groupby('parent_id'):
  g=r[1].sort_values('start_i');assert (g.start_i.iloc[1:].to_numpy()>=g.end_i.iloc[:-1].to_numpy()).all()
 receipt=json.loads((out/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(Path(f))==h
 for f,h in receipt['artifacts'].items():assert sha(out/f)==h
 result={'inherited_parent_fits_exactly_equal':len(mapped) if False else len(oldfits),'all_children_exactly_equal_after_identity_mapping':len(new),'first_support_windows_independently_verified':len(new),'new_parent_paths':int((~newfits.parent_id.isin(mapping)).sum()),'children_on_new_parent_paths':int((~new.parent_id.isin(mapping)).sum()),'status':new.status.value_counts().to_dict(),'hashes_verified':True,'script_sha256':sha(Path(__file__))}
 (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
