"""Period-specific financial events, first-report earnings consensus and research revisions."""
from event_account import *
import gzip, re, html
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
EP24=next(BASE.glob('24_*'))/'outputs'
def unit(code):
    code=code.astype(str).str.zfill(6)
    return np.where(code.str[0]=='6','SH','SZ')+code
def fetch(api):
    d=pd.read_parquet(OUT/(api+'.parquet'))
    d['instrument']=d.ts_code.str[-2:]+d.ts_code.str[:6]
    for k in ['ann_date','f_ann_date','first_ann_date','end_date']:
        if k in d:d[k]=pd.to_datetime(d[k],format='%Y%m%d',errors='coerce')
    if 'f_ann_date' in d:d['ann_date']=d[['ann_date','f_ann_date']].max(axis=1)
    return d
def calendar(actual):
    return pd.PeriodIndex(actual,freq='Q').astype('int64')
def first_disclosed(d,cols):
    k=['instrument','end_date']
    d=d.dropna(subset=k+['ann_date']).sort_values(k+['ann_date'])
    d=d[d.ann_date==d.groupby(k).ann_date.transform('min')]
    vals=d.groupby(k)[cols].nunique()
    d=d.drop_duplicates(k).set_index(k)
    for col in cols:d.loc[vals[col]>1,col]=np.nan
    return d.reset_index()
def accel(d,col,tag,basis):
    first=first_disclosed(d,[col]).merge(basis,on=['instrument','end_date'],how='left')
    first['basis']=pd.to_numeric(first.comp_type,errors='coerce').where(first.basis_known<=first.ann_date)
    first['q']=calendar(first.end_date)
    first=first.set_index(['instrument','q']).sort_index();r=first.reset_index()[['instrument','q']]
    def lag(series,n):return series.reindex(pd.MultiIndex.from_frame(r.assign(q=r.q-n))).to_numpy()
    v=first[col].to_numpy();date=first.ann_date
    prev=lag(first[col],1);pdte=lag(date,1)
    q=np.where(r.q.to_numpy()%4==0,v,v-prev)
    basis_series=first.basis;current_basis=basis_series.to_numpy()
    q[(r.q.to_numpy()%4!=0)&~((pdte<=date.to_numpy())&(lag(basis_series,1)==current_basis))]=np.nan
    q[~np.isfinite(current_basis)]=np.nan
    q=pd.Series(q,index=first.index);v0=lag(q,4)
    yoy=q.to_numpy()/np.where(v0>0,v0,np.nan)-1
    yoy[~((lag(date,4)<date.to_numpy())&(lag(basis_series,4)==current_basis))]=np.nan
    growth=pd.Series(yoy,index=first.index)
    a=yoy-lag(growth,1);a[~((lag(date,1)<date.to_numpy())&(lag(basis_series,1)==current_basis))]=np.nan
    return first.reset_index()[['instrument','end_date','ann_date']].assign(metric=tag,growth=yoy,acceleration=a)
def forecast_text():
    archive=EP24/'r19_eps_expectations'
    m=pd.read_parquet(archive/'selected_reports.parquet')[['infoCode','orgCode']].merge(pd.read_parquet(archive/'validated_extractions.parquet')[['infoCode','stockCode','available_date','source_exclusion']],on='infoCode')
    src=m[m.available_date.notna() & m.source_exclusion.fillna('').eq('')].copy()
    if not len(src): src=m[m.available_date.notna() & ~m.source_exclusion.fillna('').astype(str).str.lower().isin(['true','1'])].copy()
    pat=re.compile(r'预计[^。；;！？]{0,16}?(20\d\d)年?(第一季度|一季度|上半年|前三季度|Q1|H1)[^。；;！？]{0,14}?归母净利(?:润)?(?:约为|为|约|达到|实现)?(-?\d+(?:\.\d+)?)(亿|万)元(?!至|到|[-～~])',re.I)
    def one(row):
        f=EP24/'local_cache/r19_eps_html'/(row.infoCode+'.html.gz')
        raw=gzip.decompress(f.read_bytes()).decode('utf-8',errors='replace')
        match=re.search(r'id=["\']ctx-content["\'][^>]*>(.*?)</div>',raw,re.S)
        if not match:return []
        s=html.unescape(re.sub('<[^>]+>','',match[1])).replace(' ','')
        out=[]
        for h in pat.finditer(s):
            y,q,v,u=h.groups();q={'第一季度':'0331','一季度':'0331','Q1':'0331','上半年':'0630','H1':'0630','前三季度':'0930'}[q.upper()]
            out.append((row.infoCode,row.stockCode,row.orgCode,pd.Timestamp(row.available_date),pd.Timestamp(y+q),float(v)*(1e8 if u=='亿' else 1e4),h[0]))
        return out
    rows=[]
    with ThreadPoolExecutor(6) as ex:
        for entries in ex.map(one,src.itertuples()):rows.extend(entries)
    out=pd.DataFrame(rows,columns='infoCode stock_code broker published end_date value evidence'.split())
    (OUT/'interim_scan.txt').write_text(f'validated bodies {len(src)}; explicit dated forecast observations {len(out)}\n')
    return out
def main():
    inc=fetch('income_vip');fina=fetch('fina_indicator_vip');fore=fetch('forecast_vip');flash=fetch('express_vip')
    b=fetch('accounting_basis')
    b=first_disclosed(b,['comp_type'])[['instrument','end_date','ann_date','comp_type']].rename(columns={'ann_date':'basis_known'})
    pd.concat([accel(inc,'revenue','revenue',b),accel(fina,'profit_dedt','deducted',b)],ignore_index=True).to_parquet(OUT/'acceleration.parquet',index=False)
    pre=first_disclosed(fore,['net_profit_min','net_profit_max'])
    # A subsequent revision that references an earlier notice cannot become that notice.
    pre['known']=pre.ann_date
    pre['value']=((pre.net_profit_min+pre.net_profit_max)/2*1e4).where((pre.net_profit_min<=pre.net_profit_max)&(pre.first_ann_date.isna()|(pre.first_ann_date==pre.ann_date)))
    form=first_disclosed(inc,['n_income_attr_p'])
    form['value']=form.n_income_attr_p
    basecols=['instrument','end_date','ann_date','value']
    records=pd.concat([pre[basecols].assign(kind='guidance'),form[basecols].assign(kind='formal')],ignore_index=True)
    clocks=pd.concat([pre[['instrument','end_date']].assign(known=pre[['ann_date','first_ann_date']].min(axis=1)),form[['instrument','end_date']].assign(known=form.ann_date),flash[['instrument','end_date']].assign(known=flash.ann_date)]).groupby(['instrument','end_date']).known.min()
    af=pd.read_parquet(next(BASE.glob('35_*/data/r11_analyst_forecasts.parquet')))
    a=af[af.basis=='profit_cny'].copy()
    a['end_date']=pd.to_datetime(a.fiscal_year.astype(str)+'1231');a['published']=a.publication_proxy_date
    z=forecast_text();z.to_parquet(OUT/'interim_disclosed_forecast_spans.parquet',index=False)
    a=pd.concat([a,z],ignore_index=True);a['instrument']=unit(a.stock_code)
    key=['instrument','end_date','broker','published'];conf=a.groupby(key).value.transform('nunique')>1
    a=a.loc[~conf].drop_duplicates(key).merge(clocks,on=['instrument','end_date'])
    before=a[a.published<a.known].sort_values('published').drop_duplicates(['instrument','end_date','broker'],keep='last')
    c=before.groupby(['instrument','end_date']).value.agg(['size','median']).reset_index()
    c.to_parquet(OUT/'consensus_profit.parquet',index=False)
    r=records.merge(c,on=['instrument','end_date'],how='left').merge(clocks,on=['instrument','end_date'])
    r['error']=(r.value-r['median']).where(r['size']>=2);r['quarter']=r.end_date.dt.quarter
    r=r.sort_values(['instrument','kind','quarter','ann_date','end_date']);r['prior_sd']=np.nan
    # Same issuer, fiscal quarter and disclosure type. Exclude histories announced on the current day.
    for _,g in r[r.error.notna()].groupby(['instrument','kind','quarter'],sort=False):
        values=[]
        for i,row in g.iterrows():
            prev=[v for t,v in values if t<row.ann_date][-8:]
            if len(prev)>=2:r.at[i,'prior_sd']=np.std(prev,ddof=1)
            values.append((row.ann_date,row.error))
    r['sue']=r.error/r.prior_sd.where(r.prior_sd>0);r['first']=r.ann_date.eq(r.known)
    starts=pd.concat([pre[['instrument','end_date']].assign(clock=pre[['ann_date','first_ann_date']].min(axis=1),release='guidance'),form[['instrument','end_date']].assign(clock=form.ann_date,release='formal'),flash[['instrument','end_date']].assign(clock=flash.ann_date,release='flash')])
    starts=starts.merge(clocks,on=['instrument','end_date'])
    earliest=starts[starts.clock==starts.known].groupby(['instrument','end_date']).release.nunique().rename('same_date_release_types')
    r=r.merge(earliest,on=['instrument','end_date'],how='left')
    r['first']=r['first'].astype('boolean')
    r.loc[r.ann_date.eq(r.known)&r.same_date_release_types.gt(1),'first']=pd.NA
    r.to_parquet(OUT/'profit_surprises.parquet',index=False)
    old=EP41/'sources/n3_n4/results'
    ep=pd.read_parquet(old/'annual_events.parquet').rename(columns={'formal':'ann_date','SUE':'sue','first_formal':'first'})
    fx=pd.read_parquet(old/'flash_events.parquet').rename(columns={'express':'ann_date','first_flash':'first'})
    for g in [ep,fx]:g['end_date']=pd.to_datetime(g.year.astype(str)+'1231');g['quarter']=4
    cols='instrument end_date ann_date sue first quarter'.split()
    o=pd.concat([r[cols+['kind']],ep[cols].assign(kind='formal_eps'),fx[cols].assign(kind='flash_eps_proxy')],ignore_index=True)
    o=o.replace([np.inf,-np.inf],np.nan).dropna(subset='sue')
    o.to_parquet(OUT/'all_sue_events.parquet',index=False)
    print('surprises',o.groupby(['kind','first']).size(),flush=True)
if __name__=='__main__':main()
