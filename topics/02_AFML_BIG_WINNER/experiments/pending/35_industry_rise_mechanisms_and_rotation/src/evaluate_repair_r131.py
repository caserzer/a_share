"""Run the unchanged original evaluator in an isolated output root."""
import shutil
import pandas as pd
from common import *
import evaluate_r02


def run():
    out=ROOT/'outputs/r131';sandbox=out/'evaluation';dest=sandbox/'outputs/r02';dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(out/'predictions.parquet',dest/'predictions.parquet')
    js(dest/'run_receipt.json',dict(prediction_sha256=sha(dest/'predictions.parquet')))
    evaluate_r02.ROOT=sandbox;evaluate_r02.run()
    keys=['era','level','cohort','task','horizon'];old=pd.read_csv(ROOT/'outputs/r02/paired_increments.csv');new=pd.read_csv(dest/'paired_increments.csv')
    pair=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair.to_csv(out/'increment_comparison.csv',index=False)
    primary=pair[pair.horizon.eq(20)];changes=primary[primary.result_old.ne(primary.result_new)]
    reads={str(p):sha(p) for p in [out/'predictions.parquet',ROOT/'outputs/r02/paired_increments.csv',ROOT/'src/evaluate_r02.py',ROOT/'src/evaluate_r01.py',Path(__file__)]}
    js(out/'evaluation_summary.json',dict(reads=reads,paired_comparisons=len(pair),primary_comparisons=len(primary),primary_conclusion_changes=changes[keys+['result_old','result_new']].to_dict('records'),max_primary_increment_change=float((primary.increment_new-primary.increment_old).abs().max()),primary_supported_old=int(primary.result_old.eq('historical_increment_supported').sum()),primary_supported_new=int(primary.result_new.eq('historical_increment_supported').sum()),evaluation_files={str(p.relative_to(out)):sha(p) for p in dest.iterdir() if p.is_file()},quality='Original historical repeated-use evaluation; not new holdout'))
    print('PRIMARY CHANGES',len(changes),flush=True)

if __name__=='__main__':run()
