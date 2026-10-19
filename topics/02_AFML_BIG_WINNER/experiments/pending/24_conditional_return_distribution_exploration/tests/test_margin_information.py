import io
import json
import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from build_margin_information import parse_szse, SZ_FIELDS


def fixture():
    row = {'证券代码':'000001', '证券简称':'示例', '融资买入额(元)':150711586,
           '融资余额(元)':2891944800, '融券卖出量(股/份)':2507679, '融券余量(股/份)':98709432,
           '融券余额(元)':2278213689, '融资融券余额(元)':5170158489}
    table = io.BytesIO(); pd.DataFrame([row]).to_excel(table, index=False)
    labels = {k: ('亿元' if scale==1e8 else '万元' if k=='jrrjye' else '万股/万份') for k, (_,scale) in SZ_FIELDS.items()}
    display = dict(zqdm='000001', jrrzmr='1.50', jrrzye='28.91', jrrjmc='250.76', jrrjyl='9,870.94', jrrjye='227,821.36', jrrzrjye='51.70')
    tables = [dict(metadata=dict(tabkey='tab1',subname='2021-01-27', cols={k:'亿元' for k in ['jrrzmr','jrrzye','jrrjye']}),
                   data=[dict(jrrzmr='438.08',jrrzye='7,433.74',jrrjye='554.91')]),
              dict(metadata=dict(tabkey='tab2',subname='2021-01-27',recordcount=1,cols=labels),data=[display])]
    return tables, table.getvalue()


def test_uses_precise_excel_and_explicit_units():
    tables, body = fixture(); frame, market = parse_szse(json.dumps(tables), body, '20210127')
    assert frame.iloc[0].instrument == 'SZ000001'
    assert frame.iloc[0].buy == 150711586
    assert frame.iloc[0].lending_quantity == 98709432
    assert market['financing'] == 743374000000


@pytest.mark.parametrize('fault', ['date','count','unit','sample'])
def test_rejects_wrong_date_incomplete_export_wrong_units_and_stale_values(fault):
    tables, body = fixture()
    if fault == 'date': tables[1]['metadata']['subname'] = '2021-01-26'
    if fault == 'count': tables[1]['metadata']['recordcount'] = 2
    if fault == 'unit': tables[1]['metadata']['cols']['jrrzye'] = '万元'
    if fault == 'sample': tables[1]['data'][0]['jrrzye'] = '29.91'
    with pytest.raises(AssertionError): parse_szse(json.dumps(tables), body, '20210127')
