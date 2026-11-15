"""Replay original financing aggregation/models/selection/exits on corrected inputs."""
import shutil
import pandas as pd
from common import *
import margin_factor_r45,margin_models_r46,classifiers_margin_r47,evaluate_classifiers_margin_r47,margin_selection_r47,exits_margin_r48

def run():
 out=ROOT/'outputs/r143';root=out/'evaluation';paths={'data/monthly_panel.parquet':ROOT/'outputs/r130/monthly_panel.parquet'}
 for p in ['data/l1_monthly_panel.parquet','data/l1_assignments.parquet','data/r30_size_control.parquet']+[f'protocols/r{x}.json' for x in [45,46,47,48]]+[f'src/{s}.py' for s in ['common','train_r02','followup_r10','evaluate_size_r31','margin_models_r46','classifiers_margin_r47','evaluate_classifiers_margin_r47']]:paths[p]=ROOT/p
 for dest,source in paths.items():
  p=root/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 (root/'outputs').mkdir(exist_ok=True)
 for module in [margin_factor_r45,margin_models_r46,classifiers_margin_r47,evaluate_classifiers_margin_r47,margin_selection_r47,exits_margin_r48]:module.ROOT=root;module.run()
 results=[]
 for family in ['r46','r47']:
  a=pd.read_parquet(ROOT/f'outputs/{family}/predictions.parquet');b=pd.read_parquet(root/f'outputs/{family}/predictions.parquet');keys=KEY+['date','horizon','year','method']+(['task'] if family=='r47' else []);pair=a.merge(b,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_parquet(out/f'{family}_prediction_pairs.parquet',index=False);shared=pair[pair._merge.eq('both')]
  fk=['era','level','horizon','year']+(['task'] if family=='r47' else []);fa=pd.DataFrame(json.loads((ROOT/'outputs/r46/fold_ledger.json').read_text())) if family=='r46' else pd.read_csv(ROOT/'outputs/r47/fold_ledger.csv');fb=pd.DataFrame(json.loads((root/'outputs/r46/fold_ledger.json').read_text())) if family=='r46' else pd.read_csv(root/'outputs/r47/fold_ledger.csv');fp=fa.merge(fb,on=fk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');fp.to_csv(out/f'{family}_fold_comparison.csv',index=False)
  results.append(dict(family=family,old_rows=len(a),new_rows=len(b),added=int(pair._merge.eq('right_only').sum()),removed=int(pair._merge.eq('left_only').sum()),changed_predictions=int((shared.prediction_new-shared.prediction_old).abs().gt(1e-12).sum()),max_prediction_change=float((shared.prediction_new-shared.prediction_old).abs().max()),fold_status_changes=int(fp.status_old.ne(fp.status_new).sum()),models=len(json.loads((root/f'outputs/{family}/model_parameters.json').read_text()))))
 a=pd.read_parquet(ROOT/'data/r45_financing_intensity.parquet');b=pd.read_parquet(root/'data/r45_financing_intensity.parquet');pair=a.merge(b,on=KEY+['date'],how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_parquet(out/'factor_pairs.parquet',index=False)
 js(out/'summary.json',dict(results=results,factor_old_rows=len(a),factor_new_rows=len(b),factor_added=int(pair._merge.eq('right_only').sum()),factor_removed=int(pair._merge.eq('left_only').sum()),reads={str(p):sha(p) for p in list(paths.values())+[Path(__file__),ROOT/'protocols/r143.json']+[ROOT/f'src/{s}.py' for s in ['margin_factor_r45','margin_selection_r47','exits_margin_r48']]},quality='Historical-proxy fixed original financing branch'))
 print(results,flush=True)
if __name__=='__main__':run()
