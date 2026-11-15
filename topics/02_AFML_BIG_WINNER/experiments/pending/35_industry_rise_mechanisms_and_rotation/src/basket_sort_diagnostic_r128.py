"""Single affected-industry sort-only diagnostic; not an adopted basket repair."""
import inspect
import pandas as pd
from common import *
import basket_replay_r128 as original

def run():
    out=ROOT/'outputs/r128';m=pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet')
    m=m[m.era.eq('SW2021')&m.level.eq('L2')&m.industry_code.eq('801011.SI')]
    audit=json.loads((EP32/'extensions/v5_rdagent_onset_forecast/outputs/daily_input_audit.json').read_text())
    paths={Path(p).stem:Path(p) for p in audit['reads'] if '/normalized/prices_qfq/' in p}
    stocks={s:pd.read_parquet(paths[s],columns=['date','qfq_close','close_conflict','factor_chain_id']) for s in m.security_id.unique()}
    days=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
    source=inspect.getsource(original.rebuild);needle=".sort_values('date').drop_duplicates('date')";assert source.count(needle)==1
    source=source.replace(needle,".sort_values('date',kind='stable').drop_duplicates('date')")
    sp=out/'stable_rebuild_source.txt';sp.write_text(source);scope=dict(vars(original));exec(compile(source,str(sp),'exec'),scope);stable=scope['rebuild']
    result=[]
    for name,fn in [('original_quicksort',original.rebuild),('stable_sort_only',stable)]:
        a=fn(m,stocks,days,'2026-09-30');b=fn(m,stocks,days,'2026-10-21');b=b[b.date.le('2026-09-30')]
        comparison,*_=original.compare(a,b);result.append(dict(method=name,comparison=comparison))
    js(out/'sort_diagnostic.json',dict(industry=['SW2021','L2','801011.SI'],selected_reason='first industry in actual identity discrepancy ledger, diagnostic not performance sample',source_sha256=sha(Path(original.__file__)),stable_source_sha256=sha(sp),results=result,adopted=False))
    print(result)

if __name__=='__main__':run()
