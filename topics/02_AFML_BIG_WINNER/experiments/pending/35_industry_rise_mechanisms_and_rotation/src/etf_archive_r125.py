"""Inspect retained formal embedded states without calling production collectors."""
import math,re
from datetime import datetime
from common import *
BASE=Path('/home/xiaolv/code/golden_loop_artifacts/a_share_market_radar/reports/long_opportunities/2026')
CODE=Path('/home/xiaolv/code/golden_loop/a_share_market_radar/production')
def parse_state(text):
    begin='<!-- LONG_OPPORTUNITY_STATE_BEGIN'
    if text.count(begin)!=1:raise ValueError('missing_or_multiple_state_markers')
    tail=text.split(begin,1)[1].lstrip();legacy=tail.startswith('-->')
    if legacy:tail=tail[3:].lstrip()
    obj,n=json.JSONDecoder().raw_decode(tail)
    end='<!-- LONG_OPPORTUNITY_STATE_END -->' if legacy else 'LONG_OPPORTUNITY_STATE_END -->'
    if tail[n:].strip()!=end:raise ValueError('unexpected_state_suffix')
    if not isinstance(obj,dict):raise ValueError('state_not_object')
    return obj
def walk(obj,path=''):
    if isinstance(obj,dict):
        if 'fund_share_units' in obj:yield path,obj
        for k,v in obj.items():yield from walk(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):yield from walk(v,path+'/'+str(i))
def date_ok(x):
    if not isinstance(x,str) or not re.fullmatch(r'\d{8}',x):return False
    try:datetime.strptime(x,'%Y%m%d');return True
    except ValueError:return False
def run():
    out=ROOT/'outputs/r125';out.mkdir(exist_ok=True);files=[];occ=[]
    for p in sorted(BASE.glob('*.md')):
        rec=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
        try:s=parse_state(p.read_text());rec.update(status='parsed',target_date=s.get('target_date'),format_version=s.get('format_version'),test_only=s.get('test_only'),occurrences=0)
        except (ValueError,json.JSONDecodeError) as e:rec.update(status='parse_error',reason=str(e));files.append(rec);continue
        for pointer,row in walk(s):
            x={k:row.get(k) for k in ['instrument_code','ts_code','instrument_type','fund_share_units','fund_share_as_of']}
            x.update(source_path=str(p),source_sha256=rec['sha256'],json_pointer=pointer,target_date=s.get('target_date'),test_only=s.get('test_only'))
            v=x['fund_share_units'];finite=isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) and v>0
            code=isinstance(x['ts_code'],str) and re.fullmatch(r'\d{6}\.(SH|SZ)',x['ts_code']) is not None
            eligible=finite and code and x['instrument_type']=='ETF' and x['test_only'] is False and date_ok(x['target_date']) and date_ok(x['fund_share_as_of']) and x['fund_share_as_of']<=x['target_date']
            x['eligible_share_level']=eligible;x['same_report_date']=date_ok(x['fund_share_as_of']) and x['fund_share_as_of']==x['target_date'];occ.append(x);rec['occurrences']+=1
        files.append(rec)
    groups={}
    for i,x in enumerate(occ):
        if x['eligible_share_level']:groups.setdefault((x['ts_code'],x['fund_share_as_of']),[]).append(i)
    normalized=[]
    for (code,date),ids in sorted(groups.items()):
        vals=sorted(set(occ[i]['fund_share_units'] for i in ids))
        normalized.append(dict(ts_code=code,share_date=date,occurrence_ids=ids,unique_values=vals,status='unique_value' if len(vals)==1 else 'conflict',shares=vals[0] if len(vals)==1 else None,report_dates=sorted(set(occ[i]['target_date'] for i in ids))))
    runtime=[Path('/home/xiaolv/.openclaw/a-share-market-radar-runtime'),Path('/Users/xiaolv/.openclaw/a-share-market-radar-runtime')]
    codefiles=[CODE/n for n in ['daily_openclaw_market_radar.py','long_opportunity_report_v2.py','long_opportunity_mapping_cache.py']]
    summary=dict(files=len(files),parsed=sum(x['status']=='parsed' for x in files),parse_errors=sum(x['status']!='parsed' for x in files),occurrences=len(occ),eligible_occurrences=sum(x['eligible_share_level'] for x in occ),unique_code_dates=len(normalized),conflict_groups=sum(x['status']=='conflict' for x in normalized),securities=len({x['ts_code'] for x in normalized}),share_dates=sorted({x['share_date'] for x in normalized}),report_dates=sorted({x['target_date'] for x in files if x['status']=='parsed' and date_ok(x['target_date'])}),stale_eligible_occurrences=sum(x['eligible_share_level'] and not x['same_report_date'] for x in occ),runtime_roots=[dict(path=str(p),exists=p.exists()) for p in runtime],source_scope='selected formal report records, not full-universe historical flow',strict_PIT=False,next='If repeated exact-date ETF levels survive, audit sparse date spacing and selection/mapping limitations before any flow calculation; otherwise keep gap and move to another grounded mechanism.')
    js(out/'file_ledger.json',files);js(out/'occurrences.json',occ);js(out/'share_levels.json',normalized);js(out/'summary.json',summary)
    reads=codefiles+[Path(__file__),ROOT/'protocols/r125.json']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in reads},report_sources={x['path']:x['sha256'] for x in files},outputs={n:sha(out/n) for n in ['file_ledger.json','occurrences.json','share_levels.json','summary.json']},source_directory=str(BASE)))
    print(summary)
if __name__=='__main__':run()
