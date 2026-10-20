"""Within-industry/risk-cell identification and immutable matched pairs, never outcome-selected."""
from core import *


def conditional_auc(frame,prob='probability',group='industry_id'):
    records=[];numerator=denominator=0.;used=0;eligible_groups=0
    known=frame[frame.actual.notna()]
    for name,g in frame.groupby(group,sort=True):
        z=g[g.actual.notna()];y=labels(z.actual);events=int(np.nansum(y));neg=len(z)-events;reason='eligible'
        if name=='UNKNOWN' or str(name).startswith('UNKNOWN:'):reason='unknown_industry'
        elif len(z)<C['within_group']['minimum_rows']:reason='too_few_rows'
        elif events<C['within_group']['minimum_positive']:reason='too_few_events'
        elif neg<C['within_group']['minimum_negative']:reason='too_few_non_events'
        auc=np.nan
        if reason=='eligible':
            auc=float(roc_auc_score(y,z[prob]));pairs=events*neg;numerator+=auc*pairs;denominator+=pairs;used+=len(z);eligible_groups+=1
        records.append(dict(group=str(name),predicted=len(g),known=len(z),events=events,non_events=neg,status=reason,auc=auc))
    return dict(conditional_auc=numerator/denominator if denominator else np.nan,groups=len(records),eligible_groups=eligible_groups,
        scored_rows=used,known_rows=len(known),coverage=used/len(known) if len(known) else 0.,positive_negative_pairs=denominator),records


def make_pairs(frame):
    f=frame.copy().reset_index(drop=True);eps=1e-8
    f['incremental_score']=np.log(np.clip(f.p_full,eps,1-eps)/(1-np.clip(f.p_full,eps,1-eps)))-np.log(np.clip(f.p_base,eps,1-eps)/(1-np.clip(f.p_base,eps,1-eps)))
    candidates=[]
    for (industry,board),g in f.groupby(['industry_id','board'],sort=True):
        if industry=='UNKNOWN' or len(g)<C['matching']['minimum_industry_rows']:continue
        order=np.lexsort((tie(g.instrument),g.incremental_score));count=max(1,int(np.ceil(len(g)*C['matching']['fraction'])))
        low=g.iloc[order[:count]];high=g.iloc[order[-count:]]
        for a in high.itertuples():
            for b in low.itertuples():
                if a.vol63<=0 or b.vol63<=0:continue
                dc=abs(a.log_cap-b.log_cap);dv=abs(np.log(a.vol63/b.vol63))
                if dc<=C['matching']['maximum_log_cap_difference'] and dv<=C['matching']['maximum_log_vol_difference'] and a.incremental_score>b.incremental_score:
                    candidates.append(dict(high=a.instrument,low=b.instrument,industry_id=industry,board=board,log_cap_gap=dc,log_vol_gap=dv,
                        distance=dc/C['matching']['maximum_log_cap_difference']+dv/C['matching']['maximum_log_vol_difference'],incremental_score_gap=a.incremental_score-b.incremental_score))
    candidates.sort(key=lambda r:(r['distance'],hashlib.sha256((r['high']+':'+r['low']).encode()).hexdigest()))
    used=set();pairs=[]
    for row in candidates:
        if row['high'] in used or row['low'] in used:continue
        pairs.append(row);used.update([row['high'],row['low']])
        if len(pairs)>=C['matching']['target_pairs_per_month']:break
    return pd.DataFrame(pairs,columns=['high','low','industry_id','board','log_cap_gap','log_vol_gap','distance','incremental_score_gap'])


def error_decomposition(frame,prob='probability'):
    allrows=risk_cells(frame);g=allrows[allrows.actual.notna()].copy();e=g[prob].to_numpy()-labels(g.actual);g['error']=e
    m=float(e.mean());industry=g.groupby('industry_id').error.transform('mean');cell=g.groupby('risk_cell').error.transform('mean')
    components=dict(common_error=m*m,industry_error=float(np.mean((industry-m)**2)),risk_cell_error=float(np.mean((cell-industry)**2)),individual_error=float(np.mean((g.error-cell)**2)),total=float(np.mean(e*e)))
    assert np.isclose(sum(components[k] for k in ['common_error','industry_error','risk_cell_error','individual_error']),components['total'],atol=1e-12)
    return components
