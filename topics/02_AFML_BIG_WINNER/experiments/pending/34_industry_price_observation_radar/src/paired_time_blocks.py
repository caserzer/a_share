"""Resample identical time blocks for both arms; retain zero-observation weeks."""
import numpy as np


def paired_interval(era_counts,block_weeks=13,repetitions=2000,seed=3404,confidence=.90):
    arrays=[np.asarray(x,dtype=float) for x in era_counts if len(x)]
    for a in arrays:
        if a.ndim!=2 or a.shape[1]!=8 or not np.isfinite(a).all() or (a<0).any():raise ValueError('invalid counts')
        for j in [0,2,4,6]:
            if (a[:,j]>a[:,j+1]).any():raise ValueError('numerator exceeds denominator')
    if block_weeks<1 or repetitions<1 or not 0<confidence<1:raise ValueError('invalid bootstrap settings')
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(repetitions):
        total=np.zeros(8)
        for a in arrays:
            n=len(a);length=min(block_weeks,n)
            starts=rng.integers(0,n-length+1,size=int(np.ceil(n/length)))
            idx=np.concatenate([np.arange(s,s+length) for s in starts])[:n]
            total+=a[idx].sum(axis=0)
        rates=[np.nan if total[j+1]==0 else total[j]/total[j+1] for j in [0,2,4,6]]
        samples.append(rates+[rates[2]-rates[0],rates[3]-rates[1]])
    v=np.asarray(samples);alpha=(1-confidence)/2;result={}
    for j,name in enumerate(['A_precision','A_recall','B_precision','B_recall','B_minus_A_precision','B_minus_A_recall']):
        finite=v[np.isfinite(v[:,j]),j]
        result[name]=dict(interval=None if not len(finite) else np.quantile(finite,[alpha,1-alpha]).tolist(),defined_replicates=len(finite),undefined_replicates=repetitions-len(finite))
    return result
