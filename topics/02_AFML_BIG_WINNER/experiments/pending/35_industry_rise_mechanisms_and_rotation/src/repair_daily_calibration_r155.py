"""Replay the unchanged daily process and calibration protocols on repaired inputs."""
import importlib
import shutil
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r155';root=out/'evaluation';cache=root/'cache'
 modules=['process_replay_r09','verify_process','daily_calibration_r97','verify_daily_calibration_r97','calibrated_alerts_r98','verify_calibrated_alerts_r98','calibration_uncertainty_r99','verify_calibration_uncertainty_r99']
 sources={f'protocols/r{x:02d}.json':ROOT/f'protocols/r{x:02d}.json' for x in [9,97,98,99]}
 sources.update({f'src/{x}.py':ROOT/f'src/{x}.py' for x in modules+['build_panel','train_r02']})
 sources.update({f'outputs/r02/{x}':ROOT/f'outputs/r131/{x}' for x in ['model_parameters.json','predictions.parquet']})
 sources['cache/forecast_v5/daily_industries.parquet']=ROOT/'outputs/r129/daily_2026-10-21.parquet'
 sources['cache/forecast_v5/CSI_ALL.parquet']=CACHE/'forecast_v5/CSI_ALL.parquet'
 for rel,source in sources.items():
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dst)
 d=pd.read_parquet(cache/'forecast_v5/daily_industries.parquet');calendar=pd.read_parquet(cache/'forecast_v5/CSI_ALL.parquet').index
 ordinal={date:i for i,date in enumerate(calendar)}
 legacy=pd.read_parquet(CACHE/'forecast_v5/daily_industries.parquet',columns=['date','day_i']);assert legacy.day_i.eq(legacy.date.map(ordinal)).all()
 d['day_i']=d.date.map(ordinal);assert d.day_i.notna().all();d.to_parquet(cache/'forecast_v5/daily_industries.parquet',index=False)
 (root/'data').mkdir(exist_ok=True);(root/'outputs/r09').mkdir(exist_ok=True)
 js(out/'input_receipt.json',dict(reads={str(p):sha(p) for p in list(sources.values())+[ROOT/'protocols/r155.json',Path(__file__)]},copies={rel:sha(root/rel) for rel in sources}))
 for name in modules:
  print('RUN',name,flush=True);mod=importlib.import_module(name);mod.ROOT=root;mod.CACHE=cache;mod.run()
 js(out/'execution_receipt.json',dict(status='PASS',modules=modules,verification_hashes={str(p):sha(p) for p in root.glob('outputs/*/verification.json')}))
if __name__=='__main__':run()
