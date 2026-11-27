"""Verify vendor current-period monetary cells against dated original Chinese disclosures."""
from ep43lib import *
import json,re,gzip,time,requests,hashlib
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import fitz
F=O/'fundamental';I=F/'originals';P=F/'primary_cells';P.mkdir(exist_ok=True)
FIELDS={'n_income_attr_p':r'归属于(上市公司股东|母公司股东|母公司所有者|母公司普通股股东)的?净利润','revenue':r'(^|[其中：:、])营业收入','oper_cost':r'(^|[其中：:、])营业成本','n_cashflow_act':r'经营活动产生的现金流量净额','total_hldr_eqy_exc_min_int':r'归属于(母公司|上市公司)(股东|所有者)的?(权益|净资产)(合计|总额)?'}
NUM=re.compile(r'(?<![A-Za-z0-9])[-−]?\(?\d[\d,，]*\.\d{1,4}\)?|(?<![\w.])[-−]?\d{1,3}(?:[,，]\d{3})+(?!\.)')
UNITS=[(r'百万元',1e6),(r'万元',1e4),(r'千元',1e3),(r'(人民币元|单位[：:]元|单位为元|元币种)',1)]
def work(task):
    code,q,date,item=task;aid=item['announcementId'];file=P/(aid+'.json')
    if file.exists():return
    url='https://static.cninfo.com.cn/'+item['adjunctUrl']
    out=dict(code=code,quarter=str(q),date=date,id=aid,title=item['announcementTitle'],url=url,observed_at=datetime.now(timezone.utc).isoformat(),cells=[])
    raw=P/(aid+'.pdf')
    try:
        if not raw.exists():
            ss=requests.Session();ss.trust_env=False
            r=ss.get(url,timeout=(8,60));r.raise_for_status()
            if not r.content.startswith(b'%PDF'):raise ValueError('not PDF')
            raw.write_bytes(r.content)
        data=raw.read_bytes();out['sha256']=hashlib.sha256(data).hexdigest()
        with fitz.open(stream=data,filetype='pdf') as doc:
            refs=V.get((code,q),{});scales=set()
            for pi,page in enumerate(doc):
                if len(out['cells'])==len(FIELDS):break
                txt=page.get_text(sort=True);lines=txt.splitlines()
                txt1=re.sub(r'\s','',txt)
                scales.update(v for regex,v in UNITS if re.search(regex,txt1))
                for n,line in enumerate(lines):
                    if not NUM.search(line):continue
                    label=NUM.split(line,1)[0];label=re.sub(r'\s','',label)
                    for col,regex in FIELDS.items():
                        if col not in refs or not re.search(regex,label) or any(c['field']==col for c in out['cells']):continue
                        match=NUM.search(line);lit=match.group().replace(',','').replace('，','').replace('−','-')
                        if lit.startswith('(') and lit.endswith(')'):lit='-'+lit[1:-1]
                        try:value=float(lit)
                        except ValueError:continue
                        for scale in scales:
                            # Distinct original and vendor values must agree within the precision actually printed.
                            for expected,ann in refs[col]:
                                if ann>date or abs(expected-value*scale)>max(.015,scale*.000001):continue
                                if not expected or len(str(int(abs(expected))))<4:continue
                                out['cells'].append(dict(field=col,value=value*scale,page=pi+1,unit=scale,line=line.strip(),vendor_candidate=expected,ann=ann));break
                            else:continue
                            break
            out['pages']=len(doc)
        out['status']='parsed'
    except Exception as e:out['status']=type(e).__name__+' '+str(e)
    file.write_text(json.dumps(out,ensure_ascii=False))
def main():
    global V
    x=pd.read_parquet(F/'versions.parquet');x['code']=x.ts_code.str[:6];x['period']=pd.to_datetime(x.end_date).dt.to_period('Q')
    files=[json.loads(p.read_text()) for p in I.glob('[0-9]*.json')];codes={g['issuer'] for g in files if g['status']=='complete_index'}
    V={}
    for (code,q),g in x[x.code.isin(codes)].groupby(['code','period']):
        V[code,q]={k:list(set(zip(g.loc[g[k].notna(),k],g.loc[g[k].notna(),'date'].dt.strftime('%Y-%m-%d')))) for k in FIELDS}
    jobs=[]
    for g in files:
        if g['issuer'] not in codes:continue
        for a in g['items']:
            title=re.sub(r'<.*?>','',a['announcementTitle'])
            if re.search(r'摘要|英文|英语|关于|审计报告|董事会|释义|正文版|提示性|公告|补充说明|取消',title):continue
            yr=re.search(r'(20\d\d)\s*年',title)
            if not yr:continue
            q=3 if re.search('三季',title) else 1 if re.search('一季',title) else 2 if re.search('半年|中期',title) else 4 if '年度报告' in title else None
            if not q:continue
            period=pd.Period(yr[1]+'Q'+str(q));date=pd.to_datetime(a['announcementTime'],unit='ms',utc=True).tz_convert('Asia/Shanghai').date().isoformat()
            if period.year<2013 or not (g['issuer'],period) in V:continue
            jobs.append((g['issuer'],period,date,a))
    pd.DataFrame([(c,str(q),dt,a['announcementId'],a['announcementTitle']) for c,q,dt,a in jobs],columns=['code','q','date','id','title']).to_csv(P/'jobs.csv',index=False)
    with ThreadPoolExecutor(5) as ex:
        for i,_ in enumerate(ex.map(work,jobs)):
            if i%50==0:print(i,len(jobs),flush=True)
if __name__=='__main__':main()
