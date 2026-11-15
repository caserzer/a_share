import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r83';out.mkdir(exist_ok=True);ap=ROOT/'outputs/r82/stock_audit.parquet';ip=ROOT/'outputs/r82/intervals.json';d=pd.read_parquet(ap);iv={(x['method'],pd.Timestamp(x['origin'])):x for x in json.loads(ip.read_text())};rows=[]
 for key,g in d.groupby(['method','origin']):
  v=iv[key];good=g[g.endpoint_valued];bad=g[~g.endpoint_valued];ui=float(v['unknown_weight']);up=float(bad.weight.sum());u=ui+up;k=float((good.weight*(good.exit_price/good.entry_price-1)).sum());w=float(good.weight.sum());assert np.isclose(w+u,1)
  ref=v['r17_gross'];complete=bool(v['endpoint_valued']);critical=(ref-k)/u if u>1e-12 and ref is not None else None
  rows.append(dict(method=key[0],origin=key[1],known_weight=w,unknown_identity_weight=ui,unknown_price_weight=up,unknown_total_weight=u,known_return_contribution=k,complete=complete,complete_return=k if complete else None,r17_gross=ref,required_unknown_return_to_match_r17=critical,conditional_long_only_lower=k-u,conditional_lower_minus_r17=k-u-ref if ref is not None else None,unknown_return_1pp_effect_pp=u*.01*100))
 js(out/'intervals.json',rows);summary=[]
 for method in sorted(d.method.unique()):
  g=pd.DataFrame([x for x in rows if x['method']==method]);summary.append(dict(method=method,intervals=len(g),complete=int(g.complete.sum()),unknown_identity_weight_mean=float(g.unknown_identity_weight.mean()),unknown_price_weight_mean=float(g.unknown_price_weight.mean()),unknown_total_weight_mean=float(g.unknown_total_weight.mean()),unknown_total_weight_median=float(g.unknown_total_weight.median()),unknown_total_weight_max=float(g.unknown_total_weight.max()),conditional_lower_above_r17_count=int(g.conditional_lower_minus_r17.gt(1e-12).sum()),critical_unknown_return_below_minus_one=int(g.required_unknown_return_to_match_r17.lt(-1-1e-12).sum()),worst_coverage_origin=g.loc[g.unknown_total_weight.idxmax(),'origin']))
 js(out/'summary.json',summary);inputs=[ap,ip,ROOT/'outputs/r82/verification.json',ROOT/'protocols/r83.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},no_imputation=True,no_return_curve=True));print(json.dumps(clean(summary),ensure_ascii=False,default=str))
if __name__=='__main__':run()
