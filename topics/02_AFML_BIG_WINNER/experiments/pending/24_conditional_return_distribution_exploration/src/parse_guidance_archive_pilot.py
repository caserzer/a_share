"""Small original-document pilot; unsupported tables remain explicitly unparsed."""
import json
import re
from pathlib import Path
import pymupdf
import pandas as pd
from prepare_panel import OUT
from build_margin_information import digest


def compact(value):
    return re.sub(r'\s+', '', value or '').replace(',', '').replace('，', '')


def amount_range(cell):
    """Only explicit two-ended CNY profit/loss ranges, no percentage inference."""
    value=compact(cell)
    match=re.fullmatch(r'(盈利|亏损)[:：]([0-9]+(?:\.[0-9]+)?)(万元|亿元|元)[–—~～至-]([0-9]+(?:\.[0-9]+)?)(万元|亿元|元)',value)
    if match is None:raise ValueError(f'Unsupported amount cell: {value}')
    sign=-1 if match[1]=='亏损' else 1
    units={'元':1,'万元':10000,'亿元':100000000}
    return sorted([sign*float(match[2])*units[match[3]],sign*float(match[4])*units[match[5]]])


def parse_table(rows,revised):
    clean=[[compact(cell) for cell in row] for row in rows]
    targets=[i for i,row in enumerate(clean) if row and '归属于' in row[0] and '净利润' in row[0]
             and '扣非' not in row[0] and '扣除' not in row[0]]
    if len(targets)!=1:raise ValueError('No unique attributable-profit row')
    row_index=targets[0];headers=clean[:row_index]
    labels=('最新预计','修正后') if revised else ('本报告期',)
    columns={j for row in headers for j,cell in enumerate(row) if cell in labels}
    if len(columns)!=1:raise ValueError('No unique current-version column')
    column=columns.pop()
    if not revised and any(cell in ('原预计','修正前','最新预计','修正后') for row in headers for cell in row):
        raise ValueError('Revision table cannot be treated as initial forecast')
    cell=rows[row_index][column]
    low,high=amount_range(cell)
    return dict(low_cny=low,high_cny=high,source_cell=cell,column=column,row=row_index)


def run():
    folder=OUT/'r37_company_guidance_probe'
    receipts=json.loads((folder/'original_and_revised_pdf_receipts.json').read_text())['records']
    expected={'1222379842':(22000000,33000000),'1223191491':(-10000000,-5000000),
              '1222431147':(-390000000,-290000000),'1223301948':(-535000000,-435000000)}
    results=[]
    for record in receipts:
        path=Path(record['path']);assert digest(path)==record['sha256']
        parsed=[]
        with pymupdf.open(path) as document:
            for page_index,page in enumerate(document):
                for table in page.find_tables().tables:
                    try:value=parse_table(table.extract(),record['revised_title'])
                    except ValueError:continue
                    parsed.append(dict(value,page=page_index+1))
        assert len(parsed)==1,record['official_announcement_id']
        result=parsed[0];assert (result['low_cny'],result['high_cny'])==expected[record['official_announcement_id']]
        local_day=pd.to_datetime(record['official_announcement_time'],unit='ms',utc=True).tz_convert('Asia/Shanghai').date()
        archive_day=pd.Timestamp(record['url'].split('/')[-2]).date()
        results.append(dict(record,**result,available_date=str(max(local_day,archive_day))))
    (folder/'parsed_original_and_revised_pilot.json').write_text(json.dumps(dict(records=results,
        availability_rule='Both local announcement date and archive date strictly precede forecast origin.',
        scope='Four manually checked documents only; not a full-universe parser or model input.'),ensure_ascii=False,indent=2)+'\n')
    print('4 original/revised documents parsed; current-version amounts verified')


if __name__=='__main__':run()
