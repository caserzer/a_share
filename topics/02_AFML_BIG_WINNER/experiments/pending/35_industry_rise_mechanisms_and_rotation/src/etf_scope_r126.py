"""Sparse selected ETF endpoint differences and raw mapping provenance."""
import pandas as pd
from common import *
from etf_archive_r125 import parse_state
FIELDS=['board_code','board_kind','board_name','industry_code','industry_name','index_code','index_name','index_weight_as_of','mapping_precision','mapping_source','exposure_ratio','cache_refs','status','origin_date','selection_rank','list_date']
def run():
    out=ROOT/'outputs/r126';out.mkdir(exist_ok=True)
    lp=ROOT/'outputs/r125/share_levels.json';op=ROOT/'outputs/r125/occurrences.json';cp=CACHE/'forecast_v5/CSI_ALL.parquet'
    levels=json.loads(lp.read_text());occ=json.loads(op.read_text());calendar=pd.DatetimeIndex(pd.read_parquet(cp).index).sort_values();assert calendar.is_unique
    sources={};mappings=[]
    for i,x in enumerate(occ):
        if not x['eligible_share_level']:continue
        path=Path(x['source_path'])
        if str(path) not in sources:sources[str(path)]=parse_state(path.read_text())
        obj=sources[str(path)]
        for part in x['json_pointer'].split('/')[1:]:obj=obj[int(part)] if isinstance(obj,list) else obj[part.replace('~1','/').replace('~0','~')]
        mappings.append(dict(occurrence_id=i,ts_code=x['ts_code'],share_date=x['fund_share_as_of'],source_path=x['source_path'],source_sha256=x['source_sha256'],json_pointer=x['json_pointer'],raw={k:obj.get(k) for k in FIELDS}))
    js(out/'mapping_evidence.json',mappings)
    by={}
    for x in levels:by.setdefault(x['ts_code'],[]).append(x)
    intervals=[];coverage=[]
    for code,group in sorted(by.items()):
        group=sorted(group,key=lambda x:x['share_date'])
        coverage.append(dict(ts_code=code,observations=len(group),first=group[0]['share_date'],last=group[-1]['share_date']))
        for prev,now in zip(group,group[1:]):
            start=pd.Timestamp(prev['share_date']);end=pd.Timestamp(now['share_date']);both=start in calendar and end in calendar
            gap=int(calendar.get_loc(end)-calendar.get_loc(start)) if both else None
            valid=prev['status']==now['status']=='unique_value'
            def signatures(x):
                return sorted({(m['raw']['index_code'],m['raw']['industry_code']) for m in mappings if m['ts_code']==code and m['share_date']==x['share_date']},key=repr)
            before,after=signatures(prev),signatures(now)
            intervals.append(dict(ts_code=code,start=prev['share_date'],end=now['share_date'],calendar_days=(end-start).days,trading_sessions=gap,missing_intermediate_sessions=gap-1 if both else None,adjacent_session=both and gap==1,start_shares=prev['shares'],end_shares=now['shares'],level_difference=now['shares']-prev['shares'] if valid else None,relative_level_difference=now['shares']/prev['shares']-1 if valid else None,start_mapping_signatures=before,end_mapping_signatures=after,mapping_labels_same=len(before)==len(after)==1 and before==after,flow_eligible=False,reason='split_merge_and_full_universe_unverified; reported levels only'))
    js(out/'intervals.json',intervals);js(out/'code_coverage.json',coverage)
    indices=sorted({x['raw']['index_code'] for x in mappings if x['raw']['index_code'] is not None});industries=sorted({x['raw']['industry_code'] for x in mappings if x['raw']['industry_code'] is not None})
    summary=dict(observations=len(levels),codes=len(by),intervals=len(intervals),adjacent_session_intervals=sum(x['adjacent_session'] for x in intervals),gapped_intervals=sum(x['trading_sessions'] is not None and x['trading_sessions']>1 for x in intervals),calendar_unknown_intervals=sum(x['trading_sessions'] is None for x in intervals),same_mapping_label_intervals=sum(x['mapping_labels_same'] for x in intervals),mapping_occurrences=len(mappings),missing_index_occurrences=sum(x['raw']['index_code'] is None for x in mappings),raw_index_codes=indices,raw_industry_codes=industries,flow_eligible_intervals=0,sw_mapping_certified=False,full_universe=False,strict_PIT=False,decision='stop_sparse_source_prediction_branch_pending_new_data')
    js(out/'summary.json',summary)
    js(out/'data_gap.json',dict(status='required_not_collected',scope='ETF/holdings mechanism only; not whole-goal blocked',needed=['continuous positive shares with units and missing/zero semantics','split/merge/corporate-action evidence before interpreting share changes','historical ETF existence including exited funds; point-in-time universe','official tracking-index history and dated constituents/weights for SW-era mapping','publication/acquisition timestamps and independent historical versions','matched price/market controls, mature outcomes, enough dates for fixed tests'],source_candidates=['retained original runtime/cache if made accessible','exchange/fund-company archives or explicitly authorized vendor datasets'],cost='not established; no purchase or API use authorized here',recovery='new verifiable local artifacts or explicit scoped external acquisition authorization; no lowered thresholds',next='Return to remaining overall requirements and grounded local comparisons; do not train on16selectedlevels'))
    reads=[lp,op,cp,Path(__file__),ROOT/'protocols/r126.json',ROOT/'src/etf_archive_r125.py']+[Path(p) for p in sources]
    names=['mapping_evidence.json','intervals.json','code_coverage.json','summary.json','data_gap.json']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in reads},outputs={n:sha(out/n) for n in names}));print(summary)
if __name__=='__main__':run()
