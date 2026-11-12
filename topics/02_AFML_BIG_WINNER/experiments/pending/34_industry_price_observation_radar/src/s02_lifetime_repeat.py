"""Descriptive lifetime associations, never primary success accounting."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def associate(new, processes):
    assert new.alert_id.is_unique
    groups={k:g for k,g in processes.groupby(['era','industry_code'])}
    seen={};seen_family={};rows=[];alerts=[]
    for r in new.sort_values(['day','alert_id']).itertuples():
        g=groups.get((r.era,r.industry_code),processes.iloc[:0])
        active=g[(g.start_day_i<=r.day)&(g.end_day_i>=r.day)]
        links=[]
        for p in active.itertuples():
            prior=seen.get(p.process_id,[])
            links.append(dict(alert_id=r.alert_id,day=int(r.day),era=r.era,industry_code=r.industry_code,
                process_id=p.process_id,family_id=p.family_id,origin=int(p.start_day_i),end=int(p.end_day_i),
                left_unknown=bool(p.left_origin_uncertain),right_censored=bool(p.right_censored),
                repeat=bool(prior),previous_alert_id=prior[-1][0] if prior else None,
                previous_day=prior[-1][1] if prior else None,first_day=prior[0][1] if prior else int(r.day),
                previous_ids=[x[0] for x in prior],beyond60=bool(r.day-p.start_day_i>60)))
        known=[x for x in links if not x['left_unknown']]
        families=set(active.family_id)
        family_repeat=any(seen_family.get(x) for x in families)
        alerts.append(dict(alert_id=r.alert_id,day=int(r.day),era=r.era,industry_code=r.industry_code,
            associations=len(links),known_origin_associations=len(known),
            known_repeat=any(x['repeat'] for x in known),
            unknown_only_repeat=any(x['repeat'] for x in links) and not any(x['repeat'] for x in known),
            beyond60_known_repeat=any(x['repeat'] and x['beyond60'] for x in known),
            mixed_first_repeat=any(x['repeat'] for x in links) and any(not x['repeat'] for x in links),
            left_unknown_reference=any(x['left_unknown'] for x in links),
            right_censored_reference=any(x['right_censored'] for x in links),family_repeat=family_repeat))
        rows.extend(links)
        for x in links:seen.setdefault(x['process_id'],[]).append((r.alert_id,int(r.day)))
        for f in families:seen_family.setdefault(f,[]).append(r.alert_id)
    return pd.DataFrame(alerts),pd.DataFrame(rows)


def main():
    out=EP/'outputs/s02';out.mkdir(exist_ok=True)
    if (out/'summary.json').exists():raise FileExistsError('already evaluated')
    processfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet'
    p=pd.read_parquet(processfile);inputs={str(processfile):sha(processfile)}
    plan=EP/'rounds/S02_lifetime_repeat_plan.md';inputs[str(plan)]=sha(plan)
    specs=[('r01','r01/events.parquet',True)]
    specs += [(group+'_'+arm,group+'/'+arm+'_events.parquet',True) for group,arms in [('r01_capacity',['cap3','cap5','cap10']),('r01_delay',['delay0','delay5','delay10'])] for arm in arms]
    specs += [(group+'_'+arm,group+'/'+arm+'_evaluated.parquet',False) for group in ['r02','r03'] for arm in ['A','B']]
    results={};tables={}
    for name,path,pool in specs:
        src=EP/'outputs'/path;inputs[str(src)]=sha(src);data=pd.read_parquet(src)
        operational={'status':'NOT_MODELED'}
        if pool:
            new=data[data.event.eq('NEW')].rename(columns={'observation_id':'alert_id','day_i':'day'}).copy()
            previous={};reentries=0
            for r in new.sort_values(['day','alert_id']).itertuples():
                key=(r.era,r.industry_code)
                if key in previous:
                    old=previous[key];ex=data[data.event.eq('EXIT')&data.observation_id.eq(old.alert_id)]
                    assert len(ex)==1 and old.day<=int(ex.iloc[0].day_i)<r.day,(name,r.alert_id)
                    reentries+=1
                previous[key]=r
            operational=dict(updates=int(data.event.eq('UPDATE').sum()),unknown_suspended=int(data.reason.eq('SUSPENDED_UNKNOWN').sum()),
                             reentries=reentries,all_reentries_have_prior_exit=True,
                             exit_reasons=data.loc[data.event.eq('EXIT'),'reason'].value_counts().to_dict())
        else:new=data
        a,l=associate(new,p)
        assert len(a)==len(new) and a.alert_id.is_unique
        assert ((l.day>=l.origin)&(l.day<=l.end)).all()
        rr=l[l.repeat];assert (rr.previous_day<rr.day).all() and (rr.previous_alert_id!=rr.alert_id).all()
        assert not l.duplicated(['alert_id','process_id']).any()
        assert a.associations.sum()==len(l)
        folder=out/name;folder.mkdir(exist_ok=True)
        a.to_parquet(folder/'alerts.parquet',index=False);l.to_parquet(folder/'associations.parquet',index=False)
        result=dict(total_new=len(a),referenced_new=int(a.associations.gt(0).sum()),association_rows=len(l),
                    no_registered_reference=int(a.associations.eq(0).sum()),overlapping_references=int(a.associations.gt(1).sum()),operational=operational)
        for k in ['known_repeat','unknown_only_repeat','beyond60_known_repeat','mixed_first_repeat','left_unknown_reference','right_censored_reference','family_repeat']:
            result[k]=int(a[k].sum())
        result['known_repeat_rate_all_new']=result['known_repeat']/len(a)
        results[name]=result;tables[name]=a
        print(name,json.dumps(result,ensure_ascii=False),flush=True)
    for name in ['r01_capacity_cap5','r01_delay_delay0']:
        # Stable observation IDs and associations should reproduce the main baseline.
        pd.testing.assert_frame_equal(tables[name].reset_index(drop=True),tables['r01'].reset_index(drop=True))
        assert results[name]==results['r01'],name
    receipt=dict(scope='S02 descriptive lifetime accounting; no success relabeling',inputs=inputs,source_sha256=sha(Path(__file__)),main_reproduction=True,results=results)
    (out/'summary.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
