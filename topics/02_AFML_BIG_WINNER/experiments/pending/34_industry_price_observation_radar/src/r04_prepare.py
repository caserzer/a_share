"""Read local member prices, reproduce support, then seal paired predictions."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from member_volume_math import volume_ratio,score_candidates


def main():
    out=EP/'outputs/r04';out.mkdir(exist_ok=True)
    if (out/'prediction_seal.json').exists():raise FileExistsError('R04 sealed')
    configfile=EP/'configs/r04_volume.json';c=json.loads(configfile.read_text())
    receiptfile=PRIOR/'receipt.json';receipt=json.loads(receiptfile.read_text())
    r02seal=EP/'outputs/r02/prediction_seal.json';old=json.loads(r02seal.read_text())
    commonfile=EP/'outputs/r02/common_catalog.parquet';assert sha(commonfile)==old['artifacts'][commonfile.name]
    supportfile=EP/'outputs/activity_feasibility/weekly_support.parquet'
    sr=json.loads((EP/'outputs/activity_feasibility/receipt.json').read_text());assert sha(supportfile)==sr['outputs']['weekly_support.parquet']
    afile=CACHE/'extension_v2/products/assignments.parquet'
    a=pd.read_parquet(afile,columns=['month','date','security_id','industry_code','unresolved','level','era']);a=a[a.level.eq('L3')]
    calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values()
    ids=sorted(a.security_id.unique());idmap={s:i for i,s in enumerate(ids)}
    paths={Path(f).stem:Path(f) for f in receipt['price_reads']}
    ratios=np.full((len(cal),len(ids)),np.nan);prefixchecks=0
    for i,sid in enumerate(ids):
        file=paths[sid];assert sha(file)==receipt['price_reads'][str(file)]
        raw=pd.read_parquet(file,columns=['date','volume','volume_conflict'])
        ratios[:,i]=volume_ratio(raw,cal,c['short_sessions'],c['prior_sessions'])
        if i%500==0:
            for end in [1000,1800]:
                sv=volume_ratio(raw[raw.date<=cal[end-1]],cal[:end],c['short_sessions'],c['prior_sessions'])
                np.testing.assert_allclose(sv,ratios[:end,i],equal_nan=True);prefixchecks+=1
        if (i+1)%1000==0:print(f'member price features {i+1}/{len(ids)}',flush=True)
    cohorts={(era,str(month),code):(np.array([idmap[s] for s in g.security_id]),int(g.unresolved.max()),g.date.max()) for (era,month,code),g in a.groupby(['era','month','industry_code'])}
    common=pd.read_parquet(commonfile);rows=[]
    for r in common.itertuples():
        key=(r.era,str(r.date.to_period('M')-1),r.industry_code);cohort=cohorts.get(key)
        z=dict(era=r.era,industry_code=r.industry_code,date=r.date)
        if cohort is None:z.update(supported=False,membership_status='UNKNOWN_PRIOR_MONTH')
        else:
            si,u,anchor=cohort;assert anchor<r.date
            values=ratios[r.day_i,si];count=int(np.isfinite(values).sum());coverage=count/(len(si)+u)
            supported=count>=c['minimum_valid_members'] and coverage>=c['minimum_coverage']
            z.update(valid_members=count,coverage=coverage,supported=supported,volume_ratio=float(np.median(values[np.isfinite(values)])) if supported else None)
            z['membership_status']='HISTORICAL_PROXY'
        rows.append(z)
    features=pd.DataFrame(rows);previous=pd.read_parquet(supportfile)
    check=features.merge(previous,on=['era','industry_code','date'],validate='one_to_one')
    assert len(check)==len(previous) and check.supported.eq(check.volume_supported).all()
    known=check.membership_known;assert check.loc[known,'valid_members'].eq(check.loc[known,'volume_known_members']).all()
    features.to_parquet(out/'volume_features.parquet',index=False)
    joined=common.merge(features,on=['era','industry_code','date'],validate='one_to_one')
    joined['volume_state']=np.where(joined.supported,'SUPPORTED','DATA_INSUFFICIENT_VOLUME')
    joined.to_parquet(out/'full_catalog.parquet',index=False)
    predictions=[];weeks=[]
    for (era,date),g in joined.groupby(['era','date'],sort=True):
        allc=g[g.ticket_id.notna()];eligible=allc[allc.supported]
        ranked=score_candidates(eligible,c['volume_weight'])
        count=min(c['weekly_new_cap'],len(ranked))
        for arm in ['A','B']:
            selected=ranked.sort_values([f'score_{arm}','industry_code'],ascending=[False,True]).head(count)
            for r in selected.to_dict('records'):predictions.append(dict(**r,arm=arm,observation_id=f'R04|{arm}|{r["ticket_id"]}'))
        weeks.append(dict(era=era,date=date,common_tickets=len(allc),supported_tickets=len(eligible),new_A=count,new_B=count))
    pd.DataFrame(predictions).to_parquet(out/'predictions.parquet',index=False)
    pd.DataFrame(weeks).to_parquet(out/'weekly_burden.parquet',index=False)
    source=[configfile,receiptfile,afile,calendarfile,r02seal,commonfile,supportfile,EP/'rounds/R04_volume_plan.md',EP/'src/member_volume_math.py',EP/'tests/test_member_volume.py',Path(__file__)]
    result=dict(status='PAIRED_PREDICTIONS_SEALED_NOT_EVALUATED',source={str(x):sha(x) for x in source},artifacts={x.name:sha(x) for x in out.glob('*.parquet')},
                price_partitions=len(ids),sample_stock_prefix_checks=prefixchecks,support_rows_reproduced=len(check),
                weeks=len(weeks),common_tickets=sum(x['common_tickets'] for x in weeks),supported_tickets=sum(x['supported_tickets'] for x in weeks),
                new_per_arm=len(predictions)//2,equal_weekly_new_counts=True)
    (out/'prediction_seal.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source','artifacts']},ensure_ascii=False))


if __name__=='__main__':main()
