import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from etf_archive_r125 import parse_state,walk,date_ok

def test_strict_state_boundaries():
    modern='<!-- LONG_OPPORTUNITY_STATE_BEGIN\n{"x":1}\nLONG_OPPORTUNITY_STATE_END -->'
    legacy='<!-- LONG_OPPORTUNITY_STATE_BEGIN -->\n{"x":1}\n<!-- LONG_OPPORTUNITY_STATE_END -->'
    assert parse_state(modern)==parse_state(legacy)=={'x':1}
    for text in [modern+modern,modern+' EXTRA','{"x":1}',modern.replace('{"x":1}','[]')]:
        with pytest.raises(ValueError):parse_state(text)

def test_occurrence_paths_and_invalid_calendar_dates():
    x={'a/b~':[{'fund_share_units':None},{'fund_share_units':12}]}
    assert [p for p,v in walk(x)]==['/a~1b~0/0','/a~1b~0/1']
    assert date_ok('20260228') and not date_ok('20260230') and not date_ok('2026-02-28')
