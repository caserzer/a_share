"""Domain membership marked at each close, common dates for migration and joint state exposure."""
from mixture import *

def domains():
    m=market(True)
    from engine import PRIVATE
    nm=pd.read_parquet(PRIVATE/'daily_members.parquet').reindex(index=m.days,columns=m.symbols,fill_value=False).to_numpy()
    parts=[]
    for name in ['d6','g7_transfer','g7_refit']:
        dest=OUT/name
        daily=pd.read_parquet(dest/'daily.parquet')
        for path in sorted(dest.glob('trace_*_*.parquet')):
            arm,sg=path.stem[6:].rsplit('_',1);seg=int(sg)
            tr=pd.read_parquet(path);day=tr.day.to_numpy();stock=tr.stock.to_numpy()
            tr['inside_on_signal']=nm[day-1,stock]
            mark=m.planes[1][day,stock]
            ended=day==m.days.get_loc(SEG800[seg-1][1]);mark[ended]=m.planes[0][day[ended],stock[ended]]
            tr['capital']=np.where(tr.new_units>0,mark*tr.new_units,0)
            tr['broker_buy']=np.where(tr.flow>0,tr.fee/.001,0)
            tr['broker_sell']=np.where(tr.flow<0,tr.fee/.002,0)
            data=tr.groupby(['day','inside_on_signal'])[['target','broker_buy','broker_sell','capital','overnight','intraday','fee']].sum().reset_index()
            data['date']=m.days[data.day];data=data.drop(columns='day')
            b=daily.query('arm==@arm and segment==@seg').set_index('date')
            reconstructed=data.groupby('date').capital.sum().reindex(b.index,fill_value=0)+b.cash
            np.testing.assert_allclose(reconstructed,b.nav,rtol=0,atol=1e-10)
            data['cash_ratio']=data.date.map(b.cash/b.nav);data['exposure_ratio']=data.capital/data.date.map(b.nav)
            parts.append(data.assign(arm=arm,segment=seg,group=name))
    pd.concat(parts).to_parquet(OUT/'domain_actual_exposures.parquet',index=False)
    def gaps(label,a,b):
        x=pd.read_csv(OUT/label/'monthly.csv').pivot(index=['segment','month'],columns='arm',values='net')
        return (x[a]-x[b]).dropna().rename(label).reset_index()
    base=gaps('main','dynamic','static').drop(columns='segment')
    g=gaps('g7_transfer','exported','static').merge(gaps('g7_refit','exported','static'),on=['segment','month'],validate='1:1')
    g.merge(base,on='month',validate='1:1').to_csv(OUT/'g7_matched_calendar.csv',index=False)

def joint():
    p=OUT/'main'
    w=pd.read_parquet(p/'weights_daily.parquet').loc['2021-01-08':].copy()
    m=market();w['segment']=np.where(m.days[w.entry_idx]<pd.Timestamp(SEG300[1][0]),1,2)
    w['month']=w.index.strftime('%Y-%m')
    for z in ['Z1','Z2','Z3','Z4']:
        w[z+'_bin']=np.select([w[z].isna(),w[z]<1/3,w[z]>2/3],['unknown','low','high'],default='mid')
    f=pd.read_parquet(p/'funded_by_signal.parquet')
    flows=f[f.unique_target].groupby(['arm','origin']).buy.sum()
    data=[]
    import itertools
    for a,b in itertools.combinations(['Z1','Z2','Z3','Z4'],2):
        for (seg,ga,gb),h in w.groupby(['segment',a+'_bin',b+'_bin']):
            for arm in ['dynamic','plus_Z2','plus_Z3','plus_Z4']:
                cash=h.entry_idx.map(flows.loc[arm] if arm in flows.index.get_level_values(0) else {}).sum()
                data.append((a,b,ga,gb,seg,arm,len(h),h.month.nunique(),h[arm].mean(),cash))
    pd.DataFrame(data,columns='first_state second_state first_band second_band segment arm days months mean_tree_weight extra_broker_buy'.split()).to_csv(p/'g5_all_state_pairs.csv',index=False)
if __name__=='__main__':domains();joint()

