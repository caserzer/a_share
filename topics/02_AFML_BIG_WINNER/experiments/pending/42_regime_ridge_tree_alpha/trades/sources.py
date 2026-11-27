"""Build close-time covariates, respecting the publication date of index changes."""
from pathlib import Path
import hashlib,json,re
from io import BytesIO
import numpy as np
import pandas as pd
import subprocess
HERE=Path(__file__).resolve().parent
PENDING=HERE.parents[1]
OLD=next(PENDING.glob('41_*')); PRE=next(PENDING.glob('38_*'))/'three_track/results'
PRIVATE=next(PENDING.glob('36_*'))/'private'; OUT=HERE/'results'
CACHE=Path('/tmp/ep41_model_inputs_v1')
def departure_records():
    archive=Path.home()/'.cache/a_share/ep38_three_track'
    notices=pd.read_csv(PRE/'official_notices.csv')
    days=pd.read_parquet(PRIVATE/'market.parquet').index
    events=[]; evidence=[]
    for mode,g in [('regular',notices.groupby('period').first().reset_index()),('adhoc',pd.read_csv(PRE/'adhoc_attachments.csv'))]:
        for row in g.itertuples():
            if str(row.published)<'2020-12-01':continue
            file=archive/row.attachment
            assert hashlib.sha256(file.read_bytes()).hexdigest()==row.sha256
            if mode=='adhoc':eff=pd.Timestamp(row.effective)
            else:
                d=re.search(r'(?:20\d\d年)?(\d{1,2})月(\d{1,2})日(收[市盘]后)?',row.body.replace(' ',''))
                eff=pd.Timestamp(f'{row.period[:4]}-{d[1]}-{d[2]}')
                if d[3]:eff=days[days.searchsorted(eff,side='right')]
            names=set()
            if file.suffix=='.pdf':
                txt=subprocess.check_output(['python3','-c',"from pypdf import PdfReader; import sys; print('\\n'.join(t.extract_text(extraction_mode='layout') for t in PdfReader(sys.argv[1]).pages))",str(file)],text=True)
                part=re.search(r'沪深\s*300\s*指数样本调整名单[：:]?(.*?)(?=(?:沪深|中证|上证|深证)[^\n]{1,28}指数样本|$)',txt,re.S)
                if part:
                    for line in part[1].splitlines():
                        ids=re.findall(r'(?<!\d)\d{6}(?!\d)',line)
                        if len(ids)>=2:names.add(ids[0])
            else:
                b=pd.ExcelFile(file)
                if '调出' in b.sheet_names:
                    f=pd.read_excel(b,sheet_name='调出',dtype=str)
                else:f=pd.read_excel(b,header=None,dtype=str)
                if f.shape[1]>=3:
                    sub=f[f.iloc[:,0].str.zfill(6).isin(['000300','399300'])]
                    names=set(sub.iloc[:,2].dropna().str.zfill(6))
            names={n for n in names if re.fullmatch(r'\d{6}',n)}
            evidence.append((mode,row.id,row.published,eff,len(names),row.attachment,row.sha256))
            for name in names:events.append((name,pd.Timestamp(row.published),eff,row.id))
    pd.DataFrame(evidence,columns='kind notice publication effective departures file sha256'.split()).to_csv(OUT/'composition_sources.csv',index=False)
    return pd.DataFrame(events,columns=['code','publication','effective','notice'])
def run():
    from model_cache import ensure
    ensure()
    panel=pd.read_parquet(CACHE/'panel.parquet',columns=['entry_idx','signal_date','instrument','outer','pos60','vol60','vol20','money_rel20','l1_name','mom10','h10','event'])
    p=panel[panel.outer].copy()
    date=pd.to_datetime(p.signal_date); c=pd.read_parquet(PRIVATE/'close.parquet'); amt=pd.read_parquet(PRIVATE/'money.parquet')
    files=sorted((PRIVATE/'style_caps_20261117').glob('[0-9]'*8+'.json')); vals={}
    for f in files:
        assert hashlib.sha256(f.read_bytes()).hexdigest()==json.loads(f.with_suffix('.receipt.json').read_text())['sha256']
        j=json.loads(f.read_text())['data']; g=pd.DataFrame(j['items'],columns=j['fields'])
        g.index=g.ts_code.str[-2:]+g.ts_code.str[:6]
        good=g.free_share.gt(0)&g.free_share.le(g.float_share*1.0001)&g.float_share.le(g.total_share*1.0001)
        vals[pd.Timestamp(f.stem)]=g.free_share.where(good).reindex(c.columns)
    shares=pd.DataFrame(vals).T
    # Use the last snapshot date strictly earlier; preserve stock-specific missing values.
    d=shares.index.searchsorted(c.index,side='left')-1
    cap=shares.iloc[d.clip(0)].set_axis(c.index).mul(c)
    cp=c.index.get_indexer(shares.index)
    cap.iloc[(d<0)|((np.arange(len(c))-cp[d.clip(0)])>7)]=np.nan
    i=c.index.get_indexer(date); k=c.columns.get_indexer(p.instrument)
    def take(x):return x.to_numpy()[i,k]
    p['cap']=take(cap);p['adv']=take(amt.rolling(20).mean())
    p['cap180']=take(cap.rolling(180).mean());p['adv180']=take(amt.rolling(180).mean())
    mem=pd.read_parquet(PRIVATE/'daily_members.parquet')
    p['riskcap']=take(cap.rolling(180).mean().where(mem).rank(axis=1,pct=True))
    p['riskadv']=take(amt.rolling(180).mean().where(mem).rank(axis=1,pct=True))
    for col in ['cap','adv','vol20']:p[col]=p.groupby('entry_idx')[col].rank(pct=True)
    idx=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    total=pd.DataFrame(idx['items'],columns=idx['fields']).set_index('trade_date').close
    total.index=pd.to_datetime(total.index); total=total.sort_index().reindex(c.index).pct_change(10,fill_method=None)
    p['past_excess10']=p.mom10-date.map(total)
    events=departure_records()
    p['announced']=False
    for code,g in events.groupby('code'):
        sel=p.instrument.str.endswith(code)
        for z in g.itertuples():
            p.loc[sel & date.gt(z.publication) & date.lt(z.effective),'announced']=True
    events.to_csv(OUT/'known_departures.csv',index=False)
    p.drop(columns=['outer','mom10','cap180','adv180']).to_parquet(OUT/'covariates.parquet',index=False)
    print('notice rows',len(events),'known exposed names',p.announced.sum(),flush=True)
if __name__=='__main__':run()
