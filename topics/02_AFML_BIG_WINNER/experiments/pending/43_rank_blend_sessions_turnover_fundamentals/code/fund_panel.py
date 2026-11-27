from ep43lib import *
from collections import defaultdict
import json
F=O/'fundamental';F.mkdir(exist_ok=True)
src=O/'sources'
A=['EP','BM','ROE','stable','cashprofit','gmchange']
tables={'income_vip':['n_income_attr_p','revenue','oper_cost'],'cashflow_vip':['n_cashflow_act'],'balancesheet_vip':['total_hldr_eqy_exc_min_int']}
vars=sum(tables.values(),[])
def events(symbols,source_dir=src,destination=F):
    frames=[]
    for api,cols in tables.items():
        for file in sorted(source_dir.glob(api+'_*.parquet')):
            g=pd.read_parquet(file)
            g=g[g.ts_code.isin(symbols)&g.report_type.astype(str).eq('1')].copy()
            g['source']=file.name
            frames.append(g)
    x=pd.concat(frames,ignore_index=True)
    x['date']=pd.to_datetime(x[['ann_date','f_ann_date']].fillna('').max(axis=1),errors='coerce')
    x=x[x.date.notna()&x.end_date.notna()].copy()
    x['q']=pd.to_datetime(x.end_date).dt.to_period('Q').astype('int64')-pd.Period('2013Q1').ordinal
    x.to_parquet(destination/'versions.parquet',index=False)
    x=x[x.q.between(0,54)];key=['ts_code','date','q'];g=x.groupby(key)
    v=g[vars].first().mask(g[vars].nunique()>1)
    fin=g.comp_type.first().astype(str).ne('1')
    v.loc[fin,'oper_cost']=np.nan
    # Each table owns its fields; missing on a newly issued version invalidates the prior value.
    for api,cols in tables.items():
        keys=x[x.source.str.startswith(api)].set_index(key).index.unique()
        v['has_'+api]=v.index.isin(keys)
    result=[]
    for sym,obs in v.reset_index().groupby('ts_code',sort=False):
        z=np.full((55,len(vars)),np.nan);current=-1
        for date,dd in obs.groupby('date',sort=False):
            for row in dd.itertuples():
                for api,cols in tables.items():
                    if getattr(row,'has_'+api):
                        for col in cols:z[row.q,vars.index(col)]=getattr(row,col)
                current=max(current,row.q)
            # Standalone quarterly flows then trailing sums on a strictly consecutive four quarters.
            single=z[:current+1,:4].copy()
            ind=np.flatnonzero(np.arange(current+1)%4!=0)
            single[ind]-=z[ind-1,:4]
            def trailing(i,j):
                return single[i-3:i+1,j].sum() if i>=3 else np.nan
            def roe(i):
                if i<4 or not(z[i,4]>0 and z[i-4,4]>0):return np.nan
                return trailing(i,0)/((z[i,4]+z[i-4,4])/2)
            def gm(i):
                return 1-single[i,2]/single[i,1] if i>=0 and single[i,1]>0 else np.nan
            i=current;earn=trailing(i,0);equity=z[i,4]
            result.append((sym[-2:]+sym[:6],date,(pd.Period('2013Q1')+i).end_time.normalize(),earn,equity,roe(i),
                           -np.std([roe(j) for j in range(i-7,i+1)],ddof=1),trailing(i,3)/earn if earn>0 else np.nan,gm(i)-gm(i-4)))
    frame=pd.DataFrame(result,columns=['instrument','disclosure','period']+A)
    frame.to_parquet(destination/'events.parquet',index=False)
    return frame
def industries(frame):
    x=pd.read_parquet(PRIVATE/'industry.parquet')
    x['instrument']=x.ts_code.str[-2:]+x.ts_code.str[:6]
    x['lo']=pd.to_datetime(x.in_date,errors='coerce');x['hi']=pd.to_datetime(x.out_date,errors='coerce').fillna(pd.Timestamp('2100-01-01'))
    groups={s:g for s,g in x.groupby('instrument')};out=np.full(len(frame),'未知',object)
    for s,ix in frame.groupby('instrument').indices.items():
        if s not in groups:continue
        dates=frame.signal_date.values[ix];arr=out[ix]
        for row in groups[s].itertuples():
            ok=(dates>=row.lo.to_datetime64())&(dates<row.hi.to_datetime64())
            arr[ok]=np.where((arr[ok]=='未知')|(arr[ok]==row.l1_name),row.l1_name,'冲突')
        out[ix]=arr
    return out
def main():
    ref=frozen(True)[KEY];tr=pd.read_parquet(LOCAL/'wide_features.parquet',columns=['signal_date','instrument','weekly_ok'])
    tr=tr[tr.weekly_ok][KEY[:2]]
    keys=pd.concat([tr,ref[KEY[:2]]]).drop_duplicates().sort_values(['signal_date','instrument'])
    symbols=set(keys.instrument.str[2:]+'.'+keys.instrument.str[:2])
    issuer_file=F/'events_input_names.csv'
    if issuer_file.exists() and set(pd.read_csv(issuer_file).ts_code)==symbols:
        ev=pd.read_parquet(F/'events.parquet')
    else:
        ev=events(symbols)
        pd.DataFrame({'ts_code':sorted(symbols)}).to_csv(issuer_file,index=False)
    dates=keys.signal_date.drop_duplicates()
    panel=pd.merge_asof(keys,ev.sort_values('disclosure'),by='instrument',left_on='signal_date',right_on='disclosure',allow_exact_matches=False)
    caps=[]
    for file in src.glob('cap_*.parquet'):
        g=pd.read_parquet(file)
        if g.empty:continue
        g['instrument']=file.stem[4:];caps.append(g)
    cap=pd.concat(caps,ignore_index=True);cap['signal_date']=pd.to_datetime(cap.trade_date);cap['capital']=cap.total_mv*10000
    panel=panel.merge(cap[KEY[:2]+['capital']].drop_duplicates(),on=KEY[:2],how='left',validate='1:1')
    panel['stale']=(panel.signal_date-panel.period).dt.days>180
    panel.loc[panel.stale,A]=np.nan
    panel['equity_nonpositive']=panel.BM<=0
    for a in ['BM','EP']:panel[a]/=panel.capital.where(panel.capital>0)
    panel['industry']=industries(panel);group=panel.groupby(['signal_date','industry'])
    rank=group[A].rank();count=group[A].transform('count')
    neutr=(rank/(count+1)-.5).where((count>=10)&np.broadcast_to(~panel.industry.isin(['未知','冲突']).to_numpy()[:,None],count.shape))
    for a in A:
        panel['n_'+a]=neutr[a];panel['raw_'+a]=panel.groupby('signal_date')[a].rank()/(panel.groupby('signal_date')[a].transform('count')+1)-.5
    panel.to_parquet(F/'panel.parquet',index=False)
    print(panel.shape,flush=True)
if __name__=='__main__':main()
