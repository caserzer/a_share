from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
E=next(ROOT.parent.glob('42_*'))
sys.path.insert(0,str(E/'state'))
from core42 import *
from inputs42 import ci,CACHE
from engine import LOCAL,PRIVATE,OUT800
from mixture import Calibration
import yaml
CFG=yaml.safe_load((ROOT/'config.yaml').read_text())
O=ROOT/'outputs'
COL=ci.COLS
KEY=['signal_date','instrument','entry_idx']
def weekly(wide):
    if not wide:return ci.prepare().sort_values(ci.KEY).copy()
    f=pd.read_parquet(LOCAL/'wide_features.parquet')
    days=pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date.unique()
    f=f[f.weekly_ok & f.signal_date.isin(days)&f.h10.notna()].sort_values(ci.KEY).copy()
    g=f.groupby('signal_date').h10
    f['target_rank']=g.rank()/(g.transform('size')+1)-.5
    return f
def market_labels(df,wide):
    base=LOCAL if wide else PRIVATE
    op=pd.read_parquet(base/'qfq_open.parquet')
    cl=pd.read_parquet(base/'qfq_close.parquet')
    i=op.index.get_indexer(df.signal_date)+1;j=op.columns.get_indexer(df.instrument)
    assert i.min()>0 and j.min()>=0
    a=op.to_numpy();c=cl.to_numpy()
    intra=np.zeros(len(i));over=intra.copy()
    for k in range(10):
        intra+=np.log(c[i+k,j]/a[i+k,j]);over+=np.log(a[i+k+1,j]/c[i+k,j])
    total=np.log(a[i+10,j]/a[i,j])
    err=np.nanmax(abs(intra+over-total));assert err<1e-10
    df=df.assign(intra=intra,over=over,total=total,mature=op.index[i+10],entry_idx=i)
    ok=np.isfinite(intra+over+total)
    for name in ['intra','over','total']:
        g=df[name].where(ok).groupby(df.signal_date)
        df['y'+name]=g.rank()/(g.transform('count')+1)-.5
    return df,err
def read_features(q,wide):
    filt=[('signal_date','>=',q.start_time),('signal_date','<=',q.end_time)]
    fs=list((CACHE/'wide').glob('early_*.parquet')) if wide else list(CACHE.glob('block_*.parquet'))
    if wide and q.year>=2021:fs.append(E/'events/results/features'/f'{q}.parquet')
    return pd.concat(pd.read_parquet(f,columns=KEY+COL,filters=filt) for f in fs).sort_values(ci.KEY)
def frozen(wide):
    return pd.read_parquet(E/'state/results'/('wide_scores.parquet' if wide else 'scores.parquet'))
