from common import *
import pandas as pd
from process_replay_r09 import cooldown_alerts
IDENT=KEY+['date','variant','strategy']
def run():
 out=ROOT/'outputs/r297';out.mkdir(exist_ok=True);p=pd.read_parquet(ROOT/'outputs/r295/predictions.parquet');o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');old=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet')
 p=p.merge(o[KEY+['date','day_i','complete_path','episode_id','signal_lead']],on=KEY+['date'],validate='many_to_one');cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);ends=pd.Series(cal,index=cal).groupby(cal.to_period('M')).max();ends=ends[[x.end_time.normalize()<=cal.max() for x in ends.index]];parts=[];ranks=[]
 for variant,g in p.groupby('variant'):
  ordered=g.sort_values(['era','level','date','daily_probability','industry_code'],ascending=[True,True,True,False,True]);grp=ordered.groupby(['era','level','date']);raw=ordered[grp.cumcount()<np.ceil(.2*grp.daily_probability.transform('size'))]
  for strategy,a in [('daily',raw),('monthly',raw[raw.date.isin(ends.values)]),('daily_cooldown20',cooldown_alerts(raw))]:parts.append(a.assign(strategy=strategy))
  for key,z in g.groupby(['era','level','date']):
   a=z.sort_values(['daily_probability','industry_code'],ascending=[False,True]);b=z.sort_values(['monthly_probability','industry_code'],ascending=[False,True]);ranks.append(dict(zip(['era','level','date'],key),variant=variant,rows=len(z),same_full_order=a.industry_code.tolist()==b.industry_code.tolist(),daily_ties=int(z.daily_probability.duplicated().sum()),monthly_ties=int(z.monthly_probability.duplicated().sum())))
 new=pd.concat(parts,ignore_index=True);compare=new[IDENT].merge(old[IDENT],on=IDENT,how='outer',indicator=True,validate='one_to_one');diff=compare[compare._merge.ne('both')];new.to_parquet(out/'alerts.parquet',index=False);diff.to_parquet(out/'differences.parquet',index=False);pd.DataFrame(ranks).to_csv(out/'rank_checks.csv',index=False)
 same=new.merge(old,on=IDENT,validate='one_to_one',suffixes=('','_old'))
 for c in ['day_i','complete_path','episode_id','signal_lead','y']:assert ((same[c]==same[c+'_old'])|(same[c].isna()&same[c+'_old'].isna())).all()
 result=dict(status='PASS',prediction_rows=len(p),alerts=len(new),old_alerts=len(old),changed_alert_identities=len(diff),date_variant_groups=len(ranks),changed_full_orders=sum(not x['same_full_order'] for x in ranks),can_reuse_original_action_results=len(diff)==0,adoption=False)
 js(out/'summary.json',result);inputs=json.loads((ROOT/'protocols/r297.json').read_text())['inputs']+['protocols/r297.json','src/calibration_actions_r297.py','src/process_replay_r09.py'];js(out/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in inputs},calendar_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),outputs={s:sha(out/s) for s in ['alerts.parquet','differences.parquet','rank_checks.csv','summary.json']}));print(result)
if __name__=='__main__':run()
