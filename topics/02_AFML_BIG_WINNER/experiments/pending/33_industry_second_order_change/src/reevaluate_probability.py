"""Honor R12's exact 26-week primary bootstrap without modifying sealed predictor code."""
import json,shutil
from pathlib import Path
import probability_pool as engine
from pool_evaluation import EP,sha

def main():
    original=engine.block_interval
    def contract_interval(z,dates,block=26):
        return original(z,dates,26 if block==25 else block)
    engine.block_interval=contract_interval
    for name in ['r12','r13']:
        out=EP/'outputs'/name;archive=EP/'revisions/20261111_probability_bootstrap_25_to_26'/name
        archive.mkdir(parents=True,exist_ok=True)
        for f in ['summary.csv','annual.csv','calibration_bins.csv','scored_outcomes.parquet','momentum_controls.csv.gz','weekly_metrics.csv.gz','evaluation_receipt.json','validation.json']:
            if (out/f).exists() and not (archive/f).exists():shutil.copy2(out/f,archive/f)
        engine.OUT=out;engine.evaluate()
        receipt=json.loads((out/'evaluation_receipt.json').read_text());receipt.update(evaluation_wrapper=str(Path(__file__).resolve()),wrapper_sha256=sha(__file__),primary_bootstrap_weeks=26,correction='Replaced round(126/5)=25 with frozen 26-week primary block; predictions unchanged; old outputs archived.')
        (out/'evaluation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
