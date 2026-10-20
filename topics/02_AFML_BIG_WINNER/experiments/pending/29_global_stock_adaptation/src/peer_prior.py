"""Outcome-blind peer membership and conservative month-clustered prior correction."""
from common import *
from issuer_adaptation import offset_map


def peer_sets(current):
    f=current.reset_index(drop=True).copy();cols=C['peer']['features'];x=f[cols].to_numpy(float)
    med=np.nanmedian(x,axis=0);scale=np.nanquantile(x,.75,axis=0)-np.nanquantile(x,.25,axis=0)
    scale=np.where(np.isfinite(scale)&(scale>0),scale,1.)
    z=np.clip((x-med)/scale,-C['peer']['maximum_standardized_value'],C['peer']['maximum_standardized_value'])
    complete=np.isfinite(z).all(axis=1);valid=f.industry_stale.eq(0).to_numpy()&f.industry_id.ne('UNKNOWN').to_numpy()
    answer={}
    for i,row in f.iterrows():
        if not valid[i] or not complete[i]:
            answer[row.instrument]=dict(peers=[],distances=[],route='global_stale_unknown_or_missing_features');continue
        mask=valid&complete&f.industry_id.eq(row.industry_id).to_numpy();mask[i]=False;route='industry'
        k=C['peer']['neighbors'];minimum=C['peer']['minimum_neighbors']
        if mask.sum()<minimum:
            mask=valid&complete&f.industry_sector.eq(row.industry_sector).to_numpy();mask[i]=False
            route='sector';k=C['peer']['sector_neighbors'];minimum=C['peer']['sector_minimum_neighbors']
        if mask.sum()<minimum:
            answer[row.instrument]=dict(peers=[],distances=[],route='global_insufficient_peers');continue
        ix=np.flatnonzero(mask);dist=np.sqrt(np.mean((z[ix]-z[i])**2,axis=1))
        order=np.lexsort(([tie(s) for s in f.iloc[ix].instrument],dist))[:k]
        answer[row.instrument]=dict(peers=f.iloc[ix[order]].instrument.tolist(),distances=dist[order].tolist(),route=route)
    return answer


def peer_fit(row,membership,history):
    base=dict(a=0.,posterior_sd=np.nan,shrinkage=0.,history_rows=0,history_months=0,history_peers=0,effective_months=0.)
    if not membership['peers']:return dict(**base,reason=membership['route'])
    z=history[history.instrument.isin(membership['peers'])&history.industry_stale.eq(0)]
    field='industry_id' if membership['route']=='industry' else 'industry_sector'
    z=z[z[field].eq(row[field])]
    base.update(history_rows=len(z),history_months=z.date.nunique(),history_peers=z.instrument.nunique(),effective_months=z.date.nunique()/C['overlap_discount'])
    if base['history_months']<C['peer']['minimum_history_months'] or base['history_peers']<C['peer']['minimum_historical_peers']:
        return dict(**base,reason='insufficient_mature_peer_history')
    w=1/(z.groupby('date').date.transform('size').to_numpy()*C['overlap_discount'])
    fit=offset_map(z.offset_G,z.event,w,C['peer']['prior_sd'],C['peer']['maximum_logit_shift'])
    base.update(a=fit['estimate'],posterior_sd=fit['sd'],shrinkage=fit['shrinkage'])
    return dict(**base,reason='adapted_'+membership['route'])
