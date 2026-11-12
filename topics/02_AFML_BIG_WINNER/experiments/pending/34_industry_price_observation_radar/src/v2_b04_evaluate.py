"""Evaluation-only join after replay. Never called by signal generation."""
import json
import sys
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha


def main():
    base=Path(sys.argv[1]).resolve()
    assert base.is_relative_to((EP/'outputs/v2_b04').resolve())
    out=base/'evaluation'
    if out.exists():raise FileExistsError('Preserve first evaluation')
    out.mkdir()
    paths=[base/'events.parquet',EP/'outputs/r00_v2_label_probe02/segments.parquet',
           EP/'outputs/r00_v2_label_probe02/persistence/candidate_diagnostic.parquet',
           EP/'outputs/r00_v2_window_recovery/windows.parquet',
           EP/'outputs/r00_v2_window_recovery/process_window_audit.parquet',
           EP/'protocols/v2_b04/plan.md',Path(__file__)]
    inputs={str(f):sha(f) for f in paths}
    ev=pd.read_parquet(paths[0]);st=pd.read_parquet(paths[1]);cand=pd.read_parquet(paths[2]);ww=pd.read_parquet(paths[3]);audit=pd.read_parquet(paths[4])
    by_industry={k:g for k,g in st.groupby(['era','industry_code'])}
    cd=cand.set_index('segment_id').to_dict('index');aw=audit.set_index('segment_id').to_dict('index')
    windows={k:g for k,g in ww.groupby('segment_id')}
    known=cand[cand.diagnostic_status.eq('RETAINED')&~cand.end_boundary].copy()
    covered={};ledger=[]
    for row in ev[ev.kind.isin(['NEW','UPDATE'])].sort_values(['date','event_id']).itertuples():
        date=row.date.strftime('%Y-%m-%d');g=by_industry.get((row.era,row.industry_code));sid=None
        matches=g[g.start_date.le(date)&g.end_date.ge(date)&g.block.eq(row.block)] if g is not None else pd.DataFrame()
        timing=None
        if len(matches)!=1:status='UNKNOWN'
        else:
            s=matches.iloc[0];sid=s.segment_id
            if s.end_boundary or s.partial_weeks>0 or s.kind=='LEFT_UNKNOWN':status='UNKNOWN'
            elif not row.positive_evidence:status='NO_PRICE_EVIDENCE'
            elif sid not in cd:status='NO_INDEPENDENT_NEW_PROCESS'
            elif cd[sid]['diagnostic_status']=='PARTIAL_WEEK_UNKNOWN':status='UNKNOWN'
            elif cd[sid]['diagnostic_status']!='RETAINED':status='NOT_PERSISTENT_REFERENCE'
            elif s.kind=='HEATING' and not row.enhancement_evidence:status='NO_NEW_ENHANCEMENT_EVIDENCE'
            else:
                w=windows.get(sid,pd.DataFrame(columns=['start','end']))
                if not ((w.start<=date)&(w.end>=date)).any():status='OUTSIDE_ACTIVE_WINDOW'
                elif sid in covered:status='REPEAT'
                else:
                    timing='TIMELY' if aw[sid]['timely_reference_end'] is not None and date<=aw[sid]['timely_reference_end'] else 'LATE'
                    status=timing;covered[sid]=dict(event_id=row.event_id,date=date,kind=row.kind,timing=timing)
        ledger.append(dict(event_id=row.event_id,date=date,era=row.era,industry_code=row.industry_code,
                           kind=row.kind,process=sid,status=status,timing=timing))
    le=pd.DataFrame(ledger);pr=[]
    for row in known.to_dict('records'):
        hit=covered.get(row['segment_id']);pr.append(dict(process=row['segment_id'],family=row['family_id'],
            era=row['era'],industry_code=row['industry_code'],kind=row['kind'],start=row['start_date'],
            covered=hit is not None,first_event=None if hit is None else hit['event_id'],
            first_date=None if hit is None else hit['date'],source=None if hit is None else hit['kind'],timing=None if hit is None else hit['timing']))
    pr=pd.DataFrame(pr);new=le[le.kind.eq('NEW')];known_new=new[~new.status.eq('UNKNOWN')]
    assert set(covered)<=set(known.segment_id)
    assert pr.process.is_unique and le.event_id.is_unique
    assert len(pr)==int(pr.covered.sum())+int((~pr.covered).sum())
    summary=dict(scope='Exploratory frozen L02-P/W02 label view; NOT validated method',
        known_processes=len(pr),covered=int(pr.covered.sum()),missed=int((~pr.covered).sum()),
        coverage=float(pr.covered.mean()),coverage_timing=pr[pr.covered].timing.value_counts().to_dict(),
        coverage_source=pr[pr.covered].source.value_counts().to_dict(),
        known_families=int(pr.family.nunique()),covered_families=int(pr[pr.covered].family.nunique()),
        new_total=len(new),new_unknown=int(new.status.eq('UNKNOWN').sum()),new_evaluable=len(known_new),
        new_effective=int(known_new.status.isin(['TIMELY','LATE']).sum()),
        new_effective_rate=float(known_new.status.isin(['TIMELY','LATE']).mean()),
        new_types=new.status.value_counts().to_dict(),update_types=le[le.kind.eq('UPDATE')].status.value_counts().to_dict())
    le.to_parquet(out/'event_quality.parquet',index=False);pr.to_parquet(out/'process_coverage.parquet',index=False)
    pr.assign(year=pr.start.str[:4]).groupby(['era','year','kind']).agg(processes=('process','size'),covered=('covered','sum')).reset_index().to_csv(out/'process_strata.csv',index=False)
    new.assign(year=new.date.str[:4]).groupby(['era','year','status']).size().rename('count').reset_index().to_csv(out/'new_strata.csv',index=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=inputs,artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
