"""Independent raw mapping and interval audit."""
import re
import pandas as pd
from common import *
def run():
    out=ROOT/'outputs/r126';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    occurrences=json.loads((ROOT/'outputs/r125/occurrences.json').read_text());levels=json.loads((ROOT/'outputs/r125/share_levels.json').read_text())
    mappings=json.loads((out/'mapping_evidence.json').read_text());intervals=json.loads((out/'intervals.json').read_text())
    fields=['board_code','board_kind','board_name','industry_code','industry_name','index_code','index_name','index_weight_as_of','mapping_precision','mapping_source','exposure_ratio','cache_refs','status','origin_date','selection_rank','list_date']
    assert [m['occurrence_id'] for m in mappings]==[i for i,x in enumerate(occurrences) if x['eligible_share_level']]
    for m in mappings:
        x=occurrences[m['occurrence_id']]
        for k in ['source_path','source_sha256','json_pointer','ts_code']:assert m[k]==x[k]
        assert m['share_date']==x['fund_share_as_of']
        text=Path(m['source_path']).read_text();match=re.search(r'<!-- LONG_OPPORTUNITY_STATE_BEGIN(?: -->)?\s*(\{.*\})\s*(?:<!-- )?LONG_OPPORTUNITY_STATE_END -->\s*$',text,re.S);obj=json.loads(match.group(1))
        for part in m['json_pointer'].split('/')[1:]:obj=obj[int(part)] if isinstance(obj,list) else obj[part.replace('~1','/').replace('~0','~')]
        assert m['raw']=={k:obj.get(k) for k in fields}
    cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values()
    expected=[];coverage=[]
    for code in sorted({x['ts_code'] for x in levels}):
        g=sorted([x for x in levels if x['ts_code']==code],key=lambda x:x['share_date'])
        coverage.append(dict(ts_code=code,observations=len(g),first=g[0]['share_date'],last=g[-1]['share_date']))
        for before,after in zip(g,g[1:]):
            start,end=pd.Timestamp(before['share_date']),pd.Timestamp(after['share_date']);gap=int(((cal>start)&(cal<=end)).sum()) if start in cal and end in cal else None
            signatures=[]
            for x in [before,after]:signatures.append([list(t) for t in sorted({(m['raw']['index_code'],m['raw']['industry_code']) for m in mappings if m['ts_code']==code and m['share_date']==x['share_date']},key=repr)])
            valid=before['status']==after['status']=='unique_value'
            expected.append(dict(ts_code=code,start=before['share_date'],end=after['share_date'],calendar_days=(end-start).days,trading_sessions=gap,missing_intermediate_sessions=gap-1 if gap is not None else None,adjacent_session=gap==1,start_shares=before['shares'],end_shares=after['shares'],level_difference=after['shares']-before['shares'] if valid else None,relative_level_difference=after['shares']/before['shares']-1 if valid else None,start_mapping_signatures=signatures[0],end_mapping_signatures=signatures[1],mapping_labels_same=len(signatures[0])==len(signatures[1])==1 and signatures[0]==signatures[1],flow_eligible=False,reason='split_merge_and_full_universe_unverified; reported levels only'))
    assert intervals==expected and coverage==json.loads((out/'code_coverage.json').read_text())
    summary=json.loads((out/'summary.json').read_text())
    counts=dict(observations=len(levels),codes=len(coverage),intervals=len(intervals),adjacent_session_intervals=sum(x['adjacent_session'] for x in intervals),gapped_intervals=sum(x['trading_sessions'] is not None and x['trading_sessions']>1 for x in intervals),calendar_unknown_intervals=sum(x['trading_sessions'] is None for x in intervals),same_mapping_label_intervals=sum(x['mapping_labels_same'] for x in intervals),mapping_occurrences=len(mappings),missing_index_occurrences=sum(x['raw']['index_code'] is None for x in mappings),raw_index_codes=sorted({x['raw']['index_code'] for x in mappings if x['raw']['index_code'] is not None}),raw_industry_codes=sorted({x['raw']['industry_code'] for x in mappings if x['raw']['industry_code'] is not None}))
    for k,v in counts.items():assert summary[k]==v
    assert not any(summary[k] for k in ['flow_eligible_intervals','sw_mapping_certified','full_universe','strict_PIT'])
    assert summary['decision']=='stop_sparse_source_prediction_branch_pending_new_data'
    gap=json.loads((out/'data_gap.json').read_text());assert gap['status']=='required_not_collected' and len(gap['needed'])==6
    js(out/'verification.json',dict(status='PASS',observations=len(levels),intervals=len(intervals),mapping_occurrences=len(mappings),adjacent_session_intervals=counts['adjacent_session_intervals'],flow_eligible=0,sw_mapping_certified=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
