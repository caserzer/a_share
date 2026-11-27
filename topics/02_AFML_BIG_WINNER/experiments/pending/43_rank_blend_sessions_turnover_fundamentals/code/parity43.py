from accounts43 import *
import json
def main():
    o=O/'summary';rows=[]
    for pool,arm,ref_path,filters in [(300,'W/R',E/'state/results/main/daily.parquet',[('arm','=','R')]),(300,'B/T',E/'state/results/main/daily.parquet',[('arm','=','T')]),(300,'B/T69',E/'scale/results/daily.parquet',[('arm','=','mse69'),('fee_multiple','=',1)]),(300,'B/T69d',E/'scale/results/daily.parquet',[('arm','=','shallow'),('fee_multiple','=',1)]),(800,'W/R',EP41/'p1/results/daily.parquet',[('kind','=','strict'),('phase','=',-1),('model','=','refit'),('bucket','=','decile')]),(800,'W/head',EP41/'p1/results/daily.parquet',[('kind','=','strict'),('phase','=',-1),('model','=','refit'),('bucket','=','head')])]:
        x=pd.read_parquet(O/f'accounts/{pool}/{arm}/daily.parquet',filters=[('multiple','=',1)]);y=pd.read_parquet(ref_path,filters=filters)
        y['segment']=y.segment.replace({'primary':1,'later':2}).astype(int)
        keys=['segment','date'];a=x.set_index(keys);b=y.set_index(keys)
        assert a.index.difference(b.index).empty and b.index.difference(a.index).empty,(pool,arm,len(a),len(b),a.index[:1],b.index[:1])
        for col in ['nav','cash','fee','crossed','buy','sell']:
            err=(a[col]-b[col]).abs().max();rows.append((pool,arm,col,len(a),err));assert err<1e-8,(pool,arm,col,err)
    pd.DataFrame(rows,columns='pool arm field days max_error'.split()).to_csv(o/'baseline_parity.csv',index=False)
    x=pd.concat(pd.read_parquet(p,filters=[('pool','=',300)],columns=KEY+['T69','T69d']) for p in (O/'models').glob('*.parquet'))
    y=pd.read_parquet(E/'scale/results/model_scores.parquet',columns=KEY+['mse69','shallow'])
    x=y.merge(x,on=KEY,validate='1:1');assert len(x)==len(y)
    y=pd.DataFrame([(a,len(x),(x[a]-x[b]).abs().max()) for a,b in [('T69','mse69'),('T69d','shallow')]],columns=['arm','matched_rows','max_error']);y.to_csv(o/'tree_parity.csv',index=False);assert y.max_error.max()<1e-8
if __name__=='__main__':main()
