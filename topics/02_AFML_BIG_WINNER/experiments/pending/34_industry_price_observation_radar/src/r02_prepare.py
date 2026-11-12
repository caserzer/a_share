"""Price-only preparation and sealed paired predictions before evaluation."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from r01_features import PRICE_COLUMNS
from r02_features import change_features
from r02_candidates import CommonCandidates,select


def main():
    out=EP/'outputs/r02';out.mkdir(exist_ok=True)
    if (out/'prediction_seal.json').exists():raise FileExistsError('R02 predictions sealed')
    rawfile=PRIOR/'daily_industries.parquet';gridfile=EP/'outputs/r01/weekly_catalog.parquet'
    raw=pd.read_parquet(rawfile,columns=PRICE_COLUMNS);f=change_features(raw)
    prefix_counts={}
    for cut in ['2019-06-28','2023-06-30']:
        actual=change_features(raw[raw.date<=cut]).reset_index(drop=True)
        expected=f[f.date<=cut].reset_index(drop=True)
        pd.testing.assert_frame_equal(actual,expected);prefix_counts[cut]=len(actual)
    f.to_parquet(out/'past_only_features.parquet',index=False)
    grid=pd.read_parquet(gridfile,columns=['era','industry_code','industry_name','date','day_i'])
    joined=grid.merge(f.drop(columns=['day_i']),on=['era','industry_code','date'],how='left',validate='one_to_one')
    joined['eligible']=joined.eligible.fillna(False).astype(bool)
    schedule=CommonCandidates();catalog=[];predictions=[];weeks=[]
    for (era,date,day),g in joined.groupby(['era','date','day_i'],sort=True):
        rows=schedule.step(era,date,int(day),g[['industry_code','eligible','r5','r20','delta20']].to_dict('records'))
        count=sum(x['ticket_id'] is not None for x in rows)
        chosen={arm:select(rows,score,5) for arm,score in [('A','r20'),('B','delta20')]}
        assert len(chosen['A'])==len(chosen['B'])==min(5,count)
        for arm,selected in chosen.items():
            for r in selected:predictions.append(dict(**r,arm=arm,observation_id=f'{arm}|{r["ticket_id"]}'))
        catalog.extend(rows);weeks.append(dict(era=era,date=date,candidates=count,new_A=len(chosen['A']),new_B=len(chosen['B'])))
    for name,frame in [('common_catalog.parquet',pd.DataFrame(catalog)),('predictions.parquet',pd.DataFrame(predictions)),('weekly_burden.parquet',pd.DataFrame(weeks))]:
        frame.to_parquet(out/name,index=False)
    source=[rawfile,gridfile,EP/'configs/r02_price_change.json',EP/'rounds/R02_price_change_plan.md',
            EP/'src/r01_features.py',EP/'src/r02_features.py',EP/'src/r02_candidates.py',Path(__file__),EP/'tests/test_r02_price_change.py']
    seal=dict(status='PAIRED_PREDICTIONS_SEALED_NOT_EVALUATED',prefix_rows=prefix_counts,
              source={str(x):sha(x) for x in source},artifacts={x.name:sha(x) for x in out.glob('*.parquet')},
              weeks=len(weeks),catalog_rows=len(catalog),new_per_arm=len(predictions)//2,
              candidate_tickets=sum(x['candidates'] for x in weeks),equal_weekly_new_counts=True)
    (out/'prediction_seal.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in seal.items() if k not in ['source','artifacts']},ensure_ascii=False))


if __name__=='__main__':main()
