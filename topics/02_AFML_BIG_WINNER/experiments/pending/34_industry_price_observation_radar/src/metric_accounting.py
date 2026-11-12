"""Denominator accounting independent of candidate selection and signal scores."""
from collections import Counter,defaultdict
import numpy as np


def ratio(a,b):return None if b==0 else a/b


def summarize(processes,results):
    processes=list(processes);results=list(results)
    registry={p['process_id']:p for p in processes}
    if len(registry)!=len(processes):raise ValueError('duplicate process')
    allowed={'SUCCESS','FIRST_FAILURE','UNMATCHED_FAILURE','DUPLICATE','UNKNOWN','UNKNOWN_DUPLICATE','IMMATURE','IMMATURE_DUPLICATE','UPDATE'}
    new=[r for r in results if r['outcome']!='UPDATE']
    if len({r['alert_id'] for r in new})!=len(new):raise ValueError('duplicate new alert')
    credited=set()
    for r in results:
        state=r['outcome'];pid=r['process_id']
        if state not in allowed:raise ValueError('invalid outcome')
        if pid is not None and pid not in registry:raise ValueError('unknown process identity')
        if bool(r['new_observation_denominator'])!=(state in {'SUCCESS','FIRST_FAILURE','UNMATCHED_FAILURE','DUPLICATE'}):
            raise ValueError('invalid precision denominator membership')
        if bool(r['recall_credit'])!=(state=='SUCCESS'):raise ValueError('invalid success credit')
        if state=='SUCCESS':
            if pid is None or pid in credited:raise ValueError('duplicate or missing successful process')
            if registry[pid]['left_origin_uncertain']:raise ValueError('uncertain origin credited as known success')
            credited.add(pid)
    eligible={k for k,p in registry.items() if p['mature'] and not p['left_origin_uncertain']}
    hit=credited&eligible
    unresolved={r['process_id'] for r in results if r['outcome']=='UNKNOWN' and r['process_id'] in eligible}-hit
    # A process cannot have conflicting first results, even if both are non-success.
    first=[r['process_id'] for r in results if r['process_id'] is not None and r['outcome'] in {'SUCCESS','FIRST_FAILURE','UNKNOWN','IMMATURE'}]
    if len(first)!=len(set(first)):raise ValueError('multiple first outcomes for process')
    counts=Counter(r['outcome'] for r in results)
    denom=sum(r['new_observation_denominator'] for r in results);success=counts['SUCCESS']
    unknown=counts['UNKNOWN']+counts['UNKNOWN_DUPLICATE'];immature=counts['IMMATURE']+counts['IMMATURE_DUPLICATE']
    assert denom+unknown+immature==len(new)
    families=defaultdict(lambda:dict(processes=0,successes=0,unresolved=0))
    for pid in eligible:
        f=families[registry[pid]['family_id']];f['processes']+=1;f['successes']+=pid in hit;f['unresolved']+=pid in unresolved
    family_hits=sum(f['successes']>0 for f in families.values())
    family_unknown=sum(f['successes']==0 and f['unresolved']>0 for f in families.values())
    return dict(unique_new_alerts=len(new),updates=counts['UPDATE'],outcomes=dict(counts),
                precision_numerator=success,precision_denominator=int(denom),precision=ratio(success,denom),
                unknown_alerts=unknown,immature_alerts=immature,
                precision_unknown_bounds=[ratio(success,denom+unknown),ratio(success+unknown,denom+unknown)],
                process_catalog=len(processes),mature_known_processes=len(eligible),
                mature_left_unknown=sum(p['mature'] and p['left_origin_uncertain'] for p in processes),
                immature_processes=sum(not p['mature'] for p in processes),
                recall_numerator=len(hit),recall_lower=ratio(len(hit),len(eligible)),
                recall_upper=ratio(len(hit|unresolved),len(eligible)),unresolved_processes=len(unresolved),
                known_not_recalled=len(eligible-hit-unresolved),
                family_denominator=len(families),family_numerator=family_hits,
                family_recall_lower=ratio(family_hits,len(families)),
                family_recall_upper=ratio(family_hits+family_unknown,len(families)),
                family_counts=dict(sorted(families.items())))


def time_block_interval(era_counts,block_weeks=13,repetitions=2000,seed=3404,confidence=.90):
    """Each Nx4 array is [precision successes, precision n, recall successes, recall n]."""
    arrays=[np.asarray(x,dtype=float) for x in era_counts if len(x)]
    for a in arrays:
        if a.ndim!=2 or a.shape[1]!=4 or not np.isfinite(a).all() or (a<0).any():raise ValueError('invalid weekly counts')
        if (a[:,0]>a[:,1]).any() or (a[:,2]>a[:,3]).any():raise ValueError('numerator exceeds denominator')
    if block_weeks<1 or repetitions<1 or not 0<confidence<1:raise ValueError('invalid bootstrap settings')
    rng=np.random.default_rng(seed);values=[]
    for _ in range(repetitions):
        total=np.zeros(4)
        for a in arrays:
            n=len(a);length=min(block_weeks,n)
            starts=rng.integers(0,n-length+1,size=int(np.ceil(n/length)))
            indices=np.concatenate([np.arange(s,s+length) for s in starts])[:n]
            total+=a[indices].sum(axis=0)
        values.append([np.nan if total[1]==0 else total[0]/total[1],np.nan if total[3]==0 else total[2]/total[3]])
    v=np.asarray(values);alpha=(1-confidence)/2;result={}
    for j,name in enumerate(['precision','recall']):
        finite=v[np.isfinite(v[:,j]),j]
        result[name]=dict(interval=None if not len(finite) else np.quantile(finite,[alpha,1-alpha]).tolist(),
                          defined_replicates=len(finite),undefined_replicates=repetitions-len(finite))
    return result
