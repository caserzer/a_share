"""Add pending duration diagnostics and independently audit all new parent identities."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from audit_local_inputs import EP,PRIOR,sha

def main():
 root=EP/'outputs/v2_s12_full_directory_duration';out=root/'boundary_audit';out.mkdir(exist_ok=False)
 pf=root/'processes.parquet';wf=root/'weekly_evaluation_states.parquet';oldfile=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/processes.parquet';rawfile=PRIOR/'daily_industries.parquet'
 parents=pd.read_parquet(pf);states=pd.read_parquet(wf);old=pd.read_parquet(oldfile)
 raw=pd.read_parquet(rawfile,columns=['date','era','industry_code','block','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN').astype(str);raw['y']=np.log(raw.nav)
 rec=json.loads((PRIOR/'receipt.json').read_text());calfile=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')));cal=pd.read_parquet(calfile);cal['week']=cal.date.dt.to_period('W-SUN').astype(str);dates=cal.groupby('week').date.max();widx={w:i for i,w in enumerate(dates.index)}
 w=raw.groupby(['era','industry_code','block','week']).y.median().reset_index().merge(states,on=['era','industry_code','block','week'],validate='one_to_one');w=w[~w.state.eq('PARTIAL_WEEK_UNKNOWN')].copy();w['date']=w.week.map(dates);w['wi']=w.week.map(widx)
 parents['start_dt']=pd.to_datetime(parents.start_date);parents['end_dt']=pd.to_datetime(parents.end_date)
 pg={k:g for k,g in parents.groupby(['era','industry_code','block'])};all_candidates=[];revised=[];verified=0
 for key,g in w.groupby(['era','industry_code','block']):
  g=g.sort_values('wi');g['local_run']=g.wi.diff().ne(1).cumsum();ps=pg.get(key,parents.iloc[:0])
  for run,z in g.groupby('local_run'):
   z=z.reset_index(drop=True);y=z.y.to_numpy();n=len(z);index={str(t.date()):i for i,t in enumerate(z.date)};p=ps[ps.start_dt.ge(z.date.min())&ps.end_dt.le(z.date.max())].sort_values('start_dt')
   if len(p)>1:assert (p.start_dt.iloc[1:].to_numpy()>p.end_dt.iloc[:-1].to_numpy()).all()
   for row in p.itertuples():
    a=index[row.start_date];b=index[row.end_date];v=index[row.visible_date];eps=max(.002,2*np.median(abs(np.diff(y[a-8:a+1]))));assert a>=8 and np.isclose(eps,row.epsilon)
    assert a<=v<=b
    if row.confirm_date is not None:
     q=index[row.confirm_date];assert v<=q<=b
     if row.route=='DURATION8':
      assert q-a==8 and y[a]<=min(y[a-8:a+1]) and (y[a+1:q+1]>y[a]).all()
      assert np.median(y[q-3:q+1])-np.median(y[q-7:q-3])>=.002
      assert np.median(y[q-3:q+1])-y[a]>=.002 and max(y[a:q+1])-y[q]<eps
     else:assert q-a>=4 and (y[q-3:q+1]>y[a]).all() and y[q]-y[a]>=eps
    if row.breach_date is not None:
     breach=index[row.breach_date];assert breach==b+1
     assert y[breach]<=y[a] or max(y[a:breach+1])-y[breach]>=eps
    verified+=1
   pending=set()
   for ref in range(8,n-1):
    if y[ref]>min(y[ref-8:ref+1]):continue
    due=ref+8;end=min(due,n-1);tail=y[ref+1:end+1]
    losses=np.where(tail<=y[ref])[0];loss=None if not len(losses) else ref+1+int(losses[0])
    visible_end=end if loss is None else loss-1
    vis=next((j for j in range(ref+1,visible_end+1) if y[j]-y[ref]>=.002),None)
    if vis is None:continue
    overlaps=p[p.start_dt.le(z.date.iloc[end])&p.end_dt.ge(z.date.iloc[ref])]
    if loss is not None:status='REFERENCE_LOST'
    elif len(overlaps):status='PARENT_IDENTITY_PRECEDENCE'
    elif due>=n:status='DURATION_RIGHT_UNKNOWN';pending.update(range(vis,end+1))
    else:status='DURATION_NOT_CONFIRMED'
    all_candidates.append(dict(era=key[0],industry_code=key[1],block=int(key[2]),local_run=int(run),reference=str(z.date.iloc[ref].date()),visible=str(z.date.iloc[vis].date()),end=str(z.date.iloc[end].date()),status=status,observed_weeks=end-ref,parent_ids='|'.join(overlaps.process_id)))
   for i,r in z.iterrows():
    state=r.state
    if pd.isna(r.process_id) and state!='CONTEXT_INSUFFICIENT':
     if i in pending:state='DURATION_RIGHT_UNKNOWN'
     elif n-1-i<8:state='RIGHT_CONTEXT_UNKNOWN'
    revised.append(dict(era=key[0],industry_code=key[1],block=int(key[2]),week=r.week,state=state,process_id=r.process_id))
 assert verified==len(parents),(verified,len(parents))
 partial=states[states.state.eq('PARTIAL_WEEK_UNKNOWN')];newstates=pd.concat([partial,pd.DataFrame(revised)],ignore_index=True).sort_values(['era','industry_code','block','week'])
 assert len(newstates)==len(states) and not newstates.duplicated(['era','industry_code','block','week']).any()
 pd.DataFrame(all_candidates).to_parquet(out/'duration_candidate_diagnostics.parquet',index=False);newstates.to_parquet(out/'weekly_evaluation_states.parquet',index=False)
 bridges=[]
 for key,np_ in parents.groupby(['era','industry_code','block']):
  op=old[old.era.eq(key[0])&old.industry_code.eq(key[1])&old.block.eq(key[2])]
  for r in np_.itertuples():
   for s in op[op.start_date.le(r.end_date)&op.end_date.ge(r.start_date)].itertuples():
    bridges.append(dict(new_id=r.process_id,old_id=s.process_id,new_status=r.status,old_status=s.status,same_start=r.start_date==s.start_date,same_end=r.end_date==s.end_date))
 bridge=pd.DataFrame(bridges);bridge.to_csv(out/'old_new_interval_bridge.csv',index=False)
 summary={'all_parent_rows_verified':verified,'confirmed':int(parents.status.eq('CONFIRMED').sum()),'confirmed_known_context':int((parents.status.eq('CONFIRMED')&~parents.left_context_unknown).sum()),'route_status_counts':parents.groupby(['route','status']).size().rename('count').reset_index().to_dict('records'),'candidate_status_counts':pd.Series([r['status'] for r in all_candidates]).value_counts().to_dict(),'weekly_state_counts':newstates.state.value_counts().to_dict(),'old_without_overlap':int((~old.process_id.isin(bridge.old_id)).sum()),'new_without_overlap':int((~parents.process_id.isin(bridge.new_id)).sum()),'old_with_multiple_new':int(bridge.groupby('old_id').new_id.nunique().gt(1).sum()),'new_with_multiple_old':int(bridge.groupby('new_id').old_id.nunique().gt(1).sum()),'limits':'Process-definition audit only; no method evaluation. Overlap is not identity equivalence. Boundary states supersede raw core weekly states for this prototype.'}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 inputs=[pf,wf,oldfile,rawfile,calfile,EP/'protocols/v2_s12/plan.md',Path(__file__)]
 (out/'receipt.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in inputs},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
