import pandas as pd
import pytest
from download_exchange_guidance_catalog import quarters,flatten_sse,fetch_window
from sample_exchange_guidance_pdfs import sample_documents


def test_quarter_windows_cover_period_without_gaps_or_overlap():
    windows=list(quarters())
    assert windows[0][0]=='2017-01-01' and windows[-1][1]=='2026-04-30'
    for index,(start,end) in enumerate(windows):
        assert pd.Timestamp(end)<pd.Timestamp(start)+pd.DateOffset(months=3)
        if index:assert pd.Timestamp(start)==pd.Timestamp(windows[index-1][1])+pd.Timedelta(days=1)


def test_sse_grouped_attachments_are_preserved():
    groups=[[{'id':1},{'id':2}],[{'id':3}]]
    assert flatten_sse({'result':groups,'pageHelp':{'data':groups}})==[{'id':1},{'id':2},{'id':3}]
    with pytest.raises(AssertionError):flatten_sse({'result':groups,'pageHelp':{'data':groups[:1]}})


def test_sse_overlong_query_rejected_before_network():
    with pytest.raises(AssertionError):fetch_window('SH','2017-01-01','2026-04-30',['600519'])


def test_pdf_sampling_is_order_invariant_and_keeps_revision_strata():
    records=[dict(exchange=exchange,publish_date='2024-01-20',title='年度业绩预告'+suffix,url=f'https://example.test/{exchange}/{suffix}/{i}.pdf')
             for exchange in ('SH','SZ') for suffix in ('','修正公告') for i in range(5)]
    sample=sample_documents(records)
    assert sample==sample_documents(list(reversed(records)))
    assert len(sample)==8
    for exchange in ('SH','SZ'):
        for revision in (False,True):
            assert sum(r['exchange']==exchange and r['revision']==revision for r in sample)==2
