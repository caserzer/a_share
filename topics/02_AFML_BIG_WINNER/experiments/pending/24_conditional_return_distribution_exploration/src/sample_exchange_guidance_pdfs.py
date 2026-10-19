"""Outcome-blind, stratified original-document parser feasibility sample."""
import hashlib
import argparse
import json
import time
from pathlib import Path
import requests
import pymupdf
import pandas as pd
from audit_exchange_guidance_catalog import load_catalog
from download_exchange_guidance_catalog import DEST
from prepare_panel import OUT
from build_margin_information import digest
from parse_guidance_archive_pilot import parse_table

CACHE=OUT/'local_cache/r37_exchange_pdf_sample'


def sample_documents(records):
    frame=pd.DataFrame(records)
    frame=frame[frame.title.str.contains('业绩预[告增减亏盈]',regex=True)].copy()
    frame['year']=frame.publish_date.str[:4]
    frame['revision']=frame.title.str.contains('修正|更正|补充|调整',regex=True)
    frame['selection_hash']=frame.url.map(lambda u:hashlib.sha256(u.encode()).hexdigest())
    # Select before reading amounts or outcomes. Two documents in each exchange/year/version cell.
    sample=frame.sort_values('selection_hash').groupby(['exchange','year','revision'],sort=True).head(2)
    return sample.sort_values(['exchange','year','revision','selection_hash']).to_dict('records')


def parse_pdf(path,revision):
    parsed=[]
    with pymupdf.open(path) as document:
        pages=len(document)
        for index,page in enumerate(document):
            if index>=5:break
            for table in page.find_tables().tables:
                try:result=parse_table(table.extract(),revision)
                except ValueError:continue
                parsed.append(dict(result,page=index+1))
    if len(parsed)!=1:return dict(parse_status='unsupported_or_ambiguous',candidate_tables=len(parsed),pages=pages)
    return dict(parse_status='parsed_not_manually_verified',pages=pages,**parsed[0])


def run(exchange=None):
    CACHE.mkdir(exist_ok=True)
    records,manifests=load_catalog((exchange,) if exchange else ('SZ','SH'));sample=sample_documents(records)
    prefix=exchange+'_' if exchange else ''
    (DEST/f'{prefix}pdf_sample_selection.json').write_text(json.dumps(dict(source_manifests=manifests,records=sample,
        design='Two smallest URL SHA256 hashes per exchange x calendar year x original/revision title group; no forecast outcome used.'),ensure_ascii=False,indent=2)+'\n')
    results=[];blocked_hosts=set()
    progress=DEST/f'{prefix}pdf_sample_progress.jsonl'
    with progress.open('w') as stream:
        for index,record in enumerate(sample):
            url=record['url'];host=url.split('/')[2]
            path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.pdf')
            result=dict(record,path=str(path))
            try:
                if not path.exists():
                    if host in blocked_hosts:raise RuntimeError('Previous access denial: no further host requests')
                    time.sleep(1)
                    response=requests.get(url,timeout=40)
                    if response.status_code in (401,403,429):blocked_hosts.add(host)
                    response.raise_for_status()
                    assert response.content.startswith(b'%PDF'),'Non-PDF response'
                    path.write_bytes(response.content)
                result.update(sha256=digest(path),download_status='complete',**parse_pdf(path,record['revision']))
            except Exception as error:
                result.update(download_status='failed' if not path.exists() else 'complete',parse_status='failed',error=repr(error))
            results.append(result);stream.write(json.dumps(result,ensure_ascii=False)+'\n');stream.flush()
            if (index+1)%10==0:print(index+1,'/',len(sample),'sample documents checked',flush=True)
    (DEST/f'{prefix}pdf_sample_results.json').write_text(json.dumps(dict(records=results,limitation='Parser feasibility only; parsed amounts require original-document review before becoming model inputs.'),ensure_ascii=False,indent=2)+'\n')
    frame=pd.DataFrame(results)
    summary=frame.groupby(['exchange','revision','parse_status']).size().rename('documents')
    summary.to_csv(DEST/f'{prefix}pdf_sample_summary.csv');print(summary.to_string(),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--exchange',choices=['SZ','SH'])
    run(parser.parse_args().exchange)
