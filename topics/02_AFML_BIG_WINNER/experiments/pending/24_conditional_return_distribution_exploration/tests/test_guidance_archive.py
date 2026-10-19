import pytest
from parse_guidance_archive_pilot import amount_range,parse_table
import download_guidance_catalog as catalog


def test_loss_range_sign_and_units():
    assert amount_range('亏损：500 万元—1,000 万元')==[-10000000,-5000000]
    assert amount_range('盈利：0.2亿元至3,000万元')==[20000000,30000000]


@pytest.mark.parametrize('cell',['增长：20%至30%','盈利：1000万元以上','-500万元至100万元','盈利：10至20','盈利：10万元–20万元，同比30%'])
def test_ambiguous_amounts_are_rejected(cell):
    with pytest.raises(ValueError):amount_range(cell)


def test_revision_uses_new_column_not_original_or_prior_year():
    rows=[['项目','本报告期',None,'上年同期'],[None,'原预计','最新预计',None],
          ['归属于上市公司股东的净利润','盈利：2200万元–3300万元','亏损：500万元–1000万元','亏损：38033万元']]
    result=parse_table(rows,True)
    assert result['low_cny']==-10000000 and result['high_cny']==-5000000
    with pytest.raises(ValueError):parse_table(rows,False)


def test_deducted_profit_is_not_attributable_profit():
    rows=[['项目','本报告期'],['扣除非经常性损益后的净利润','盈利：10万元–20万元']]
    with pytest.raises(ValueError):parse_table(rows,False)


def test_access_denial_stops_without_retry(tmp_path,monkeypatch):
    calls=[]
    class Denied:
        status_code=403
        headers={'Content-Type':'application/octet-stream'}
        content=b''
    monkeypatch.setattr(catalog,'CACHE',tmp_path)
    monkeypatch.setattr(catalog,'DEST',tmp_path)
    monkeypatch.setattr(catalog.time,'sleep',lambda _:None)
    monkeypatch.setattr(catalog.requests,'post',lambda *a,**k:calls.append(k) or Denied())
    with pytest.raises(catalog.CatalogAccessStopped):catalog.fetch('002311','org')
    assert len(calls)==1
    assert (tmp_path/'access_stop.json').exists()
    assert not (tmp_path/'002311_1.json').exists()


def test_uncached_stock_is_unknown_not_empty(tmp_path,monkeypatch):
    monkeypatch.setattr(catalog,'CACHE',tmp_path)
    def forbidden(*a,**k):raise AssertionError('Offline audit must not request network')
    monkeypatch.setattr(catalog.requests,'post',forbidden)
    result=catalog.fetch('002311','org',cache_only=True)
    assert result['status']=='unqueried' and 'announcements' not in result
