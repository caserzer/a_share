"""Read local member prices, reproduce support, then seal paired predictions."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from member_breadth_math import member_arrays,breadth_counts,score_candidates


def main():
    out=EP/'outputs/r03';out.mkdir(exist_ok=True)
    if (out/'prediction_seal.json').exists():raise FileExistsError('R03 sealed')
    configfile=EP/'configs/r03_breadth.json';c=json.loads(configfile.read_text())
    receiptfile=PRIOR/'receipt.json';receipt=json.loads(receiptfile.read_text())
    r02seal=EP/'outputs/r02/prediction_seal.json';old=json.loads(r02seal.read_text())
    commonfile=EP/'outputs/r02/common_catalog.parquet';assert sha(commonfile)==old['artifacts'][commonfile.name]
    supportfile=EP/'outputs/breadth_feasibility/weekly_support.parquet'
    sr=json.loads((EP/'outputs/breadth_feasibility/receipt.json').read_text());assert sha(supportfile)==sr['output_sha']
    afile=CACHE/'extension_v2/products/assignments.parquet'
    a=pd.read_parquet(afile,columns=['month','date','security_id','industry_code','unresolved','level','era']);a=a[a.level.eq('L3')]
    calendarfile=Path(next(x for x in receipt['inputs'] if x.endswith('/calendar.parquet')))
    cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values()
    ids=sorted(a.security_id.unique());idmap={s:i for i,s in enumerate(ids)}
    paths={Path(f).stem:Path(f) for f in receipt['price_reads']}
    valid=np.zeros((len(cal),len(ids)),bool);up=np.zeros_like(valid);prefixchecks=0
    for i,sid in enumerate(ids):
        file=paths[sid];assert sha(file)==receipt['price_reads'][str(file)]
        raw=pd.read_parquet(file,columns=['date','qfq_close','close_conflict','factor_chain_id'])
        valid[:,i],up[:,i]=member_arrays(raw,cal,c['member_lookback'])
        if i%500==0:
            for end in [1000,1800]:
                sv,su=member_arrays(raw[raw.date<=cal[end-1]],cal[:end],c['member_lookback'])
                assert np.array_equal(sv,valid[:end,i]) and np.array_equal(su,up[:end,i]);prefixchecks+=1
        if (i+1)%1000==0:print(f'member price features {i+1}/{len(ids)}',flush=True)
    cohorts={(era,str(month),code):(np.array([idmap[s] for s in g.security_id]),int(g.unresolved.max()),g.date.max()) for (era,month,code),g in a.groupby(['era','month','industry_code'])}
    common=pd.read_parquet(commonfile);rows=[]
    for r in common.itertuples():
        key=(r.era,str(r.date.to_period('M')-1),r.industry_code);cohort=cohorts.get(key)
        z=dict(era=r.era,industry_code=r.industry_code,date=r.date)
        if cohort is None:z.update(supported=False,membership_status='UNKNOWN_PRIOR_MONTH')
        else:
            si,u,anchor=cohort;assert anchor<r.date
            z.update(breadth_counts(len(si)+u,int(valid[r.day_i,si].sum()),int(up[r.day_i,si].sum()),c['minimum_valid_members'],c['minimum_coverage']))
            z['membership_status']='HISTORICAL_PROXY'
        rows.append(z)
    features=pd.DataFrame(rows);previous=pd.read_parquet(supportfile)
    check=features.merge(previous,on=['era','industry_code','date'],validate='one_to_one')
    assert len(check)==len(previous) and check.supported.eq(check.support5_80).all()
    known=check.members.notna();assert check.loc[known,'valid_members'].eq(check.loc[known,'history20_known']).all()
    features.to_parquet(out/'breadth_features.parquet',index=False)
    joined=common.merge(features,on=['era','industry_code','date'],validate='one_to_one')
    joined['breadth_state']=np.where(joined.supported,'SUPPORTED','DATA_INSUFFICIENT_BREADTH')
    joined.to_parquet(out/'full_catalog.parquet',index=False)
    predictions=[];weeks=[]
    for (era,date),g in joined.groupby(['era','date'],sort=True):
        allc=g[g.ticket_id.notna()];eligible=allc[allc.supported]
        ranked=score_candidates(eligible,c['breadth_weight'])
        count=min(c['weekly_new_cap'],len(ranked))
        for arm in ['A','B']:
            selected=ranked.sort_values([f'score_{arm}','industry_code'],ascending=[False,True]).head(count)
            for r in selected.to_dict('records'):predictions.append(dict(**r,arm=arm,observation_id=f'R03|{arm}|{r["ticket_id"]}'))
        weeks.append(dict(era=era,date=date,common_tickets=len(allc),supported_tickets=len(eligible),new_A=count,new_B=count))
    pd.DataFrame(predictions).to_parquet(out/'predictions.parquet',index=False)
    pd.DataFrame(weeks).to_parquet(out/'weekly_burden.parquet',index=False)
    source=[configfile,receiptfile,afile,calendarfile,r02seal,commonfile,supportfile,EP/'rounds/R03_member_breadth_plan.md',EP/'src/member_breadth_math.py',EP/'tests/test_member_breadth.py',Path(__file__)]
    result=dict(status='PAIRED_PREDICTIONS_SEALED_NOT_EVALUATED',source={str(x):sha(x) for x in source},artifacts={x.name:sha(x) for x in out.glob('*.parquet')},
                price_partitions=len(ids),sample_stock_prefix_checks=prefixchecks,support_rows_reproduced=len(check),
                weeks=len(weeks),common_tickets=sum(x['common_tickets'] for x in weeks),supported_tickets=sum(x['supported_tickets'] for x in weeks),
                new_per_arm=len(predictions)//2,equal_weekly_new_counts=True)
    (out/'prediction_seal.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source','artifacts']},ensure_ascii=False))


if __name__=='__main__':main()
