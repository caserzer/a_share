from constituent_audit import *
from shared import PRIVATE,outer
DATES={4718:'2017-01-18',4794:'2017-02-14',12524:'2019-01-18',13179:'2020-08-17',13307:'2021-03-15',13716:'2021-09-13',13420:'2021-09-28',15546:'2025-03-04',1006022:'2025-09-05',3006027:'2026-01-12',3006261:'2026-10-12',3006227:'2026-10-19'}
def download():
    rows=[]
    for id,day in DATES.items():
        doc=requests.get(api+'queryAnnouncementById',params={'id':id},timeout=15).json()['data']
        soup=BeautifulSoup(doc['content'],'html.parser')
        urls=[a.get('href','') for a in soup.select('a[href]')]+[a['fileUrl'] for a in doc['enclosureList']]
        url=next(url for url in urls if url.lower().endswith(('.xlsx','.xls')))
        f=CACHE/(f'adhoc_{id}'+Path(url).suffix)
        if not f.exists():
            r=requests.get(url,timeout=30);r.raise_for_status();f.write_bytes(r.content)
        b=pd.ExcelFile(f);print(id,b.sheet_names[:4],pd.read_excel(b,header=None,nrows=3).iloc[:,:7].values.tolist())
        rows.append(dict(id=id,effective=day,published=doc['publishDate'],body=soup.get_text(' ',strip=True)[:400],url=url,attachment=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    pd.DataFrame(rows).to_csv(OUT/'adhoc_attachments.csv',index=False)
if __name__=='__main__':download()

def reconstruct():
    events=pd.read_csv(OUT/'regular_changes.csv',dtype=str); additions=[]
    for row in pd.read_csv(OUT/'adhoc_attachments.csv').itertuples():
        if row.effective>'2026-09-30': continue
        f=CACHE/row.attachment;b=pd.ExcelFile(f);codes=[]
        for act,sheet in [('out','调出'),('in','调入')]:
            if sheet in b.sheet_names:
                z=pd.read_excel(b,sheet_name=sheet,dtype=str)
                z=z[z.iloc[:,0].str.zfill(6).isin(['000300','000905','000906','399300'])]
                if z.iloc[:,0].str.zfill(6).eq('000906').any():z=z[z.iloc[:,0].str.zfill(6).eq('000906')]
                v=z.iloc[:,2]
            else:
                z=pd.read_excel(b,header=None,dtype=str)
                code=z.iloc[:,0].str.zfill(6)
                z=z[code.eq('000906')] if code.eq('000906').any() else z[code.isin(['000300','000905','399300'])]
                v=z.iloc[:,2 if act=='out' else 4].replace({'-':{12524:'601598',13420:'601868'}.get(row.id)})
            codes.append(set(v.dropna().str.zfill(6)) - {'00000-','0000--'})
        overlap=codes[0]&codes[1]
        for act,names in zip(['out','in'],codes):
            for name in names-overlap:
                assert re.fullmatch(r'\d{6}',name),name
                additions.append(dict(effective=row.effective,action=act,code=name,kind='adhoc',notice=str(row.id)))
    ev=pd.concat([events,pd.DataFrame(additions)],ignore_index=True)
    # Canonical archive identifier for one security with an observed ticker change.
    ev['announced_code']=ev.code
    ev['code']=ev.code.replace({'300114':'302132'})
    ev.to_csv(OUT/'effective_changes.csv',index=False)
    w=pd.read_parquet(OUT/'weights800.parquet')
    weights={pd.Timestamp(d):set(z.con_code.str[:6]) for d,z in w.groupby('trade_date')}
    days=pd.read_parquet(PRIVATE/'market.parquet').index
    current=weights[min(weights)].copy();snap=[];audit=[]
    for date in days[days<=pd.Timestamp('2026-09-30')]:
        if date<min(weights):continue
        prev=days[days.get_loc(date)-1] if days.get_loc(date)>0 else min(weights)
        z=ev[(ev.effective>str(prev.date()))&(ev.effective<=str(date.date()))]
        before=current.copy()
        current.difference_update(z[z.action=='out'].code);current.update(z[z.action=='in'].code)
        assert len(current)==800,(date,len(current),set(z.code))
        if date in weights:
            audit.append(dict(date=date,only_rebuilt=','.join(sorted(current-weights[date])),only_snapshot=','.join(sorted(weights[date]-current))))
        if len(z) or not snap:
            snap.extend((date,c) for c in sorted(current))
    a=pd.DataFrame(audit);a.to_csv(OUT/'monthly_constituent_checks.csv',index=False)
    assert (a.only_rebuilt.eq('')&a.only_snapshot.eq('')).all(),a[a.only_rebuilt.ne('')].to_string()
    blocks=pd.DataFrame(snap,columns=['effective','code'])
    dates=sorted(set(pd.read_parquet(PRIVATE/'features.parquet',columns=['signal_date']).signal_date)|set(outer().signal_date)|set(pd.read_parquet(OUT/'contributions.parquet',columns=['signal_date']).signal_date))
    result=[]
    for d in dates:
        if d>pd.Timestamp('2026-09-30'):continue
        last=blocks.loc[blocks.effective<=d,'effective'].max()
        result.append(blocks[blocks.effective.eq(last)].assign(signal_date=d))
    pd.concat(result).to_parquet(OUT/'effective800.parquet',index=False)

if __name__=='__main__':reconstruct()
