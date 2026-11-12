"""Payoff appendix only, read after process reflections; no rule changes or ranking."""
import json
from pathlib import Path
import pandas as pd
from onset_replay import EP,sha


def main():
    source=Path('/tmp/ep33_r01_panel.parquet')
    labels=pd.read_parquet(source,columns=['era','industry_code','block','date','day_i','return126','excess126','adverse126'])
    e=pd.read_csv(EP/'outputs/r07/episodes.csv.gz',parse_dates=['date'])
    f=e.merge(labels,on=['era','industry_code','block','date'],how='left',validate='many_to_one',indicator=True)
    rows=[]
    for method,g in f.groupby('method'):
        k=g[g.excess126.notna()];rows.append(dict(method=method,prompts=len(g),known126=len(k),unknown126=int(g.excess126.isna().sum()),
            median_excess126=k.excess126.median(),q25_excess126=k.excess126.quantile(.25),q75_excess126=k.excess126.quantile(.75),
            median_adverse126=k.adverse126.median(),positive_excess_fraction=k.excess126.gt(0).mean()))
    out=EP/'outputs/r08';pd.DataFrame(rows).to_csv(out/'secondary_payoff_appendix.csv',index=False)
    (out/'secondary_receipt.json').write_text(json.dumps({'role':'descriptive appendix read only after r08_reflection; not method selection',
        'inputs':{str(p):sha(p) for p in [source,EP/'outputs/r07/episodes.csv.gz',EP/'rounds/r08_reflection.md',Path(__file__)]},
        'limits':'overlapping episodes; different populations; no net portfolio claim'},indent=2)+'\n')
    print('Secondary appendix written; no rules adjusted.')

if __name__=='__main__':main()
