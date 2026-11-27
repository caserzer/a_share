from disclosures import *
import re
D=O.parent/'amendments';D.mkdir(exist_ok=True)
def main():
    issuers=sorted(json.loads(p.read_text())['issuer'] for p in O.glob('[0-9]*.json') if json.loads(p.read_text())['status']=='complete_index')
    url='https://np-anotice-stock.eastmoney.com/api/security/ann'
    sess=requests.Session();sess.trust_env=False
    for code in issuers:
        dest=D/(code+'.json')
        if dest.exists():continue
        evidence=[];amends=[];seen=set();status='complete'
        try:
            for page in range(1,250):
                args=dict(sr=1,page_size=100,page_index=page,ann_type='A',client_source='web',begin_time='2013-01-01',end_time='2026-10-12',f_node=0,s_node=0,stock_list=code)
                r=sess.get(url,params=args,timeout=(6,18));r.raise_for_status();obj=r.json()
                if obj.get('success')!=1:raise ValueError('unsuccessful index')
                d=obj['data'];rows=d['list'];expected=int(d['total_hits'])
                evidence.append(dict(page=page,total=expected,rows=len(rows),sha256=hashlib.sha256(r.content).hexdigest()))
                for x in rows:
                    seen.add(x['art_code']);title=x['title']
                    if re.search('更正|修订|差错|追溯调整|重述',title) and re.search('财务|会计|年度报告|季度报告|半年度报告|季报|年报',title):amends.append((x['notice_date'][:10],title,x['art_code']))
                if len(seen)==expected:break
                if len(rows)<100:raise ValueError('incomplete pagination')
        except Exception as e:status=type(e).__name__+' '+str(e)
        dest.write_text(json.dumps(dict(code=code,status=status,seen=len(seen),evidence=evidence,amendments=amends),ensure_ascii=False))
        print(code,status,len(seen),len(amends),flush=True)
        if status.startswith('HTTPError 403'):break
if __name__=='__main__':main()
