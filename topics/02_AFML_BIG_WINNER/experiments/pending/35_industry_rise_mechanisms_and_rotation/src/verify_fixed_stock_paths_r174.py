"""Independent raw-window and every-position verification of the L2 path gate."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r174';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 keys=['variant','era','level','method','origin'];a=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit']);detail=pd.read_parquet(out/'stock_interval_audit.parquet');pos=pd.read_parquet(ROOT/'outputs/r172/nominal_positions.parquet');pk=keys+['security_id'];pd.testing.assert_frame_equal(detail[pk+['weight']].sort_values(pk).reset_index(drop=True),pos[pk+['weight']].sort_values(pk).reset_index(drop=True));assert len(a)==len(pos[keys].drop_duplicates())
 cov=pd.read_csv(ROOT/'outputs/r172/concentration.csv',parse_dates=['origin']).set_index(keys);calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);d=detail.merge(a[keys+['entry','exit']],on=keys,validate='many_to_one');paths={Path(p).stem:Path(p) for p in receipt['price_partitions']};checked=0
 for sid,g in d.groupby('security_id'):
  p=paths[sid];assert sha(p)==receipt['price_partitions'][str(p)];f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id','volume','volume_conflict','can_buy','can_sell']).set_index('date').reindex(calendar);price=pd.to_numeric(f.qfq_close).to_numpy();ok=f.close_conflict.eq(False).to_numpy()&(price>0);ch=f.factor_chain_id.fillna('__MISSING__').to_numpy();buy=f.can_buy;sell=f.can_sell;volume=pd.to_numeric(f.volume);vok=(volume.gt(0)&f.volume_conflict.eq(False)).to_numpy()
  for (entry,exit),q in g.groupby(['entry','exit']):
   lo=calendar.get_loc(entry);hi=calendar.get_loc(exit);valid=bool(ok[lo:hi+1].all());chain=bool(ch[lo]!='__MISSING__' and all(x==ch[lo] for x in ch[lo:hi+1]));ep=bool(ok[lo] and ok[hi] and ch[lo]!='__MISSING__' and ch[lo]==ch[hi]);bu=0 if pd.isna(buy.iloc[lo]) else 1 if bool(buy.iloc[lo]) else 2;se=0 if pd.isna(sell.iloc[hi]) else 1 if bool(sell.iloc[hi]) else 2
   values=dict(price_valid=valid,chain_stable=chain,endpoint_valid=ep,entry_price=price[lo] if ok[lo] else np.nan,exit_price=price[hi] if ok[hi] else np.nan,buy_state=bu,sell_state=se,endpoint_volume_valid=bool(vok[lo] and vok[hi]))
   for name,value in values.items():assert np.isclose(q[name].to_numpy(),value,equal_nan=True).all(),(sid,entry,name)
   checked+=1
 groups={k:g for k,g in detail.groupby(keys)};original={}
 for variant,n in [('top10',169),('top20',137)]:
  t=pd.read_csv(ROOT/f'outputs/r{n}/evaluation/outputs/r04/intervals.csv',parse_dates=['origin','entry','exit']);original[variant]=t.set_index(['era','level','method','origin'])
 for row in a.to_dict('records'):
  key=tuple(row[k] for k in keys);g=groups[key];o=original[row['variant']].loc[key[1:]];assert row['entry']==o.entry and row['exit']==o.exit and row['synthetic_status']==o.status and np.isclose(row['synthetic_gross'],o.gross_return,equal_nan=True)
  u=cov.loc[key,'unknown_weight'];good=g.price_valid&g.chain_stable;ready=bool(u<1e-12 and good.all() and np.isclose(g.weight.sum(),1));ret=sum(w*e/b for w,e,b in zip(g.weight,g.exit_price,g.entry_price))-1 if ready else np.nan
  values=dict(stocks=len(g),unknown_weight=u,price_bad=(~g.price_valid).sum(),chain_bad=(~g.chain_stable).sum(),unvalued_known_weight=g.loc[~good,'weight'].sum(),full_path_valued=ready,endpoint_only_valued=bool(u<1e-12 and g.endpoint_valid.all()),fixed_stock_gross=ret,gross_difference=ret-o.gross_return if ready and pd.notna(o.gross_return) else np.nan,buy_unknown=g.buy_state.eq(0).sum(),sell_unknown=g.sell_state.eq(0).sum(),buy_disallowed=g.buy_state.eq(2).sum(),sell_disallowed=g.sell_state.eq(2).sum(),endpoint_volume_bad=(~g.endpoint_volume_valid).sum(),standalone_entry_exit_eligible=bool(ready and g.buy_state.eq(1).all() and g.sell_state.eq(1).all() and g.endpoint_volume_valid.all()))
  for name,value in values.items():assert np.isclose(row[name],value,equal_nan=True),(key,name)
 for row in pd.read_csv(out/'summary.csv').to_dict('records'):
  g=a[a.variant.eq(row['variant'])&a.era.eq(row['era'])&a.method.eq(row['method'])];q=g[g.full_path_valued]
  values=dict(planned=len(g),full_path_valued=len(q),endpoint_only_valued=g.endpoint_only_valued.sum(),unknown_identity=g.unknown_weight.ge(1e-12).sum(),price_gaps=g.price_bad.gt(0).sum(),chain_gaps=g.chain_bad.gt(0).sum(),standalone_eligible=g.standalone_entry_exit_eligible.sum(),comparison_complete=q.gross_difference.notna().sum(),mean_difference=q.gross_difference.mean(),min_difference=q.gross_difference.min(),max_difference=q.gross_difference.max(),whole_path_valid=g.full_path_valued.all())
  for name,value in values.items():assert np.isclose(row[name],value,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',intervals=len(a),position_rows=len(detail),unique_stock_windows=checked,source_partitions=len(paths),unknown_and_missing_preserved=True,no_net_curve=True,adoption=False))
 print('PASS R174',len(a),len(detail),checked)
if __name__=='__main__':run()
