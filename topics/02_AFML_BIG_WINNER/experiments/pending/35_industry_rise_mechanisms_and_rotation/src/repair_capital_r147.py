import shutil
import pandas as pd
from common import *
import capital_coverage_r68,capital_monthly_r73,capital_monitor_r74,capital_cashflow_r69,capital_profit_r70,capital_controls_r71

def run():
 out=ROOT/'outputs/r147';root=out/'evaluation';root.mkdir(parents=True,exist_ok=True)
 paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet'}
 for rel in ['data/l1_monthly_panel.parquet','data/l1_assignments.parquet','outputs/r67/same_period_pairs.json','outputs/r72/company_pairs.parquet','outputs/r63/evidence_matrix.parquet','outputs/r67/selected_facts.json','data/financial_archive_all_market.parquet']+[f'protocols/r{x}.json' for x in [68,69,70,71,73,74]]:paths[rel]=ROOT/rel
 for rel,p in paths.items():
  dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 mods=[capital_coverage_r68,capital_cashflow_r69,capital_profit_r70,capital_controls_r71,capital_monthly_r73,capital_monitor_r74]
 for m in mods:m.ROOT=root;m.run()
 comparisons=[]
 for rel in ['outputs/r68/member_links.parquet','outputs/r73/member_evidence.parquet','outputs/r74/evidence_matrix.parquet']:
  a=pd.read_parquet(ROOT/rel);b=pd.read_parquet(root/rel);same=a.equals(b);comparisons.append(dict(path=rel,old=len(a),new=len(b),exactly_equal=same))
 for rel in ['outputs/r68/industry_coverage.json','outputs/r68/summary.json','outputs/r73/industry_evidence.json','outputs/r73/summary.json','outputs/r74/monthly_observations.json','outputs/r74/coverage.json']:
  a=json.loads((ROOT/rel).read_text());b=json.loads((root/rel).read_text());comparisons.append(dict(path=rel,old=len(a),new=len(b),exactly_equal=a==b))
 js(out/'summary.json',dict(comparisons=comparisons,reads={str(p):sha(p) for p in list(paths.values())+[Path(__file__),ROOT/'protocols/r147.json']+[Path(m.__file__) for m in mods]},quality='Historical-proxy; operating evidence only'))
 print(json.dumps(comparisons))
if __name__=='__main__':run()
