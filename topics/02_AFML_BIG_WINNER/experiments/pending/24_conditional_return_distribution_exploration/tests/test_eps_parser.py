import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from parse_eps_forecasts import parse_paragraph,parse_report,parse_profit_paragraph


def test_explicit_years_not_intervening_growth_rates():
    p='测算2020-2022年的收入增速分别为10%、26%、20%，净利润增速分别为13%、34%、22%，对应EPS分别为36.93、49.61、60.66元。'
    assert parse_paragraph(p,2020)==[{2020:36.93,2021:49.61,2022:60.66}]
    assert parse_paragraph('预计2023/24/25年EPS为0.8/1.1/1.4元。',2023)==[{2023:.8,2024:1.1,2025:1.4}]
    assert parse_paragraph('预计2024-2026年EPS为0.71、0.78、0.82元，当前PE为12、11、10倍。',2024)==[{2024:.71,2025:.78,2026:.82}]
    assert parse_paragraph('预计21-23年每股收益（EPS）分别为0.85元，0.93元及1.00元/股，对应PE为10倍。',2021)==[{2021:.85,2022:.93,2023:1.0}]


def test_does_not_guess_missing_years_or_mismatched_value_counts():
    assert not parse_paragraph('预计未来三年EPS分别为1.0/1.2/1.5元。',2023)
    assert not parse_paragraph('2023-2025年EPS分别为1.0/1.2元。',2023)
    assert not parse_paragraph('2023-2025年EPS增速分别为10/20/30%。',2023)
    assert not parse_paragraph('2023-2025年EPS为10/20/30%。',2023)
    assert not parse_paragraph('2023-2025年EPS由1.0/1.2/1.5调整至0.8/1.0/1.2元。',2023)


def test_current_widgets_excluded_and_later_source_date_used():
    html='<div>2026-2028年EPS为99/100/101元</div><div id="ctx-content"><p>2020-2022年EPS为1/2/3元。</p></div><script>var x={"notice_date":"2020-10-30 00:00:00"};</script>'
    r=parse_report(html,'2020-10-29')
    assert r['forecasts']=={2020:1.,2021:2.,2022:3.}
    assert r['available_date']=='2020-10-30'
    conflict=html.replace('</div><script>','<p>2020-2022年EPS为1.5/2.5/3.5元。</p></div><script>')
    assert parse_report(conflict,'2020-10-29')['status']=='conflicting_forecasts'


def test_net_profit_units_and_metrics_are_explicit():
    text='预计2023-2025年营业收入为40/50/60亿元，归母净利润分别为3.2亿元、4.8亿元和5.6亿元。'
    assert parse_profit_paragraph(text,2023)==[{2023:3.2e8,2024:4.8e8,2025:5.6e8}]
    assert parse_profit_paragraph('预计2023/24/25年归母净利润为3.2/4.8/5.6亿元。',2023)==[{2023:3.2e8,2024:4.8e8,2025:5.6e8}]
    assert not parse_profit_paragraph('预计2023-2025年归母净利润同比增长3/4/5%。',2023)
    assert not parse_profit_paragraph('预计2023-2025年扣非归母净利润为3/4/5亿元。',2023)
    assert not parse_profit_paragraph('预计2023-2025年归母净利润为3/4/5。',2023)
    assert not parse_profit_paragraph('预计2023-2025年不考虑股权变动影响后的归母净利润为3/4/5亿元。',2023)


def test_date_after_single_forecast_is_not_a_second_profit():
    assert not parse_profit_paragraph('2024/2025年预期归母净利润由11.6/14.7亿元上调至13.9/22.0亿元，并预测2026年归母净利润为26.6亿元，2024年4月25日收盘价对应PE为41.7/26.3/21.7倍。',2024)
    assert not parse_profit_paragraph('2023-2024年利润从24/32亿元调整至19/27亿元，预计2025年归母净利润为33.94亿元，2023-2025年利润增速为20%/40%/22%。',2023)
    assert not parse_profit_paragraph('2025年和2026年一季度，公司实现营收分别为720亿元和204亿元，实现归母净利润分别为293亿元和82亿元。',2026)
    assert not parse_paragraph('2023/2024年EPS由1/2元调整至0.8/1.8元，预计2025年EPS为2.3元，2024年股价上涨。',2024)
