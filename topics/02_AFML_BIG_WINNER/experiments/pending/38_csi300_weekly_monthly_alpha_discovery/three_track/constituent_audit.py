from notices import *
from shared import PRIVATE
from pypdf import PdfReader
def regular():
    trading_days=pd.read_parquet(PRIVATE/"market.parquet").index
    notices=pd.read_csv(OUT/'official_notices.csv');events=[]
    for month,g in notices.groupby('period'):
        r=g.iloc[0];date=re.search(r'(?:20\d\d年)?(\d{1,2})月(\d{1,2})日(收[市盘]后)?',r.body.replace(' ',''))
        day=pd.Timestamp(f'{month[:4]}-{date[1]}-{date[2]}')
        if date[3]:day=trading_days[trading_days.searchsorted(day,side='right')]
        f=CACHE/r.attachment;kind='official_800'
        if f.suffix in ['.xlsx','.xls']:
            codes=[]
            for sheet in ['调出','调入']:
                t=pd.read_excel(f,sheet_name=sheet,dtype=str)
                ids=t.iloc[:,0].str.zfill(6);names=t.iloc[:,2].str.zfill(6)
                codes.append(set(names[ids.eq('000906')]))
            assert all(codes)
        else:
            txt='\n'.join(p.extract_text(extraction_mode='layout') for p in PdfReader(f).pages)
            codes=[set(),set()]
            for part in ['沪深300','中证500']:
                segment=re.search(part+r'指数样本调整名单[：:]?(.*?)(?=(?:沪深|中证|上证)[A-Za-z0-9]+指数(?:样本|备选)|$)',re.sub(r'[ \t]','',txt),re.S)
                assert segment,part
                pairs=re.findall(r'^\s*(\d{6})[^\d\n]*?(\d{6})[^\n]*$',segment[1],re.M)
                for a,b in pairs:codes[0].add(a);codes[1].add(b)
            common=codes[0]&codes[1];codes=[x-common for x in codes];kind='official_300_plus_500'
        for act,names in zip(['out','in'],codes):
            events.extend(dict(effective=str(day.date()),action=act,code=x,kind=kind,notice=r.id,period=month) for x in sorted(names))
    return pd.DataFrame(events)

def anchors(events):
    w=pd.read_parquet(OUT/'weights800.parquet')
    prev=None;res=[]
    for d,g in w.groupby('trade_date'):
        day=pd.Timestamp(d); after=set(g.con_code.str[:6])
        if prev:
            before=prev.copy();changed=events[(events.effective>str(last.date()))&(events.effective<=str(day.date()))]
            for _,z in changed.groupby('effective'):
                before.difference_update(z[z.action=='out'].code);before.update(z[z.action=='in'].code)
            for side,ss in [('out',before-after),('in',after-before)]:
                res.extend(dict(month=d[:6],code=x,action=side) for x in ss)
        prev=after;last=day
    return pd.DataFrame(res)
if __name__=='__main__':
    events=regular();events.to_csv(OUT/'regular_changes.csv',index=False)
    gaps=anchors(events);gaps.to_csv(OUT/'unexplained_changes.csv',index=False)
    print(gaps.groupby('month').size())
