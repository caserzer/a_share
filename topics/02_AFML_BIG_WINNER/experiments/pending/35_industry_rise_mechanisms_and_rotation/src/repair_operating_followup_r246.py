from common import *
import pandas as pd
import shutil,importlib

def run():
 out=ROOT/'outputs/r246';root=out/'evaluation';out.mkdir(exist_ok=True)
 sources={
 'outputs/r73/industry_evidence.json':ROOT/'outputs/r147/evaluation/outputs/r73/industry_evidence.json',
 'outputs/r73/member_evidence.parquet':ROOT/'outputs/r147/evaluation/outputs/r73/member_evidence.parquet',
 'outputs/r72/selected_fields.parquet':ROOT/'outputs/r72/selected_fields.parquet',
 'outputs/r93/task_evidence.parquet':ROOT/'outputs/r147/task_evidence.parquet',
 'data/r10_alert_followup.parquet':ROOT/'outputs/r156/evaluation/data/r10_alert_followup.parquet',
 'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet'}
 for n in [94,95,96]:sources[f'protocols/r{n}.json']=ROOT/f'protocols/r{n}.json';(root/f'outputs/r{n}').mkdir(parents=True,exist_ok=True)
 for rel,path in sources.items():dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dst)
 modules=['disclosed_period_r94','verify_disclosed_period_r94','alert_accounting_r95','verify_alert_accounting_r95','accounting_pairs_r96','verify_accounting_pairs_r96']
 for name in modules:
  mod=importlib.import_module(name);mod.ROOT=root;mod.run()
 old=pd.read_parquet(ROOT/'outputs/r95/alerts.parquet');new=pd.read_parquet(root/'outputs/r95/alerts.parquet');keys=KEY+['date','strategy'];q=old.merge(new,on=keys,how='outer',validate='one_to_one',suffixes=('_old','_new'),indicator=True);q.to_parquet(out/'alert_comparison.parquet',index=False);shared=q[q._merge.eq('both')];changes={}
 for col in ['accounting_snapshot','accounting_period','accounting_status','accounting_group','accounting_coherence','excess20','return20','continuation_excess20_60','breadth_change20']:
  a=shared[col+'_old'];b=shared[col+'_new'];numeric=col in ['accounting_coherence','excess20','return20','continuation_excess20_60','breadth_change20'];equal=np.isclose(a,b,atol=1e-12,rtol=1e-10,equal_nan=True) if numeric else a.eq(b)|(a.isna()&b.isna());changes[col]=dict(changed=int((~equal).sum()),known_to_unknown=int((a.notna()&b.isna()).sum()),unknown_to_known=int((a.isna()&b.notna()).sum()))
 summaries={}
 for n,key in [(95,['era','level','strategy','accounting_group','metric']),(96,['era','level','metric'])]:
  a=pd.DataFrame(json.loads((ROOT/f'outputs/r{n}/summary.json').read_text()));b=pd.DataFrame(json.loads((root/f'outputs/r{n}/summary.json').read_text()));z=a.merge(b,on=key,how='outer',validate='one_to_one',suffixes=('_old','_new'),indicator=True);z.to_csv(out/f'r{n}_summary_comparison.csv',index=False);summaries[n]=dict(old_rows=len(a),new_rows=len(b),identity_counts=z._merge.value_counts().to_dict())
 ledger_old=pd.DataFrame(json.loads((ROOT/'outputs/r96/date_ledger.json').read_text()));ledger_new=pd.DataFrame(json.loads((root/'outputs/r96/date_ledger.json').read_text()));z=ledger_old.merge(ledger_new,on=['era','level','date'],how='outer',suffixes=('_old','_new'),validate='one_to_one',indicator=True);z.to_csv(out/'paired_date_ledger_comparison.csv',index=False)
 stats=dict(old_alerts=len(old),new_alerts=len(new),identities=q._merge.value_counts().to_dict(),shared_changes=changes,old_known=int(old.accounting_coherence.notna().sum()),new_known=int(new.accounting_coherence.notna().sum()),old_periods=sorted(old.accounting_period.dropna().unique()),new_periods=sorted(new.accounting_period.dropna().unique()),old_monthly=int(old.strategy.eq('monthly').sum()),new_monthly=int(new.strategy.eq('monthly').sum()),old_paired_dates=int(ledger_old.paired.sum()),new_paired_dates=int(ledger_new.paired.sum()),summaries=summaries)
 js(out/'comparison.json',stats)
 reads=list(sources.values())+[ROOT/'protocols/r246.json',Path(__file__)]+[ROOT/f'src/{name}.py' for name in modules]
 js(out/'verification.json',dict(status='PASS',original_independent_verifiers_passed=[94,95,96],inputs={str(p):sha(p) for p in reads},outputs={str(p.relative_to(out)):sha(p) for p in [out/'comparison.json',out/'alert_comparison.parquet',out/'r95_summary_comparison.csv',out/'r96_summary_comparison.csv',out/'paired_date_ledger_comparison.csv']+[root/f'outputs/r{n}/verification.json' for n in [94,95,96]]},adoption=False,new_economic_periods=False));print(json.dumps(stats,ensure_ascii=False,default=str))
if __name__=='__main__':run()
