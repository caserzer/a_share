from disclosures import *
def main():
    s=Study();m=s.m
    f=OUT/'fusion';signals=pd.read_parquet(f/'daily_sources_and_increments.parquet')
    groups=[]
    for dt,d in signals.groupby('signal_date'):
        i=m.days.get_loc(dt);e=i+1;j=m.symbols.get_indexer(d.instrument)
        a=pd.DataFrame({'sector':s.sector(i)[j],'cap_quintile':pd.cut(s.cap[e][j],[0,.2,.4,.6,.8,1],labels=False,include_lowest=True),'all':1})
        for n in ['eps20','eps60','target20','coverage_delta','sue20']:
            a[n]=d[n].notna().to_numpy()
        a['both']=a.eps20&a.sue20
        b=a.groupby(['sector','cap_quintile'],dropna=False).sum().reset_index().assign(signal_date=dt)
        groups.append(b)
    pd.concat(groups).to_parquet(f/'sector_and_size_coverage.parquet',index=False)
    a=pd.read_parquet(next(BASE.glob('35_*/data/r11_analyst_forecasts.parquet')))
    a.groupby([a.publication_proxy_date.dt.to_period('M').astype(str),'basis']).agg(reports=('infoCode','nunique'),stocks=('stock_code','nunique'),brokers=('broker','nunique')).to_csv(f/'monthly_archived_forecasts.csv')
    b=pd.read_parquet(OUT/'profit_surprises.parquet')
    b['comparable']=b['size']>=2;b['standardized']=b.sue.notna()
    b.groupby(['quarter','kind','first']).agg(disclosures=('instrument','size'),comparable=('comparable','sum'),standardized=('standardized','sum')).to_csv(OUT/'period_evidence.csv')
    z=pd.read_parquet(OUT/'acceleration.parquet')
    z['valid_growth']=z.growth.notna();z['valid_accel']=z.acceleration.notna()
    z.groupby(['metric',z.end_date.dt.quarter]).agg(filings=('instrument','size'),with_growth=('valid_growth','sum'),with_acceleration=('valid_accel','sum')).to_csv(OUT/'acceleration_source_coverage.csv')
    for c in ['fina_indicator_vip','income_vip','forecast_vip','express_vip']:
        g=pd.read_json(OUT/(c+'.jsonl'),lines=True);assert (g.code==0).all()
    print('source audit',len(signals),flush=True)
if __name__=='__main__':main()
