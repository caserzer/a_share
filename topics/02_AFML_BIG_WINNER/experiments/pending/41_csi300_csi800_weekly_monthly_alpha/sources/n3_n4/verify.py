from pathlib import Path
import gzip,hashlib,json
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
def main():
    receipts=json.loads((OUT/'event_source_receipts.json').read_text())
    for r in receipts:
        assert hashlib.sha256(gzip.decompress((HERE/'raw/events'/r['file']).read_bytes())).hexdigest()==r['sha256']
    ah=json.loads((OUT/'source_receipts.json').read_text())
    assert hashlib.sha256((HERE/'raw/hkex_mapping.pdf').read_bytes()).hexdigest()==ah['mapping_sha256']
    for r in ah['bars']:
        if 'rows' in r:
            assert hashlib.sha256(gzip.decompress((HERE/'raw'/(r['ticker']+'.json.gz')).read_bytes())).hexdigest()==r['sha256']
    d=pd.read_parquet(OUT/'daily.parquet')
    ref=pd.read_parquet(HERE.parents[1]/'p2/results/funded_daily.parquet').query('arm=="rank" and mul==1')
    for name,g in d.query('rule=="covered_ridge"').groupby('test'):
        if name.endswith('covered_basket'):continue
        z=g.merge(ref,on=['date','scope'],validate='1:1')
        assert len(z)==len(ref)
        for c in ['nav','fee','cash','crossed']:np.testing.assert_allclose(z[c+'_x'],z[c+'_y'],atol=1e-11)
    orders=pd.read_parquet(OUT/'orders.parquet')
    keys=['scope','test','rule','idx']
    acct=d.set_index(keys)
    fees=orders.groupby(keys).fee.sum().reindex(acct.index,fill_value=0)
    np.testing.assert_allclose(fees,acct.fee,atol=1e-12)
    mo=pd.read_csv(OUT/'full_months.csv')
    rows=[]
    for (name,scope),g in mo.groupby(['test','scope']):
        x=g.pivot(index='month',columns='rule',values='net')
        v=(x.signal-x.covered_ridge).values*1e4
        rng=np.random.default_rng(4101)
        ix=rng.integers(0,len(v)-2,size=(10000,(len(v)+2)//3,1))+np.arange(3)
        a,b=np.quantile(v[ix.reshape(10000,-1)[:,:len(v)]].mean(axis=1),[.025,.975])
        rows.append(dict(test=name,scope=scope,n=len(v),average=v.mean(),low=a,high=b))
    pd.DataFrame(rows).to_csv(OUT/'intervals.csv',index=False)
    out=pd.read_parquet(OUT/'incoming_capital.parquet')
    for label in [1,10]:out['real_D'+str(label)]=out.bought*out.realized_decile.eq(label)
    out.groupby(['test','scope','rule','supported'])[['bought','planned','actual_value','real_D1','real_D10']].sum().to_csv(OUT/'capital_summary.csv')
    cmp=pd.read_csv(OUT/'same_day_industry_events.csv').query('size_matched')
    print('matched N3 pairs',len(cmp))
    for n in [5,10,20]:
        a=np.sign(cmp.SUE_x-cmp.SUE_y)*(cmp['h'+str(n)+'_x']-cmp['h'+str(n)+'_y'])
        print(n,len(a.dropna()),a.mean()*1e4)
if __name__=='__main__':main()
