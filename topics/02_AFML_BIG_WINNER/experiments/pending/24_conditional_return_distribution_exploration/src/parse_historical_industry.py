"""Parse dated official classification tables, retaining page/source evidence."""
import json,re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import pandas as pd
import pymupdf
from download_historical_industry import CACHE
from build_margin_information import digest

def clean(value):return re.sub(r'\s+','',value or '')

def parse_rows(rows,state):
    output=[]
    for row in rows:
        row=[clean(v) for v in row]
        if len(row)==8 and re.fullmatch(r'\d{6}',row[0]):
            code,name,sector,sector_name,sub,sub_name,major,major_name=row
        elif len(row)==5 and re.fullmatch(r'\d{6}',row[3]):
            for i in [0,1,2]:
                if row[i]:state[i]=row[i]
            m=re.search(r'[（(]([A-S])[）)]',state[0])
            # Some source PDFs visibly clip the sector cell. Preserve the stock/major; do not guess the sector.
            sector=m[1] if m else 'unknown';sector_name=state[0];major=state[1];major_name=state[2];code,name=row[3:];sub=''
        else:continue
        assert (sector=='unknown' or re.fullmatch('[A-S]',sector)) and re.fullmatch(r'\d{2}',major),(row,state)
        output.append(dict(code=code,name=name,sector=sector,major=sector+major,sector_name=sector_name,major_name=major_name,sub=sub))
    return output

def parse_release(item):
    path=Path(item['pdf_path']);assert digest(path)==item['pdf_sha256']
    target=path.with_suffix('.parquet');audit_path=path.with_suffix('.parse.json')
    if target.exists() and audit_path.exists():
        audit=json.loads(audit_path.read_text());assert digest(target)==audit['table_sha256'] and audit['pdf_sha256']==item['pdf_sha256'];return audit
    doc=pymupdf.open(path);state={0:'',1:'',2:''};records=[];text_codes=set();table_pages=0
    for pageno,page in enumerate(doc):
        text_codes.update(re.findall(r'(?<!\d)\d{6}(?!\d)',page.get_text()))
        tables=page.find_tables().tables
        if tables:table_pages+=1
        for table in tables:
            for row in parse_rows(table.extract(),state):records.append(dict(**row,page=pageno+1))
    frame=pd.DataFrame(records);assert len(frame)>3000 and not frame.code.duplicated().any(),(item['title'],len(frame))
    assert set(frame.code)==text_codes,(item['title'],text_codes-set(frame.code),set(frame.code)-text_codes)
    frame['published']=pd.Timestamp(item['date']);frame['release_title']=item['title'];frame['source_pdf_sha256']=item['pdf_sha256']
    frame.to_parquet(target,index=False)
    audit=dict(title=item['title'],published=item['date'],pdf_path=str(path),pdf_sha256=item['pdf_sha256'],table_path=str(target),
        table_sha256=digest(target),rows=len(frame),unknown_sector_rows=int(frame.sector.eq('unknown').sum()),sectors=frame.sector.nunique(),majors=frame.major.nunique(),pages=len(doc),table_pages=table_pages,
        independent_text_code_set_matches=True,parser_sha256=digest(Path(__file__)))
    audit_path.write_text(json.dumps(audit,indent=2)+'\n');return audit

def run():
    manifest=json.loads((CACHE/'download_manifest.json').read_text());assert len(manifest)==19 and all(r['status']=='ok' for r in manifest)
    audits=[]
    with ProcessPoolExecutor(max_workers=2) as pool:
        for result in pool.map(parse_release,manifest):
            audits.append(result);print(result['title'],result['rows'],result['pages'],flush=True)
    (CACHE/'parse_manifest.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':run()
