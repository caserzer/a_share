import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from source_scan_r27 import scan_paragraph


def test_currency_suffix_not_hidden_by_matched_unit():
 bad='预计2025-2027年归母净利润分别为20.49/24.44/29.67万元/吨，EPS分别为1.15/1.38/1.67元。'
 flags=scan_paragraph(bad,2025)
 assert any(x['kind']=='profit_noncurrency_dimension' for x in flags)
 good=bad.replace('万元/吨','亿元')
 assert not any(x['kind']=='profit_noncurrency_dimension' for x in scan_paragraph(good,2025))


def test_explicit_year_mismatch_review_flag_not_correction():
 text='预计2024-2026年归母净利润分别为29.52亿元、48.10亿元、61.36亿元。预计2023-2025年每股收益分别为0.45元、0.73元、0.93元。'
 flags=scan_paragraph(text,2024);f=next(x for x in flags if x['kind']=='cross_basis_year_sets')
 assert f['profit_years']==[2024,2025,2026] and f['eps_years']==[2023,2024,2025]
 assert f['basis']=='review_both'


def test_share_basis_context_and_normal_pair():
 text='预计2025-2027年归母净利润为10/20/30亿元，按送转股前股本EPS为1/2/3元。'
 assert any(x['kind']=='share_basis_language' for x in scan_paragraph(text,2025))
 assert scan_paragraph(text.replace('按送转股前股本',''),2025)==[]
