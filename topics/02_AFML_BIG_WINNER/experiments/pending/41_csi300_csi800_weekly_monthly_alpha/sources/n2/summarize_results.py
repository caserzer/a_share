from pathlib import Path
import json,hashlib
import pandas as pd
OUT=Path(__file__).resolve().parent
def main():
    cov=pd.read_csv(OUT/'coverage.csv')
    cov['month']=cov.signal_date.str[:7]
    cov['sparse']=cov.nonzero<3
    cov.groupby(['spec','month']).agg(dates=('entry_idx','size'),sparse_days=('sparse','sum'),candidates=('candidates','sum'),covered=('covered_candidates','sum'),nonzero=('nonzero','sum'),reserved_slots=('baseline_buy_slots','sum'),covered_slots=('covered_buy_slots','sum'),adjusted_slots=('distinct_changed','sum')).to_csv(OUT/'sparse_months.csv')
    c=pd.read_parquet(OUT/'choices.parquet')
    c['covered']=c.score.notna()
    c['nonzero']=c.covered & c.score.ne(0)
    c.groupby(['spec','recent_financial_report']).agg(reserves=('score','size'),covered=('covered','sum'),nonzero=('nonzero','sum'),mean_info_age=('age','mean')).to_csv(OUT/'report_recency.csv')
    f=pd.read_csv(OUT/'outcome_funds.csv')
    f=f[f.changed & f.covered]
    print(f.groupby(['spec','segment','outcome']).executed_net_buy.sum())
    origin=next(OUT.parents[2].glob('35_*'))/'data'
    files=[origin/'r11_analyst_forecasts.parquet',origin/'financial_archive_all_market.parquet',OUT.parents[1]/'p2/results/scores.parquet',OUT.parent/'reserves.py',OUT.parent/'execution_audit.py',*OUT.glob('*.py')]
    check=pd.read_parquet(OUT/'daily.parquet')
    assert check[['nav','fee','cash']].notna().all().all()
    paths=files+[OUT/'REPORT.md']+[p for p in OUT.iterdir() if p.suffix in ['.csv','.parquet','.json'] and p.name!='verification.json']
    (OUT/'verification.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
if __name__=='__main__':main()
