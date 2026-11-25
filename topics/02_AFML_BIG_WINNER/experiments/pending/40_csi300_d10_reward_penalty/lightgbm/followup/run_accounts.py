from accounts_followup import *
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from tempfile import TemporaryDirectory
import pyarrow as pa
import pyarrow.parquet as pq

def run(task):
    scope,arm,h,phase,delay,mul=task
    e0,end=BOUNDS[scope]
    entries=range(e0+phase,end-h-delay+1,h)
    plan={e+delay:TARGET[e][arm] for e in entries}
    orig=(h,phase,delay,mul)==(10,0,0,1)
    detailed=orig and not arm.startswith('P') or (h==10 and delay==0 and mul==1 and arm in ['R','T','B','A','X11'])
    try:w,d,p,o=replay(M,ACT,plan,h,mul,True)
    except ValueError as exc:return task,str(exc)
    meta=dict(scope=scope,arm=arm,h=h,phase=phase,delay=delay,mul=mul)
    def frame(rows,cols):return pd.DataFrame(rows,columns=cols.split()).assign(**meta)
    if not detailed:
        trial=TRADES/f'{scope}_{arm}_h{h}_p{phase}_d{delay}_c{mul}'
        trial.mkdir(exist_ok=True,parents=True)
        for data,cols,name in [(p,'entry_idx instrument target weight gross fee','positions'),(o,'idx instrument net_amount pretrade_nav','orders')]:
            pd.DataFrame(data,columns=cols.split()).to_parquet(trial/(name+'.parquet'),index=False,compression='zstd')
        p,o=[],[]
    return task,[frame(w,'entry_idx net fee turnover'),frame(d,'idx date nav cash buy sell fees'),frame(p,'entry_idx instrument target weight gross fee'),frame(o,'idx instrument net_amount pretrade_nav')]

def pack(source):
    for name in ['positions','orders']:
        path=DEST/('supplementary_'+name+'.parquet')
        writer=None
        try:
            for f in sorted(source.glob('*/'+name+'.parquet')):
                scope,arm,h,ph,delay,rate=f.parent.name.split('_')
                g=pd.read_parquet(f).assign(scope=scope,arm=arm,h=int(h[1:]),phase=int(ph[1:]),delay=int(delay[1:]),mul=int(rate[1:]))
                table=pa.Table.from_pandas(g,preserve_index=False)
                if writer is None:writer=pq.ParquetWriter(path,table.schema,compression='zstd')
                writer.write_table(table)
        finally:
            if writer:writer.close()

def main():
    global M,ACT,BOUNDS,TARGET,TRADES
    temp=TemporaryDirectory(prefix='ep40-order-shards-')
    TRADES=Path(temp.name)
    ledger.accounts.OUT=DEST
    M,ACT=ledger.setup('flat')
    days=M.days
    bounds=[days.get_loc(d) for d in ['2021-01-11','2025-03-03','2026-10-12']]
    BOUNDS=dict(primary=bounds[:2],later=bounds[1:])
    scores=pd.read_parquet(DEST/'daily_scores.parquet')
    folds=pd.concat([pd.read_parquet(f) for f in sorted((DEST/'folds').glob('*.parquet'))])
    assert len(folds)==40756
    scores=scores.merge(folds,how='left',on=KEY,validate='1:1')
    base=scores[(scores.entry_idx-bounds[0])%10==0]
    inds=industries(base.signal_date.unique())
    TARGET={}
    for e,g in scores.groupby('entry_idx'):
        full=(e-bounds[0])%10==0 and e<=bounds[-1]-10
        if full:g=g.assign(industry=g.instrument.map(inds[g.signal_date.iloc[0]]).fillna('未知'))
        targets=picks(g,full)
        TARGET[e]={a:M.symbols.get_indexer(v) for a,v in targets.items()}
        assert all(min(v)>=0 for v in TARGET[e].values())
    tasks=[]
    for scope in BOUNDS:
        tasks.extend((scope,a,10,0,0,1) for a in TARGET[bounds[0]])
        for a in ['R','T','B','A','X11']:
            tasks.extend((scope,a,10,ph,0,1) for ph in range(1,10))
            tasks.extend((scope,a,h,0,0,1) for h in [5,20])
            tasks.extend((scope,a,10,0,0,m) for m in [0,2])
            tasks.append((scope,a,10,0,1,1))
    bins=[[] for _ in range(4)];errors=[]
    with ProcessPoolExecutor(8,mp_context=get_context('fork')) as pool:
        for task,result in pool.map(run,tasks,chunksize=3):
            if isinstance(result,str):errors.append((*task,result));continue
            for b,df in zip(bins,result):
                if len(df):b.append(df)
    for b,name in zip(bins,['windows','daily','positions','orders']):
        pd.concat(b,ignore_index=True).to_parquet(DEST/(name+'.parquet'),index=False)
    pack(TRADES)
    temp.cleanup()
    pd.DataFrame(errors,columns='scope arm h phase delay mul error'.split()).to_csv(DEST/'failures.csv',index=False)
if __name__=='__main__':main()
