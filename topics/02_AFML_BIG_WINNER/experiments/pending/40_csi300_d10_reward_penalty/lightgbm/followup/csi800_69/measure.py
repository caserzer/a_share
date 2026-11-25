from inputs import *
from hashlib import sha256
import subprocess
def digest(p):
    h=sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
    return h.hexdigest()

def main():
    strict=pd.read_parquet(OUT800/'strict_daily.parquet').query('path=="common"').assign(proxy='strict')
    stress=pd.read_parquet(OUT800/'sensitivity_daily.parquet').assign(segment=0)
    allpaths=pd.concat([strict,stress])
    cal=pd.read_parquet(PRIVATE/'market.parquet',columns=[]).index
    d0,d1=map(pd.Timestamp,['2021-01-11','2026-10-12'])
    cal=cal[(cal>=d0)&(cal<=d1)]
    idx=pd.read_parquet(STORE/'index800.parquet');bench=idx.set_index(pd.to_datetime(idx.trade_date)).close
    rows=[];segments=[];months=[]
    def record(g,base,idxbase,meta,dest):
        ret=(g.iloc[-1]/base-1)*100
        dest.append(dict(**meta,start=g.index.min().date(),end=g.index.max().date(),n=len(g),ridge=ret.R,swap=ret.swap,excess=ret.swap-ret.R,index800=100*(bench.at[g.index[-1]]/bench.at[idxbase]-1)))
    for (proxy,size,mode),group in allpaths.groupby(['proxy','size','mode']):
        common=dict(proxy=proxy,size=size,mode=mode);paths=[]
        for (scope,seg),g in sorted(group.groupby(['scope','segment']),key=lambda kv:kv[1].date.min()):
            v=g.pivot(index='date',columns='arm',values='nav').sort_index()
            record(v,1,v.index[0],dict(**common,scope=scope,segment=seg),segments)
            if paths and paths[-1].index[-1]==v.index[0]:
                prev=paths.pop();v=pd.concat([prev.iloc[:-1],v*prev.iloc[-1]])
            paths.append(v)
        for v in paths:
            for period,dates in [('all',cal)]+[(str(y),cal[cal.year==y]) for y in sorted(set(cal.year))]:
                first,last=dates[[0,-1]]
                start=first if first==d0 else cal[cal.get_loc(first)-1]
                if start>=v.index[0] and last<=v.index[-1]:
                    h=v.loc[first:last]
                    pd.testing.assert_index_equal(pd.Index(h.index.values),pd.Index(dates.values))
                    record(h,1 if first==d0 else v.loc[start],start,dict(**common,period=period),rows)
            for label,h in v.groupby(v.index.to_period('M')):
                prior=cal.get_loc(h.index[0])-1
                if prior<0 or cal[prior] not in v.index or label in [v.index[0].to_period('M'),v.index[-1].to_period('M')]:continue
                record(h,v.loc[cal[prior]],cal[prior],dict(**common,month=str(label)),months)
    for name,data in [('annual',rows),('segments',segments),('full_months',months)]:
        pd.DataFrame(data).to_csv(OUT800/(name+'.csv'),index=False)
    a=pd.DataFrame(rows);assert not a.duplicated(['proxy','size','mode','period']).any()
    sr=a.query('proxy=="strict"');assert set(sr.period)=={'2021','2022','2024','2025','2026'}
    assert len(sr)==30
    for _,g in a[a.proxy!='strict'].groupby(['proxy','size','mode']):
        for arm in ['ridge','swap','index800']:
            year=g[g.period!='all'];np.testing.assert_allclose((1+year[arm]/100).prod(),1+g.loc[g.period=='all',arm].item()/100)
    keys=['signal_date','instrument']
    s=pd.read_parquet(OUT800/'scores.parquet');assert not s.duplicated(keys).any() and np.isfinite(s.filter(regex='_(R|T)$')).all().all()
    cf=pd.read_csv(OUT800/'folds.csv')
    assert len(cf)==46 and (cf.latest_maturity<cf.first_signal).all()
    files=[LOCAL/'wide_features.parquet',STORE/'wide_scores.parquet',STORE/'effective800.parquet',STORE/'effective_changes.csv',STORE/'index800.parquet',
           *(LOCAL.glob('*.parquet')),*LOCAL.glob('limits/*.parquet'),*LOCAL.glob('suspensions/*.parquet'),
           *(PRIVATE/(n+'.parquet') for n in ['features','labels','market','daily_members']),DEST/'daily_scores.parquet',*sorted((DEST/'folds').glob('*.parquet')),
           *sorted((LINEAR/'models').glob('*.json')),HERE.parent/'stagger.py',*HERE.glob('*.py'),HERE/'PROTOCOL.md']
    receipt=dict(git=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),lightgbm=lgb.__version__,eligible_stock_days=len(s),signal_dates=s.signal_date.nunique(),overlap_tree_scores_checked=40700,model_pairs=len(cf),inputs={str(f):digest(f) for f in files},outputs={str(f.relative_to(OUT800)):digest(f) for f in OUT800.rglob('*') if f.is_file() and f.name!='verification.json'})
    (OUT800/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
