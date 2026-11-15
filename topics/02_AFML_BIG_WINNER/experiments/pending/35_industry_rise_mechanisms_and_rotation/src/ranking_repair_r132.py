"""Unchanged R01 ranking evaluation in an isolated repaired-data root."""
import shutil
import pandas as pd
from common import *
import evaluate_r01

def run():
    out=ROOT/'outputs/r132';sandbox=out/'evaluation';dest=sandbox/'outputs/r01'
    for p in [dest,sandbox/'data',sandbox/'protocols',sandbox/'src']:p.mkdir(parents=True,exist_ok=True)
    source=ROOT/'outputs/r130/monthly_panel.parquet';shutil.copyfile(source,sandbox/'data/monthly_panel.parquet')
    shutil.copyfile(ROOT/'protocols/r01.json',sandbox/'protocols/r01.json')
    for name in ['evaluate_r01.py','common.py']:shutil.copyfile(ROOT/f'src/{name}',sandbox/f'src/{name}')
    js(dest/'panel_receipt.json',dict(sha256=sha(source),source=str(source),repair_protocol=sha(ROOT/'protocols/r132.json')))
    evaluate_r01.ROOT=sandbox;evaluate_r01.run()
    keys=['era','level','cohort','horizon'];old=pd.read_csv(ROOT/'outputs/r01/paired_increments.csv');new=pd.read_csv(dest/'paired_increments.csv')
    pair=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair.to_csv(out/'increment_comparison.csv',index=False)
    sk=['era','level','date','cohort','method','industry_code'];a=pd.read_parquet(ROOT/'outputs/r01/selections.parquet');b=pd.read_parquet(dest/'selections.parquet');selection=a.merge(b,on=sk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');selection.to_parquet(out/'selection_comparison.parquet',index=False)
    primary=pair[pair.horizon.eq(20)];changes=primary[primary.result_old.ne(primary.result_new)]
    reads={str(p):sha(p) for p in [source,ROOT/'outputs/r01/paired_increments.csv',ROOT/'outputs/r01/selections.parquet',ROOT/'protocols/r01.json',ROOT/'protocols/r132.json',ROOT/'src/evaluate_r01.py',ROOT/'src/common.py',Path(__file__)]}
    js(out/'receipt.json',dict(reads=reads,paired_comparisons=len(pair),primary_comparisons=len(primary),primary_conclusion_changes=changes[keys+['result_old','result_new']].to_dict('records'),primary_supported_old=int(primary.result_old.eq('historical_increment_supported').sum()),primary_supported_new=int(primary.result_new.eq('historical_increment_supported').sum()),max_primary_delta_ic_change=float((primary.delta_ic_new-primary.delta_ic_old).abs().max()),selection_added=int(selection._merge.eq('right_only').sum()),selection_removed=int(selection._merge.eq('left_only').sum()),selection_common_weight_changes=int((selection._merge.eq('both')&~np.isclose(selection.weight_old,selection.weight_new,atol=1e-12,rtol=1e-12,equal_nan=True)).sum()),outputs={str(p.relative_to(out)):sha(p) for p in dest.iterdir() if p.is_file()},quality='Historical-proxy fixed-ranking replay'))
    print('PRIMARY CHANGES',len(changes),flush=True)

if __name__=='__main__':run()
