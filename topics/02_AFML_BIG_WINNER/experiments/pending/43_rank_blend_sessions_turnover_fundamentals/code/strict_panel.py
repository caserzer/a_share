from fund_panel import *
from original_cells import NUM,UNITS
import fitz,re
S=F/'strict';S.mkdir(exist_ok=True)
def shares(raw,guess):
    if not np.isfinite(guess):return None
    with fitz.open(raw) as doc:
        scales=set()
        for i,p in enumerate(doc):
            txt=p.get_text(sort=True)
            compact=re.sub(r'\s','',txt)
            scales.update(v for rx,v in [(r'百万股',1e6),(r'万股',1e4),(r'千股',1e3),(r'(单位[：:]股|股份总数|总股本)',1)] if re.search(rx,compact))
            for line in txt.splitlines():
                if not re.search(r'股份总数|总股本|股份总额|普通股股数',line):continue
                for number in NUM.finditer(line):
                    try:n=float(number.group().replace(',','').replace('，',''))
                    except ValueError:continue
                    for sc in scales:
                        if n>0 and abs(guess-n*sc)<2:return (n*sc,i+1,line.strip())
def main():
    from concurrent.futures import ProcessPoolExecutor
    proxy=pd.read_parquet(F/'panel.parquet');cap=pd.concat(pd.read_parquet(p) for p in src.glob('cap_*.parquet'))
    cap['instrument']=cap.ts_code.str[-2:]+cap.ts_code.str[:6];cap['dt']=pd.to_datetime(cap.trade_date)
    cap=cap.drop_duplicates(['instrument','dt']).set_index(['instrument','dt']).total_mv
    close=pd.read_parquet(LOCAL/'close.parquet')
    pdir=F/'primary_cells';files=list(pdir.glob('*.json'))
    if len(files)!=len(pd.read_csv(pdir/'jobs.csv')):raise RuntimeError('original collection pending')
    reports=[json.loads(p.read_text()) for p in files];facts=[];receipts=[]
    comp=pd.read_parquet(F/'versions.parquet',columns=['ts_code','comp_type']).drop_duplicates().set_index('ts_code').comp_type
    for r in reports:
        sym=('SZ' if r['code'].startswith(('0','3')) else 'SH')+r['code'];ticker=sym[2:]+'.'+sym[:2];q=pd.Period(r['quarter'])
        # Report-date cutoff and hash are retained even when OCR or tables did not yield a value.
        base=dict(ts_code=ticker,end_date=q.end_time.strftime('%Y%m%d'),ann_date=r['date'].replace('-',''),f_ann_date=r['date'].replace('-',''),report_type='1',comp_type=str(comp.loc[ticker].iloc[0] if isinstance(comp.loc[ticker],pd.Series) else comp.loc[ticker]),source_doc=r['id'])
        facts.append({**base,**{c['field']:c['value'] for c in r['cells']}})
        if r['status']!='parsed':continue
        px=close[sym].loc[:q.end_time].dropna()
        if px.empty:continue
        price=px.iloc[-1];date=px.index[-1];hist=cap.get((sym,date),np.nan)
        if not np.isfinite(hist):continue
        digest=r['sha256'];original=pdir/(r['id']+'.pdf')
        assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
        got=shares(original,hist*1e4/price)
        if got:
            sh,page,line=got
            receipts.append((sym,pd.Timestamp(r['date']),q.end_time.normalize(),sh,page,line,digest))
    fb=pd.DataFrame(facts)
    # Unknown on a new unverified report supersedes previously certified amounts for that report period.
    syms=set(fb.ts_code)
    for api,fields in tables.items():
        for c in fields:
            if c not in fb:fb[c]=np.nan
        keep=['ts_code','end_date','ann_date','f_ann_date','report_type','comp_type','source_doc']+fields
        fb[keep].to_parquet(S/(api+'_originals.parquet'),index=False)
    ev=events(syms,S,S)
    sh=pd.DataFrame(receipts,columns='instrument known period shares page line sha256'.split())
    sh.to_parquet(S/'share_receipts.parquet',index=False)
    p=proxy[KEY[:2]+['industry','capital']].copy()
    p=pd.merge_asof(p.sort_values('signal_date'),ev.sort_values('disclosure'),left_on='signal_date',right_on='disclosure',by='instrument',allow_exact_matches=False)
    p.loc[(p.signal_date-p.period).dt.days>180,A]=np.nan
    p['checked_cap']=np.nan
    if len(sh):
        # For the most recently disclosed current share count, reconcile every valuation to actual daily capitalization.
        sh=sh.sort_values(['instrument','known','period']).drop_duplicates(['instrument','known'],keep='last')
        ss=pd.merge_asof(p[KEY[:2]],sh.sort_values('known'),by='instrument',left_on='signal_date',right_on='known',allow_exact_matches=False)
        i=close.index.get_indexer(p.signal_date);j=close.columns.get_indexer(p.instrument);raw=close.to_numpy()[i,j]*ss.shares
        ok=(abs(raw-p.capital)<=np.maximum(2.,close.to_numpy()[i,j]*2)) & ((ss.signal_date-ss.period).dt.days<=180)
        p['checked_cap']=raw.where(ok)
    p['EP']/=p.checked_cap;p['BM']/=p.checked_cap
    gg=p.groupby(['signal_date','industry']);count=gg[A].transform('count');values=(gg[A].rank()/(count+1)-.5).where(count>=10)
    for col in A:p['n_'+col]=values[col].where(~p.industry.isin(['未知','冲突']))
    p.to_parquet(S/'panel.parquet',index=False)
    print(len(p),p[A].notna().sum().to_dict(),p[['n_'+a for a in A]].notna().sum().to_dict(),flush=True)
if __name__=='__main__':main()
