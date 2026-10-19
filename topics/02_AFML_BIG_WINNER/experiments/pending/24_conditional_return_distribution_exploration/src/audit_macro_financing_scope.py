"""Expanded diagnostic of unused loan field and annual totals actually used."""
import json
from pathlib import Path
import pandas as pd
from build_domestic_macro import read_sources,CACHE,DEST
from build_margin_information import digest

def run():
    raw,_=read_sources();p=CACHE/'RPT_ECONOMY_RMB_LOAN.json';data=pd.DataFrame(json.loads(p.read_text())['result']['data'])
    data.index=pd.to_datetime(data.REPORT_DATE).dt.to_period('M')
    pairs=pd.concat([data.RMB_LOAN.rename('vendor_loan'),raw.tsf_rmb_loan.rename('tsf_entity_loan')],axis=1).dropna()
    pairs['difference']=pairs.vendor_loan-pairs.tsf_entity_loan;pairs.to_csv(DEST/'loan_scope_probe.csv')
    mismatch=pairs[pairs.difference.abs()>.5]
    # Both loan fields are excluded from every input feature. Do not repair them with hindsight.
    cases=[(2022,320100,'https://www.ndrc.gov.cn/fggz/fgzh/gnjjjc/hbjr/202301/t20230130_1347689.html'),
           (2023,355900,'https://www.china-cba.net/Index/show/catid/33/id/42988.html'),
           (2024,322600,'https://jrj.sh.gov.cn/SCGK194/20250115/0e2b8ef740064ad6ad14b0a2e609c2f5.html'),
           (2025,356000,'https://www.stats.gov.cn/zt_18555/zthd/lhfw/2026lhzt/2026hgjj/202602/t20260228_1962667.html')]
    checks=[]
    for year,expected,url in cases:
        rows=raw[raw.index.year==year].tsf;assert len(rows)==12 and rows.notna().all()
        actual=float(rows.sum());assert abs(actual-expected)<=50
        checks.append(dict(year=year,field='tsf',value=actual,official=expected,tolerance=50,official_url=url))
    audit=dict(probe_only_loan_fields_excluded=True,source_path=str(p),source_sha256=digest(p),overlap_months=len(pairs),
        equal_within_one_yuan100m_rounding=int(pairs.difference.abs().le(.5).sum()),
        mismatched_months={str(k):dict(v) for k,v in mismatch.iterrows()},annual_tsf_crosschecks=checks,
        interpretation='135/136 overlapping loan observations agree within integer-CNY100m rounding. 2022-06 is inconsistent; neither loan field is used. Annual total TSF checks do not certify all monthly vintages.')
    (DEST/'financing_scope_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (DEST/'loan_scope_probe.json').write_text(json.dumps({k:v for k,v in audit.items() if k!='annual_tsf_crosschecks'},indent=2)+'\n')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':run()
