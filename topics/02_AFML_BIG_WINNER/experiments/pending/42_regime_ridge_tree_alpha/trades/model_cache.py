"""Regenerate the ephemeral EP41 model inputs without writing into EP41 results."""
from pathlib import Path
import subprocess, sys, tempfile
def ensure():
    cache=Path('/tmp/ep41_model_inputs_v1')
    if (cache/'panel.parquet').exists():return
    models=next(Path(__file__).resolve().parents[2].glob('41_*/models'))
    with tempfile.TemporaryDirectory(prefix='ep42-model-cache-') as scratch:
        code="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import prepare_inputs as p;p.OUT=Path(sys.argv[2]);p.main()"
        subprocess.run([sys.executable,'-c',code,str(models),scratch],check=True)
    if not (cache/'panel.parquet').exists():raise RuntimeError('EP41 reconstruction did not emit the model panel')
if __name__=='__main__':ensure()
