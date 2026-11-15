import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r47';receipt=json.loads((out/'selection_receipt.json').read_text())
 for path,digest in receipt['inputs'].items():assert sha(Path(path))==digest
 cols=KEY+['date','price_ready','members']+F[:-1];p=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=cols)]);p['log_members']=np.log(p.members)
 p=p.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet',columns=KEY+['date','size_control']),on=KEY+['date'],how='left').merge(pd.read_parquet(ROOT/'data/r45_financing_intensity.parquet',columns=KEY+['date','financing_intensity']),on=KEY+['date'],how='left');p=p[p.price_ready&p[F+['size_control']].notna().all(axis=1)]
 table=pd.read_parquet(out/'selection_by_date.parquet');samples=pd.concat([g.iloc[np.linspace(0,len(g)-1,4,dtype=int)] for _,g in table.groupby(['era','level'])])
 for x in samples.to_dict('records'):
  g=p[p.era.eq(x['era'])&p.level.eq(x['level'])&p.date.eq(x['date'])];sizes=g.size_control.to_numpy();ranks=np.array([(np.sum(sizes<v)+(np.sum(sizes==v)+1)/2)/len(sizes) for v in sizes]);selected=g.financing_intensity.notna().to_numpy()
  assert sum(selected)==x['selected'] and sum(~selected)==x['other']
  assert abs(ranks[selected].mean()-x['selected_mean_size_rank'])<1e-12 and abs(ranks[~selected].mean()-x['other_mean_size_rank'])<1e-12
 for x in json.loads((out/'selection_summary.json').read_text()):
  g=table[table.era.eq(x['era'])&table.level.eq(x['level'])];assert len(g)==x['dates'] and abs(g.size_rank_gap.mean()-x['mean_rank_gap'])<1e-12
 js(out/'selection_verification.json',dict(status='PASS',direct_date_rank_checks=len(samples),summary_groups=5,scope='coverage size differences only; not corrected selection bias'))
 print('R47 selection verified',len(samples),'dates')

if __name__=='__main__':run()
