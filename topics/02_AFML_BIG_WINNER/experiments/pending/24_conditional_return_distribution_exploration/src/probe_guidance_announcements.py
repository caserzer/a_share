"""Check whether the public announcement archive retains initial and amended guidance."""
import json,math
import requests
from prepare_panel import OUT
from build_margin_information import digest
DEST=OUT/'r37_company_guidance_probe'
CACHE=OUT/'local_cache/r37_guidance_announcements'
URL='https://np-anotice-stock.eastmoney.com/api/security/ann'


def run():
    CACHE.mkdir(exist_ok=True);receipts=[];records=[];checks=[]
    for code in ['300520','300663']:
        page=1;expected=None;rows=[]
        while True:
            params=dict(sr=-1,page_size=100,page_index=page,ann_type='A',client_source='web',f_node=0,s_node=0,
                        stock_list=code,begin_time='2025-01-01',end_time='2025-04-30')
            path=CACHE/f'{code}_{page}.json'
            if not path.exists():
                r=requests.get(URL,params=params,timeout=30);r.raise_for_status();path.write_bytes(r.content)
            payload=json.loads(path.read_text());data=payload['data'];total=int(data['total_hits'])
            if expected is None:expected=total
            assert total==expected;rows.extend(data['list'])
            receipts.append(dict(code=code,path=str(path),sha256=digest(path),url=URL,params=params,rows=len(data['list'])))
            if page>=math.ceil(total/100):break
            page+=1
        assert len(rows)==expected and len({r['art_code'] for r in rows})==len(rows)
        selected=[r for r in rows if '业绩预告' in r['title']]
        for r in selected:records.append(dict(query_stock=code,**r))
        checks.append(dict(code=code,total_announcements=expected,guidance_announcements=len(selected)))
    (DEST/'announcement_archive_probe.json').write_text(json.dumps(dict(receipts=receipts,checks=checks,records=records,
        limitation='Two stocks and a bounded 2025 date window only; original PDFs and broader completeness still need validation.'),indent=2)+'\n')
    print(json.dumps(dict(checks=checks,records=records),indent=2,ensure_ascii=False))


if __name__=='__main__':run()
