"""Independent embedded JSON, pointer, eligibility and duplicate reconstruction."""
import math,re
from datetime import datetime
from common import *
def run():
    out=ROOT/'outputs/r125';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['report_sources'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    files=json.loads((out/'file_ledger.json').read_text());occ=json.loads((out/'occurrences.json').read_text());levels=json.loads((out/'share_levels.json').read_text());summary=json.loads((out/'summary.json').read_text())
    assert sorted(receipt['report_sources'])==[str(p) for p in sorted(Path(receipt['source_directory']).glob('*.md'))]
    extracted={};states={}
    for f in files:
        path=Path(f['path']);assert f['bytes']==path.stat().st_size and f['sha256']==sha(path)
        text=path.read_text()
        match=re.search(r'<!-- LONG_OPPORTUNITY_STATE_BEGIN(?: -->)?\s*(\{.*\})\s*(?:<!-- )?LONG_OPPORTUNITY_STATE_END -->\s*$',text,re.S)
        assert text.count('<!-- LONG_OPPORTUNITY_STATE_BEGIN')==1 and match is not None
        s=json.loads(match.group(1));states[str(path)]=s;assert f['status']=='parsed' and f['target_date']==s.get('target_date') and f['format_version']==s.get('format_version') and f['test_only']==s.get('test_only')
        stack=[('',s)];count=0
        while stack:
            pointer,x=stack.pop()
            if isinstance(x,dict):
                if 'fund_share_units' in x:extracted[(str(path),pointer)]=x;count+=1
                stack.extend((pointer+'/'+str(k).replace('~','~0').replace('/','~1'),v) for k,v in x.items())
            elif isinstance(x,list):stack.extend((pointer+'/'+str(i),v) for i,v in enumerate(x))
        assert f['occurrences']==count
    assert len(occ)==len(extracted) and len({(x['source_path'],x['json_pointer']) for x in occ})==len(occ)
    grouped={}
    for i,x in enumerate(occ):
        row=extracted[(x['source_path'],x['json_pointer'])];state=states[x['source_path']]
        for c in ['instrument_code','ts_code','instrument_type','fund_share_units','fund_share_as_of']:assert x[c]==row.get(c)
        assert x['target_date']==state.get('target_date') and x['test_only']==state.get('test_only') and x['source_sha256']==receipt['report_sources'][x['source_path']]
        v=x['fund_share_units'];valid=type(v) in [int,float] and math.isfinite(v) and v>0 and x['instrument_type']=='ETF' and x['test_only'] is False and isinstance(x['ts_code'],str) and bool(re.fullmatch(r'\d{6}\.(SH|SZ)',x['ts_code']))
        dates={}
        for c in ['target_date','fund_share_as_of']:
            try:
                d=datetime.strptime(str(x[c]),'%Y%m%d');dates[c]=d if isinstance(x[c],str) and d.strftime('%Y%m%d')==x[c] else None
            except ValueError:dates[c]=None
        eligible=bool(valid and all(dates.values()) and dates['fund_share_as_of']<=dates['target_date'])
        assert x['eligible_share_level']==eligible and x['same_report_date']==bool(dates['fund_share_as_of'] and x['fund_share_as_of']==x['target_date'])
        if eligible:grouped.setdefault((x['ts_code'],x['fund_share_as_of']),[]).append(i)
    rebuilt=[]
    for (code,date),ids in sorted(grouped.items()):
        values=sorted({occ[i]['fund_share_units'] for i in ids})
        rebuilt.append(dict(ts_code=code,share_date=date,occurrence_ids=ids,unique_values=values,status='unique_value' if len(values)==1 else 'conflict',shares=values[0] if len(values)==1 else None,report_dates=sorted({occ[i]['target_date'] for i in ids})))
    assert rebuilt==levels
    counts=dict(files=len(files),parsed=len(states),parse_errors=0,occurrences=len(occ),eligible_occurrences=sum(len(v) for v in grouped.values()),unique_code_dates=len(levels),conflict_groups=sum(x['status']=='conflict' for x in levels),securities=len({x['ts_code'] for x in levels}),share_dates=sorted({x['share_date'] for x in levels}),report_dates=sorted({s['target_date'] for s in states.values()}),stale_eligible_occurrences=sum(x['eligible_share_level'] and not x['same_report_date'] for x in occ))
    for k,v in counts.items():assert summary[k]==v,(k,summary[k],v)
    for x in summary['runtime_roots']:assert x['exists']==Path(x['path']).exists()
    js(out/'verification.json',dict(status='PASS',files=len(files),occurrences=len(occ),eligible_occurrences=counts['eligible_occurrences'],unique_code_dates=len(levels),securities=counts['securities'],conflicts=counts['conflict_groups'],full_universe=False,strict_PIT=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
