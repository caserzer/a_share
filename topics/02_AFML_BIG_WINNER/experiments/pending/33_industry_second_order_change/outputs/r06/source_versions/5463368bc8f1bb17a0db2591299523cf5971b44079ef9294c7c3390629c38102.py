"""Outcome-free case sampling and prefix-only append-only descriptive replay."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

EP=Path(__file__).resolve().parents[1]
SOURCE=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5')
OUT=EP/'outputs/r06'
KEY=['era','industry_code','block']


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def clean(v):
    if isinstance(v,(pd.Timestamp,np.datetime64)):return str(pd.Timestamp(v).date())
    if isinstance(v,(np.integer,)):return int(v)
    if isinstance(v,(np.floating,float)):return None if not np.isfinite(v) else float(v)
    if pd.isna(v):return None
    return v


def load():
    d=pd.read_parquet(SOURCE/'daily_industries.parquet')
    d=d[d.level.eq('L3')].sort_values(['era','industry_code','date'])
    market=pd.read_parquet(SOURCE/'CSI_ALL.parquet').close.sort_index()
    s=pd.Series(market.index,index=market.index)
    weeks=s.groupby(s.index.to_period('W-FRI')).max()
    weeks=weeks[[p.end_time.normalize()<=market.index.max() for p in weeks.index]]
    return d,market,pd.DatetimeIndex(weeks)


def describe_features(g,market):
    g=g.sort_values('date').copy()
    assert g.day_i.diff().dropna().eq(1).all()
    g['x']=np.log(g.nav.to_numpy()/market.reindex(g.date).to_numpy())
    for w in [5,20,60]:g[f'rate{w}']=(g.x-g.x.shift(w))*5/w
    g['rate_change']=g.rate20-g.rate20.shift(5)
    g['new_low']=g.x.lt(g.x.shift(1).rolling(20,min_periods=20).min()).where(g.x.shift(20).notna())
    g['new_low_count10']=g.new_low.rolling(10,min_periods=10).sum()
    for w in [5,20]:g[f'breadth_change{w}']=g.breadth21-g.breadth21.shift(w)
    g['vol60']=g.x.diff().rolling(60,min_periods=60).std()
    return g


def sample():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'sample_registry.csv').exists():raise RuntimeError('Sample exists; do not resample after observations')
    d,market,weeks=load()
    catalog_path=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_all_industry_review/outputs/industry_coverage.csv'
    cat=pd.read_csv(catalog_path);cat=cat[cat.level.eq('L3')]
    registry=[];selected=[]
    grouped={(era,code):g for (era,code),g in d.groupby(['era','industry_code'],sort=False)}
    for year in range(2021,2026):
        for half,month in [(1,1),(2,7)]:
            begin=pd.Timestamp(year,month,1);end=begin+pd.DateOffset(months=6)-pd.Timedelta(days=1)
            entry=weeks[(weeks>=begin)&(weeks<=end)][0];era='SW2014' if year==2021 else 'SW2021'
            period=f'{year}H{half}';rows=[]
            for _,c in cat[cat.era.eq(era)].iterrows():
                series=grouped.get((era,c.industry_code),d.iloc[:0])
                hist=series[series.date.le(entry)]
                row=dict(period=period,era=era,industry_code=c.industry_code,industry_name=c.industry_name,entry=str(entry.date()),end=str(end.date()))
                key=f'EP33-onset-r06|{period}|{era}|{c.industry_code}'
                row['sample_hash']=hashlib.sha256(key.encode()).hexdigest()
                if hist.empty or hist.date.iloc[-1]!=entry:
                    row.update(status='NO_ENTRY_DATA',history_sessions=0,coverage=None)
                else:
                    last=hist.iloc[-1];n=int(hist.block.eq(last.block).sum())
                    status='READY' if n>=64 and last.coverage>=.8 and last.members>=5 else 'INSUFFICIENT_AT_ENTRY'
                    row.update(status=status,history_sessions=n,coverage=clean(last.coverage))
                rows.append(row)
            available=sorted([r for r in rows if r['status']!='NO_ENTRY_DATA'],key=lambda r:r['sample_hash'])
            ready=[r for r in available if r['status']=='READY']
            first=(ready or available)[0] if available else None
            second_pool=[r for r in available if r!=first and r['status']!='READY'] or [r for r in available if r!=first]
            chosen=([first] if first else [])+(second_pool[:1])
            ids={r['industry_code'] for r in chosen}
            for r in rows:r['selected']=r['industry_code'] in ids
            registry+=rows
            for i,r in enumerate(chosen):
                selected.append(r|{'case_id':f'{period}_{i+1}_{r["industry_code"]}','deep_read':half==1 and i==0})
    pd.DataFrame(registry).to_csv(OUT/'sample_registry.csv',index=False)
    pd.DataFrame(selected).to_csv(OUT/'cases.csv',index=False)
    inputs=[SOURCE/'daily_industries.parquet',SOURCE/'CSI_ALL.parquet',catalog_path,EP/'rounds/r06_sampling_contract.md']
    receipt={'selection':'entry-prefix and deterministic hash only','inputs':{str(p):sha(p) for p in inputs},'cases_sha256':sha(OUT/'cases.csv'),'registry_sha256':sha(OUT/'sample_registry.csv')}
    (OUT/'sampling_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(pd.DataFrame(selected)[['case_id','industry_name','status','history_sessions','deep_read']].to_string(index=False))


def observation(hist,market,date):
    if hist.empty or hist.date.iloc[-1]!=date:return {'data_status':'MISSING','hypothesis':'本周路径缺失，不能判断变化；不填零或补写状态。','next_check':'等待可用路径，检查是否发生断块。'}
    last=hist.iloc[-1];block=hist[hist.block.eq(last.block)]
    f=describe_features(block,market.loc[:date]);r=f.iloc[-1]
    fields=['rate5','rate20','rate60','rate_change','new_low_count10','breadth21','breadth_change5','breadth_change20','volume_ratio','coverage','members','day_i','block','x']
    result={k:clean(r[k]) for k in fields};result['history_sessions']=len(block)
    result['data_status']='OBSERVABLE' if len(block)>=64 and r.coverage>=.8 else 'PARTIAL'
    if pd.isna(r.rate20) or pd.isna(r.rate_change):
        hyp='连续历史不足，暂不命名趋势或二阶变化。'
    elif r.rate20<0 and r.rate_change>0:
        hyp='中期仍弱但恶化速度在收窄；可疑减速，尚不能认定转向。'
    elif r.rate20>=0 and r.rate_change>0:
        hyp='中期改善速度增加；需区分变化刚发生与既有趋势延续。'
    elif r.rate20>=0:
        hyp='中期仍改善但速度回落；不因当前仍强就忽略减速。'
    else:hyp='中期恶化未见速度改善；不制造起点信号。'
    result['hypothesis']=hyp
    result['competing_explanation']='单周波动、市场风格共振或成员/覆盖变化；价格迹象不等于盈利机制。'
    result['next_check']='下一段是否减少相对新低、短中期方向趋同，以及宽度变化能否延续；相反发展则撤回或修正当前解释。'
    return result


def advance(n):
    d,market,weeks=load();cases=pd.read_csv(OUT/'cases.csv');receipt=json.loads((OUT/'sampling_receipt.json').read_text())
    assert sha(OUT/'cases.csv')==receipt['cases_sha256']
    finance=pd.read_csv(EP/'outputs/r04/industry_coverage.csv.gz',parse_dates=['date'])
    displays=[]
    grouped={(era,code):g for (era,code),g in d.groupby(['era','industry_code'],sort=False)}
    for _,case in cases.iterrows():
        dates=weeks[(weeks>=pd.Timestamp(case.entry))&(weeks<=pd.Timestamp(case.end))]
        path=OUT/'replay'/f'{case.case_id}.jsonl';path.parent.mkdir(exist_ok=True)
        prior=[json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
        prev='GENESIS'
        for r in prior:
            h=r['record_hash'];b={k:v for k,v in r.items() if k!='record_hash'}
            assert b['previous_hash']==prev and hashlib.sha256(stable(b).encode()).hexdigest()==h
            prev=h
        for i in range(len(prior),min(n,len(dates))):
            date=dates[i]
            series=grouped.get((case.era,case.industry_code),d.iloc[:0])
            hist=series[series.date.le(date)]
            obs=observation(hist,market,date)
            fin=finance[(finance.date==date)&(finance.era==case.era)&(finance.industry_code==case.industry_code)]
            for col in ['finance_coverage','growth','finance_acceleration']:
                obs[col]=clean(fin.iloc[0][col]) if len(fin) else None
            body={'case_id':case.case_id,'industry_name':case.industry_name,'step':i+1,'asof':str(date.date()),'previous_hash':prev,**obs}
            body['record_hash']=hashlib.sha256(stable(body).encode()).hexdigest()
            with path.open('a') as f:f.write(stable(body)+'\n')
            prev=body['record_hash'];prior.append(body)
        if bool(case.deep_read):
            for r in prior[max(0,min(n,len(prior))-4):min(n,len(prior))]:
                displays.append({k:r.get(k) for k in ['case_id','industry_name','asof','rate5','rate20','rate60','rate_change','new_low_count10','breadth21','breadth_change5','volume_ratio','finance_coverage','finance_acceleration','data_status']})
    (OUT/f'checkpoint_{n:02d}.json').write_text(json.dumps({'through_step':n,'cases_hash':sha(OUT/'cases.csv'),'ledger_hashes':{p.name:sha(p) for p in sorted((OUT/'replay').glob('*.jsonl'))},'script_hash':sha(__file__)},indent=2)+'\n')
    print(pd.DataFrame(displays).round(4).to_string(index=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--sample',action='store_true');ap.add_argument('--advance',type=int);a=ap.parse_args()
    if a.sample:sample()
    if a.advance:advance(a.advance)
