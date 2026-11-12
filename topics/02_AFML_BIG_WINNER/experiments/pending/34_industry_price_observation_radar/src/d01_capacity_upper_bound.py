"""Retrospective relaxed upper bound, not an implementable predictor."""
import json,math
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from post_alert_evaluation import post_alert_result,label_neighborhood_known,registered_rules


def main():
    out=EP/'outputs/d01';out.mkdir(exist_ok=True)
    if (out/'result.json').exists():raise FileExistsError('already evaluated')
    pfile=EP/'outputs/r00_metric_denominators/full_process_registry.parquet';allp=pd.read_parquet(pfile);p=allp[allp.mature&~allp.left_origin_uncertain]
    rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile);asof=int(raw.day_i.max());rawgroups={k:g.sort_values('day_i') for k,g in raw.groupby(['era','industry_code'])}
    gridfile=EP/'outputs/r02/common_catalog.parquet';g=pd.read_parquet(gridfile)
    g['candidate_id']=g.era+'|'+g.industry_code+'|'+g.date.dt.strftime('%Y-%m-%d')
    g['week']=g.era+'|'+g.date.dt.to_period('W-SUN').astype(str)
    assert g.candidate_id.is_unique
    supportfiles=[]
    for name in ['r03','r04']:
        f=EP/'outputs'/name/'full_catalog.parquet';supportfiles.append(f)
        s=pd.read_parquet(f,columns=['era','industry_code','date','supported']).rename(columns={'supported':name+'_supported'})
        g=g.merge(s,on=['era','industry_code','date'],validate='one_to_one')
    g['all_price_eligible']=g.eligible
    g['positive20']=g.eligible&g.r20.gt(0)
    g['r02_tickets']=g.ticket_id.notna()
    g['r03_tickets']=g.ticket_id.notna()&g.r03_supported
    g['r04_tickets']=g.ticket_id.notna()&g.r04_supported
    scopes=['all_price_eligible','positive20','r02_tickets','r03_tickets','r04_tickets']
    gg={k:v for k,v in g.groupby(['era','industry_code'])};cache={};edges=[];audit=[]
    rules=registered_rules();before,after=rules['timely_window_trading_days']
    for r in p.itertuples():
        candidates=gg[(r.era,r.industry_code)];candidates=candidates[candidates.day_i.between(r.start_day_i+before,r.start_day_i+after)]
        data=rawgroups[(r.era,r.industry_code)];ds=data.day_i.to_numpy();v=data.nav.to_numpy();b=data.block.to_numpy(float,na_value=np.nan)
        for c in candidates.itertuples():
            if c.candidate_id not in cache:cache[c.candidate_id]=label_neighborhood_known(ds,v,b,c.day_i,asof)
            known=cache[c.candidate_id]
            result=post_alert_result(ds,v,b,c.day_i,asof,process_end=int(r.end_day_i),process_end_observed=not r.right_censored)
            valid=known and result['status']=='POST_VALID'
            row=dict(candidate_id=c.candidate_id,process_id=r.process_id,week=c.week,day=int(c.day_i),origin=int(r.start_day_i),coverage_known=bool(known),post_status=result['status'],valid=bool(valid),**{k:bool(getattr(c,k)) for k in scopes})
            audit.append(row)
            if valid:edges.append(row)
    a=pd.DataFrame(audit);edge=pd.DataFrame(edges);a.to_parquet(out/'all_window_pairs.parquet',index=False)
    edge.to_parquet(out/'valid_edges.parquet',index=False)
    results={};flows=[]
    for scope in scopes:
        subset=edge[edge[scope]];graph=nx.DiGraph()
        graph.add_nodes_from(['SOURCE','SINK'])
        for r in subset.itertuples():
            week='W|'+r.week;ticket='C|'+r.candidate_id;process='P|'+r.process_id
            graph.add_edge('SOURCE',week,capacity=5);graph.add_edge(week,ticket,capacity=1)
            graph.add_edge(ticket,process,capacity=1);graph.add_edge(process,'SINK',capacity=1)
        value,flow=nx.maximum_flow(graph,'SOURCE','SINK');cut,_=nx.minimum_cut(graph,'SOURCE','SINK');assert value==cut
        chosen=[]
        for r in subset.itertuples():
            if flow['C|'+r.candidate_id].get('P|'+r.process_id,0):chosen.append(dict(scope=scope,candidate_id=r.candidate_id,process_id=r.process_id,week=r.week))
        f=pd.DataFrame(chosen);assert len(f)==value and f.candidate_id.is_unique and f.process_id.is_unique and f.groupby('week').size().max()<=5
        flows.extend(chosen)
        supported=a[a[scope]];reachable=set(subset.process_id)
        reasons={}
        for pid in p.process_id:
            rows=supported[supported.process_id.eq(pid)]
            if pid in reachable:reason='HAS_SUCCESS_EDGE'
            elif not len(rows):reason='NO_CANDIDATE_IN_WINDOW'
            elif not rows.coverage_known.any():reason='NO_KNOWN_LABEL_NEIGHBORHOOD'
            else:reason='NO_VALID_POST_PATH_AMONG_KNOWN_CANDIDATES'
            reasons[reason]=reasons.get(reason,0)+1
        results[scope]=dict(candidate_rows=int(g[scope].sum()),window_pairs=len(supported),valid_edges=len(subset),reachable_processes=len(reachable),
            max_flow=int(value),min_cut=int(cut),recall_upper=value/len(p),weekly_capacity_loss=len(reachable)-value,
            process_reasons=reasons,below_registered_recall_target=value/len(p)<rules['timely_process_recall_target'])
    # Any actual success must be feasible in its corresponding relaxation.
    sources=[('r01','positive20',EP/'outputs/r01/evaluated_new_observations.parquet')]
    sources += [(group+'_'+arm,group+'_tickets',EP/'outputs'/group/(arm+'_evaluated.parquet')) for group in ['r02','r03','r04'] for arm in ['A','B']]
    actualchecks={}
    for name,scope,file in sources:
        f=pd.read_parquet(file);f=f[f.recall_credit];validset=set(zip(edge.loc[edge[scope],'candidate_id'],edge.loc[edge[scope],'process_id']))
        pairs={(r.era+'|'+r.industry_code+'|'+r.date.strftime('%Y-%m-%d'),r.process_id) for r in f.itertuples()}
        assert pairs<=validset,(name,pairs-validset);actualchecks[name]=len(pairs)
    pd.DataFrame(flows).to_parquet(out/'oracle_allocations.parquet',index=False)
    files=[pfile,rawfile,gridfile,*supportfiles,EP/'rounds/D01_capacity_upper_bound_plan.md',Path(__file__),EP/'src/post_alert_evaluation.py',EP/'configs/evaluation_registration.json']+[x[2] for x in sources]
    result=dict(scope='Retrospective relaxed upper bound; NOT achievable performance or a signal',known_process_denominator=len(p),target_processes=math.ceil(len(p)*rules['timely_process_recall_target']),
        excluded_processes=len(allp)-len(p),results=results,actual_success_edges_checked=actualchecks,inputs={str(f):sha(f) for f in files})
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},ensure_ascii=False))


if __name__=='__main__':main()
