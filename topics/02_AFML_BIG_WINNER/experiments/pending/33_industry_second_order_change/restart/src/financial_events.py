import json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
CACHE=Path('/home/xiaolv/.cache/a_share/ep30_d2/proxy/financials')

def construct(raw,calendar):
    f=raw.copy()
    for c in ['REPORT_DATE','NOTICE_DATE','UPDATE_DATE']:f[c]=pd.to_datetime(f[c],errors='coerce')
    f['period']=f.REPORT_DATE.dt.to_period('Q');f['value']=pd.to_numeric(f.TOTALOPERATEREVE,errors='coerce')
    duplicate=f.period.duplicated(keep=False);lookup=f[~duplicate&f.period.notna()].set_index('period').to_dict('index');rows=[]
    def quarter(q):
        deps=[q] if q.quarter==1 else [q,q-1]
        if any(k not in lookup or pd.isna(lookup[k]['value']) for k in deps):raise ValueError('MISSING_REVENUE_DEPENDENCY')
        v=lookup[q]['value'] if len(deps)==1 else lookup[q]['value']-lookup[q-1]['value']
        return v,deps
    for period in sorted(lookup):
        if period.year<2016:continue
        record={'period':str(period),'period_end':period.end_time.normalize()}
        try:
            values={};deps=set()
            for q in [period,period-4,period-1,period-5]:
                v,d=quarter(q);values[q]=v;deps.update(d)
            if values[period]<0 or values[period-1]<0 or values[period-4]<=0 or values[period-5]<=0:raise ValueError('NONCOMPARABLE_REVENUE')
            if any(pd.isna(lookup[q][c]) for q in deps for c in ['NOTICE_DATE','UPDATE_DATE']):raise ValueError('MISSING_AVAILABILITY')
            avail=max(lookup[q][c] for q in deps for c in ['NOTICE_DATE','UPDATE_DATE'])
            current=lookup[period];current_avail=max(current['NOTICE_DATE'],current['UPDATE_DATE'])
            index=calendar.searchsorted(avail,side='right')
            if index>=len(calendar):raise ValueError('BEYOND_EXISTING_CALENDAR')
            growth=values[period]/values[period-4]-1;previous=values[period-1]/values[period-5]-1
            kind='DEPENDENCY_DELAYED' if avail>current_avail else ('CURRENT_UPDATE_DELAYED' if current['UPDATE_DATE']>current['NOTICE_DATE'] else 'NOTICE_ALIGNED_PROXY')
            record.update(status='AVAILABLE_PROXY',known_date=calendar[index],available_date=avail,current_notice=current['NOTICE_DATE'],current_update=current['UPDATE_DATE'],
                left_censored=bool(avail<calendar[0]),notice_to_available_days=(avail-current['NOTICE_DATE']).days,kind=kind,growth=growth,previous_growth=previous,acceleration=growth-previous,
                dependencies=';'.join(map(str,sorted(deps))),dependency_count=len(deps))
        except ValueError as exc:record['status']=str(exc)
        rows.append(record)
    return pd.DataFrame(rows),int(duplicate.sum())

def main():
    out=ROOT/'restart/financial_events';out.mkdir(parents=True,exist_ok=True)
    calendar=pd.DatetimeIndex(pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').index)
    allrows=[];sources={};audits=[]
    for path in sorted(CACHE.glob('*.parquet')):
        raw=pd.read_parquet(path,columns=['REPORT_DATE','NOTICE_DATE','UPDATE_DATE','TOTALOPERATEREVE']);events,dups=construct(raw,calendar)
        code,exchange=path.stem.split('.');events['instrument']=exchange+code;allrows.append(events)
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();audits.append({'instrument':exchange+code,'raw_rows':len(raw),'duplicate_period_rows':dups})
    ledger=pd.concat(allrows,ignore_index=True);ledger.to_parquet(out/'stock_event_ledger.parquet',index=False)
    available=ledger[ledger.status.eq('AVAILABLE_PROXY')].copy()
    assert available.known_date.gt(available.available_date).all()
    # Replay accepts only current/newer report periods; every raw computable event remains in ledger.
    available=available.sort_values(['instrument','known_date','period_end'])
    available['state_accepted']=available.period_end.ge(available.groupby('instrument').period_end.cummax())
    available.loc[available.duplicated(['instrument','known_date'],keep='last'),'state_accepted']=False
    available.to_parquet(out/'stock_available_events.parquet',index=False)
    available.groupby(['kind',available.known_date.dt.year]).size().rename('events').to_csv(out/'event_time_coverage.csv')
    pd.DataFrame(audits).to_csv(out/'source_audit.csv',index=False)
    result={'status':'EVENT_RECONSTRUCTION_COMPLETE_NOT_EFFICACY_VALIDATION','code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources':len(sources),'source_hashes':sources,'record_status':ledger.status.value_counts().to_dict(),
       'available_kinds':available.kind.value_counts().to_dict(),'state_accepted_events':int(available.state_accepted.sum()),'independent_stock_identities':available.instrument.nunique(),
       'timing_check':'every known_date strictly after latest dependency availability','limits':'current-vintage historical proxy; NOTICE_ALIGNED does not certify first publication; industry cohort reconstruction still pending'}
    (out/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_hashes'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
