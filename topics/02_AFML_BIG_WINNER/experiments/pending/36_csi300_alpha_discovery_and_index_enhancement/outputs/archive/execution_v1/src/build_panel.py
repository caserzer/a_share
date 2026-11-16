"""Verify consumed EP30 files and build features separately from labels."""
import numpy as np,pandas as pd
from common import *
from features import compute,dictionary
from residual import monthly_residual_score

def main():
 root,manifest=release();used=[]
 def read(name):
  f=read_sealed(root,manifest,name);used.append(manifest[name]);return f
 days=pd.DatetimeIndex(read('inputs/inputs/baseline/normalized/calendar.parquet').date);signals=signal_days(days)
 members=pd.read_parquet(PRIVATE/'members/weekly.parquet');members['instrument']=members.code.str[:2].str.upper()+members.code.str[3:]
 members['updateDate']=pd.to_datetime(members.updateDate)
 assert not (members.updateDate>members.signal_date).any()
 symbols=sorted(set(members.instrument));sec=read('inputs/normalized/securities.parquet');intervals=read('inputs/normalized/code_intervals.parquet')
 fields=['qfq_open','qfq_high','qfq_low','qfq_close','open','high','low','close','volume','money','turnover_rate','vendor_trade_status','vendor_is_st']
 mats={k:pd.DataFrame(np.nan,index=days,columns=symbols) for k in fields};audit=[]
 for i,s in enumerate(symbols):
  ids=set(sec.loc[sec.instrument.eq(s)|sec.metadata_instrument_v3.eq(s),'security_id']);ids.update(intervals.loc[intervals.instrument.eq(s),'security_id'])
  if len(ids)!=1:audit.append(dict(instrument=s,status='UNKNOWN_IDENTITY',identity_count=len(ids)));continue
  sid=next(iter(ids));name=f'normalized/prices_qfq/{sid}.parquet'
  if name not in manifest:audit.append(dict(instrument=s,security_id=sid,status='MISSING_BARS'));continue
  f=read(name).set_index('date').reindex(days)
  for k in fields:
   x=pd.to_numeric(f[k],errors='coerce')
   cf=k.replace('qfq_','')+'_conflict'
   if cf in f:x=x.mask(f[cf].fillna(False).astype(bool))
   if k.startswith('qfq_') or k in ['open','high','low','close']:x=x.where(x>0)
   mats[k][s]=x
  audit.append(dict(instrument=s,security_id=sid,status='READ_VERIFIED',rows=int(f.qfq_close.notna().sum()),unknown_execution=int(f.can_buy.isna().sum()),source_sha256=manifest[name]['sha256']))
  if i%100==0:print('prices',i,len(symbols),flush=True)
 # Deduplicate provider update dates; identical snapshots queried from multiple signal days must agree.
 sets=members.groupby(['updateDate','signal_date']).instrument.apply(lambda x:tuple(sorted(x)))
 assert sets.groupby(level=0).nunique().max()==1
 snap=members[['updateDate','instrument']].drop_duplicates().assign(member=True).pivot(index='updateDate',columns='instrument',values='member').fillna(False)
 member=snap.reindex(snap.index.union(days)).sort_index().ffill().reindex(days).reindex(columns=symbols).fillna(False).astype(bool)
 market_path=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/sources/000300.SH.parquet')
 mr=market_path.with_suffix('.receipt.json');receipt=json.loads(mr.read_text());assert sha(Path(receipt['path']))==receipt['sha256']
 raw=json.loads(Path(receipt['path']).read_text())['data'];market=pd.DataFrame(raw['items'],columns=raw['fields']);market['date']=pd.to_datetime(market.trade_date);market=market.set_index('date').reindex(days)
 market['close']=pd.to_numeric(market.close);market['open']=pd.to_numeric(market.open)
 f=compute(mats['qfq_close'],mats['qfq_open'],mats['qfq_high'],mats['qfq_low'],mats['volume'],mats['money'],mats['turnover_rate'],member,market.close)
 core=dictionary().query("group=='core'").feature.tolist()
 weekly_index=members.loc[members.signal_date.isin(signals),['signal_date','instrument']].drop_duplicates().set_index(['signal_date','instrument']).index
 def flatten(x):
  a=x.reindex(signals).rename_axis(index='signal_date',columns='instrument').stack(dropna=False)
  return a.reindex(weekly_index)
 panel=pd.DataFrame({k:flatten(x) for k,x in f.items()});panel['score_eligible']=flatten(mats['qfq_close'].notna().rolling(60).sum().ge(60)) & panel[core].notna().mean(axis=1).ge(.8)
 panel['missing_reason']=np.where(panel.score_eligible,'','INSUFFICIENT_PAST_HISTORY_OR_FEATURES')
 panel['residual_score']=flatten(monthly_residual_score(mats['qfq_close'],market.close))
 panel=panel.reset_index(); panel.to_parquet(PRIVATE/'features.parquet',index=False)
 labels=panel[['signal_date','instrument']].copy()
 for H,delay in [(5,0),(10,0),(20,0),(10,1)]:
  tag=f'h{H}'+('_delay1' if delay else '')
  entry=mats['qfq_open'].shift(-(1+delay));exit=mats['qfq_open'].shift(-(1+delay+H))
  labels[tag]=flatten(exit/entry-1).to_numpy()
  pos=days.get_indexer(pd.DatetimeIndex(labels.signal_date));ix=pos+1+delay+H
  labels[tag+'_mature']=pd.to_datetime([days[i] if i<len(days) else pd.NaT for i in ix])
 labels['entry_date']=[days[i+1] if i+1<len(days) else pd.NaT for i in days.get_indexer(pd.DatetimeIndex(labels.signal_date))]
 labels['target_z']=labels.groupby('signal_date').h10.transform(zscore)
 labels.to_parquet(PRIVATE/'labels.parquet',index=False)
 for k,v in mats.items():v.to_parquet(PRIVATE/(k+'.parquet'))
 member.to_parquet(PRIVATE/'daily_members.parquet');market[['open','close']].to_parquet(PRIVATE/'market.parquet')
 pd.DataFrame(audit).to_csv(OUT/'data_audit/security_coverage.csv',index=False)
 coverage=panel.groupby('signal_date').agg(original_members=('instrument','size'),score_eligible=('score_eligible','sum'))
 coverage['known_h10']=labels.groupby('signal_date').h10.count();coverage['unknown_h10']=coverage.original_members-coverage.known_h10
 coverage['mature_h10']=labels.groupby('signal_date').h10_mature.count();coverage['unmature_h10']=coverage.original_members-coverage.mature_h10;coverage['unknown_mature_h10']=coverage.mature_h10-coverage.known_h10
 coverage.to_csv(OUT/'data_audit/weekly_coverage.csv')
 save_json(OUT/'manifests/data_snapshot.json',dict(ep30_root=str(root),ep30_manifest_sha256=sha(root/'FULL_MANIFEST.json'),consumed_files=used,features_sha256=sha(PRIVATE/'features.parquet'),labels_sha256=sha(PRIVATE/'labels.parquet'),membership_sha256=sha(PRIVATE/'members/weekly.parquet'),market_raw_sha256=receipt['sha256'],market_normalized_sha256=sha(PRIVATE/'market.parquet'),date_min=str(days.min()),date_max=str(days.max()),membership_identity='Historical-proxy; weekly updateDate not exact intraday announcement vintage'))
 print('panel',panel.shape,'eligible',panel.score_eligible.sum(),flush=True)
if __name__=='__main__':main()
