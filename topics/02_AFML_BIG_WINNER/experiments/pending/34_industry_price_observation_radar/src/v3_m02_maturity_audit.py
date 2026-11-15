"""Compare reconstructed annual prefix enhancements to final retrospective fits."""
import json
from pathlib import Path
import pandas as pd
from audit_local_inputs import EP,sha
from v3_m02_targets import weekly_runs,sources_and_raw
from v2_s11_duration_identity_guarded import excursions
from v2_s13_duration_enhancements import enhancements,synthetic


def parent_ref(key,date):
    return f'{key[0]}|{key[1]}|{int(key[2])}|{int(key[3])}|{pd.Timestamp(date).date()}'


def main():
    out=EP/'outputs/v3_m02_maturity_audit'
    if out.exists():raise FileExistsError(out)
    out.mkdir();rawpath,calpath,raw,cal=sources_and_raw()
    tests=synthetic();assert all(x['pass_semantic'] and x['scale_invariant'] for x in tests)
    (out/'synthetic_checks.json').write_text(json.dumps(tests,indent=2)+'\n')
    pp=EP/'outputs/v2_s12_full_directory_duration/processes.parquet';cp=EP/'outputs/v2_s13_duration_enhancements/children.parquet'
    parent=pd.read_parquet(pp).set_index('process_id');child=pd.read_parquet(cp)
    final=[]
    for c in child.itertuples():
        p=parent.loc[c.parent_id]
        if c.status!='PATH_SUPPORTED' or p.status!='CONFIRMED' or p.left_context_unknown:continue
        key=(p.era,p.industry_code,p.block,p.complete_week_run)
        final.append(dict(parent_reference=parent_ref(key,p.start_date),start=c.start_date,end=c.end_date,confirm=c.confirm_date,
            parent_confirm=p.confirm_date,parent_breach=p.breach_date,child_id=c.child_id))
    final=pd.DataFrame(final);review_dates=pd.read_parquet(EP/'outputs/r01/weekly_catalog.parquet',columns=['date']).date.drop_duplicates().sort_values()
    cuts={year:review_dates[review_dates.dt.year.eq(year)].max() for year in range(2019,2026)}
    snapshots=[]
    for no,(key,w) in enumerate(weekly_runs(raw,cal)):
        for year,cut in cuts.items():
            z=w[w.date.le(cut)].reset_index(drop=True);y=z.y.to_numpy()
            if len(y)<9:continue
            for p in excursions(y):
                if p['status']!='CONFIRMED' or p['left_context_unknown']:continue
                start=p['start_i'];end=p['end_i'];_,children=enhancements(y[start:end+1])
                for c in children:
                    if c['status']!='PATH_SUPPORTED':continue
                    snapshots.append(dict(year=year,as_of=str(cut.date()),era=key[0],industry_code=key[1],parent_reference=parent_ref(key,z.date.iloc[start]),
                        start=str(z.date.iloc[start+c['start_i']].date()),end=str(z.date.iloc[start+c['end_i']].date()),confirm=str(z.date.iloc[start+c['confirm_i']].date()),
                        parent_closed=not p['right_open']))
        if no%100==0:print('annual prefix groups',no,'supported children',len(snapshots),flush=True)
    prefix=pd.DataFrame(snapshots);prefix.to_parquet(out/'annual_prefix_children.parquet',index=False)
    records=[];summaries=[]
    for year,cut in cuts.items():
        date=str(cut.date());a=prefix[prefix.year.eq(year)].copy();b=final[final.confirm.le(date)&final.parent_confirm.le(date)].copy()
        used=set();counts={'EXACT_START_CONFIRM':0,'OVERLAP_CHANGED':0,'PREFIX_ONLY_NO_OVERLAP':0,'FINAL_ONLY':0};closed_disagreement=0
        for ix,r in a.iterrows():
            candidates=b[b.parent_reference.eq(r.parent_reference)&~b.index.isin(used)]
            exact=candidates[candidates.start.eq(r.start)&candidates.confirm.eq(r.confirm)]
            chosen=None
            if len(exact):chosen=exact.index[0];status='EXACT_START_CONFIRM'
            else:
                overlap=candidates[candidates.start.le(r.end)&candidates.end.ge(r.start)]
                if len(overlap):
                    chosen=overlap.sort_values(['start','confirm']).index[0];status='OVERLAP_CHANGED'
                else:status='PREFIX_ONLY_NO_OVERLAP'
            counts[status]+=1
            if r.parent_closed and status!='EXACT_START_CONFIRM':closed_disagreement+=1
            if chosen is not None:used.add(chosen)
            records.append(dict(year=year,status=status,parent_reference=r.parent_reference,parent_closed=r.parent_closed,prefix_start=r.start,prefix_confirm=r.confirm,
                final_child=None if chosen is None else b.loc[chosen,'child_id'],final_start=None if chosen is None else b.loc[chosen,'start'],final_confirm=None if chosen is None else b.loc[chosen,'confirm']))
        for ix,r in b[~b.index.isin(used)].iterrows():
            closed=pd.notna(r.parent_breach) and r.parent_breach<=date
            counts['FINAL_ONLY']+=1
            if closed:closed_disagreement+=1
            records.append(dict(year=year,status='FINAL_ONLY',parent_reference=r.parent_reference,parent_closed=closed,prefix_start=None,prefix_confirm=None,final_child=r.child_id,final_start=r.start,final_confirm=r.confirm))
        assert closed_disagreement==0,(year,closed_disagreement)
        summaries.append(dict(year=year,cutoff=date,prefix_supported=len(a),final_nominally_confirmed=len(b),**counts,closed_parent_disagreements=closed_disagreement))
    pd.DataFrame(records).to_csv(out/'all_differences.csv',index=False);pd.DataFrame(summaries).to_csv(out/'annual_summary.csv',index=False)
    sources=[rawpath,calpath,pp,cp,EP/'protocols/v3_r00/m02_maturity_plan.md',EP/'src/v3_m02_targets.py',EP/'src/v2_s13_duration_enhancements.py',EP/'src/v2_s11_duration_identity_guarded.py',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()},scope='Training label availability audit, not method performance. Annual snapshots repeat processes; not independent samples.'),indent=2)+'\n')
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__=='__main__':main()
