"""As-of availability only, preserving original rows; no model or outcome scoring."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import OUT,EP
from build_margin_information import digest
from build_joint_information import SOURCE
from download_holder_counts import DEST


def run():
    manifest=json.loads((DEST/'source_manifest.json').read_text());assert manifest['failed']==0
    assert digest(SOURCE)==manifest['source_panel_sha256'];panel=pd.read_parquet(SOURCE)
    rows=[];status={};receipts=0
    for source in manifest['results']:
        status[source['code']]=source['status']
        for receipt in source['pages']:
            path=Path(receipt['path']);assert digest(path)==receipt['sha256'];payload=json.loads(path.read_text());receipts+=1
            if source['status']=='source_no_records':
                assert payload['code']==9201 and payload['message']=='返回数据为空' and payload['result'] is None
            else:
                assert payload['success'];rows.extend(payload['result']['data'])
    raw=pd.DataFrame(rows)
    for col in ['END_DATE','HOLD_NOTICE_DATE']:raw[col]=pd.to_datetime(raw[col])
    assert not raw.duplicated(['SECURITY_CODE','END_DATE']).any()
    assert raw[['END_DATE','HOLD_NOTICE_DATE','HOLDER_NUM']].notna().all().all() and raw.HOLDER_NUM.gt(0).all()
    early=raw.HOLD_NOTICE_DATE<raw.END_DATE
    raw.loc[early].to_csv(DEST/'notice_before_period.csv',index=False)
    valid=raw[~early].copy();available=[]
    for stock,g in panel.groupby('instrument',sort=True):
        code=stock[2:];history=valid[valid.SECURITY_CODE.eq(code)].sort_values(['END_DATE','HOLD_NOTICE_DATE'])
        for date in g.date:
            known=history[history.HOLD_NOTICE_DATE.lt(date)]
            item=dict(date=date,instrument=stock,source_status=status[code],has_history=bool(len(known)),
                      selected_end=pd.NaT,selected_notice=pd.NaT,selected_count=np.nan,age_days=np.nan,
                      previous_end=pd.NaT,previous_notice=pd.NaT,previous_count=np.nan,previous_gap_days=np.nan)
            if len(known):
                current=known.iloc[-1]
                item.update(selected_end=current.END_DATE,selected_notice=current.HOLD_NOTICE_DATE,
                            selected_count=float(current.HOLDER_NUM),age_days=(date-current.END_DATE).days)
                if len(known)>1:
                    previous=known.iloc[-2]
                    item.update(previous_end=previous.END_DATE,previous_notice=previous.HOLD_NOTICE_DATE,
                                previous_count=float(previous.HOLDER_NUM),previous_gap_days=(current.END_DATE-previous.END_DATE).days)
            available.append(item)
    availability=pd.DataFrame(available)
    result=panel[['date','instrument']].merge(availability,on=['date','instrument'],how='left',sort=False,validate='one_to_one')
    pd.testing.assert_frame_equal(result[['date','instrument']],panel[['date','instrument']])
    assert len(result)==37018 and result.source_status.notna().all()
    assert (result.selected_notice.isna()|result.selected_notice.lt(result.date)).all()
    assert (result.previous_notice.isna()|result.previous_notice.lt(result.date)).all()
    assert (result.selected_end.isna()|result.selected_end.le(result.selected_notice)).all()
    result['fresh180']=result.age_days.between(0,180);result['fresh365']=result.age_days.between(0,365)
    result['previous_available']=result.previous_gap_days.between(1,370)
    result.to_parquet(OUT/'local_cache/holder_count_availability_probe.parquet',index=False)
    test=result[result.date.ge('2021-01-01')];assert len(test)==27600
    summary=test.groupby(test.date.dt.year).agg(rows=('instrument','size'),history=('has_history','sum'),fresh180=('fresh180','sum'),
         fresh365=('fresh365','sum'),previous_available=('previous_available','sum'))
    summary.to_csv(DEST/'availability_by_year.csv')
    for key in ['has_history','fresh180','fresh365','previous_available']:summary[key+'_rate']=test.groupby(test.date.dt.year)[key].mean()
    audit=dict(technical_source_and_availability_checks_passed=True,raw_rows=len(raw),source_stocks=len(status),stocks_with_records=manifest['complete'],
        stocks_vendor_no_records=manifest['source_no_records'],failed_requests=manifest['failed'],raw_page_receipts_verified=receipts,
        notice_before_period_rows_excluded=int(early.sum()),original_rows=len(result),original_test_rows=len(test),
        test_coverage={key:float(test[key].mean()) for key in ['has_history','fresh180','fresh365','previous_available']},
        uncovered_test_rows=int((~test.has_history).sum()),source_manifest_sha256=digest(DEST/'source_manifest.json'),
        availability_sha256=digest(OUT/'local_cache/holder_count_availability_probe.parquet'),
        forecast_candidate=False,goal_evidence=False,
        limitations='Vendor histories and announcement fields only; original filing vintages not certified. No-record response means unknown, never zero shareholders. Early-notice records conservatively excluded without claiming all are errors. No improvement or full original-source coverage established.')
    (DEST/'availability_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    lines=['# 股东户数历史数据覆盖检查','',
        f'原1242只股票中，{manifest["complete"]}只股票有公开历史记录，{manifest["source_no_records"]}只接口明确无记录，网络失败{manifest["failed"]}只。取得{len(raw):,}条记录；{int(early.sum())}条公告日期早于统计日的记录保守排除，其中存在上市初期记录，不能一概称为数据错误。','',
        '按每个原预测日，仅选择公告日期严格早于该日的最新统计期；前期户数也必须来自当时已公布的独立记录。原37,018行与27,600测试股票月全部保留。未知户数不填0，也不将今天的户数回填历史。','',
        '|测试年份|行数|已有公布记录|统计期不超过180天|统计期不超过365天|可用前一期记录|','|---|---|---|---|---|---|']
    for year,r in summary.iterrows():
        lines.append(f'|{year}|{int(r.rows)}|{r.has_history_rate:.2%}|{r.fresh180_rate:.2%}|{r.fresh365_rate:.2%}|{r.previous_available_rate:.2%}|')
    lines+=['','这项来源检查描述公开数据与时间对齐的可用范围；预测效果见[正式消融报告](holder_count_models_report.md)，不能用覆盖率代替准确率。不同新鲜度窗口仅用于描述覆盖，不是按预测效果挑选阈值。供应商历史版本和原始公告数值尚未全量验证。','',
        '来源：[东方财富股东户数](https://data.eastmoney.com/gdhs/)，保留每页请求参数、原始响应及哈希；[可用性核验](outputs/r36_holder_counts/availability_audit.json)、[年度覆盖](outputs/r36_holder_counts/availability_by_year.csv)、[早于统计日记录](outputs/r36_holder_counts/notice_before_period.csv)。','']
    if (DEST/'filing_crosschecks.json').exists():
        checks=json.loads((DEST/'filing_crosschecks.json').read_text());assert checks['all_four_counts_match']
        lines += ['原始公告抽核补充：', '', '原始公告抽核：宁德时代2020年年报摘要和贵州茅台2025年年报中的四个股东户数均与接口一致。两条次年3月末户数已出现在年报中，而接口标注为更晚的季报日期（分别晚2天、8天）。保留供应商日期，不按零散抽核提前回填；这不是完整历史版本认证。见[原始公告核对](outputs/r36_holder_counts/filing_crosschecks.json)。', '']
    (EP/'holder_count_data_probe.md').write_text('\n'.join(lines));print(json.dumps(audit,indent=2))


if __name__=='__main__':run()
