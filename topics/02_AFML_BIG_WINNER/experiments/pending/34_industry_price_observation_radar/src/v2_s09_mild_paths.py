"""Signal-blind diagnostic windows for mild recovery across volatility backgrounds."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP, PRIOR, sha

def main():
 out=EP/'outputs/v2_s09_mild_paths';out.mkdir(exist_ok=False)
 rawfile=PRIOR/'daily_industries.parquet';pdir=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected'
 files=[rawfile,pdir/'weekly_evaluation_states.parquet',pdir/'processes.parquet',EP/'protocols/v2_s09/plan.md',Path(__file__)]
 rec=json.loads((PRIOR/'receipt.json').read_text());calpath=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')));files.append(calpath)
 cal=pd.read_parquet(calpath);cal['week']=cal.date.dt.to_period('W-SUN').astype(str);weeks=cal.groupby('week').date.max();weekid={w:i for i,w in enumerate(weeks.index)}
 raw=pd.read_parquet(rawfile,columns=['date','era','industry_code','industry_name','block','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN').astype(str);raw['y']=np.log(raw.nav)
 weekly=raw.groupby(['era','industry_code','block','week']).agg(y=('y','median'),industry_name=('industry_name','first')).reset_index()
 states=pd.read_parquet(files[1]);weekly=weekly.merge(states,on=['era','industry_code','block','week'],validate='one_to_one');weekly=weekly[~weekly.state.eq('PARTIAL_WEEK_UNKNOWN')].copy();weekly['wi']=weekly.week.map(weekid);weekly['date']=weekly.week.map(weeks)
 parents=pd.read_parquet(files[2]);confirmed=parents[parents.status.eq('CONFIRMED')&~parents.left_context_unknown]
 spans={k:g for k,g in confirmed.groupby(['era','industry_code','block'])}
 rows=[];segments={}
 for key,g in weekly.groupby(['era','industry_code','block']):
  g=g.sort_values('wi');g['run']=g.wi.diff().ne(1).cumsum()
  for run,z in g.groupby('run'):
   z=z.reset_index(drop=True);token=(*key,int(run));segments[token]=z
   y=z.y.to_numpy()
   for i in range(8,len(z)-8):
    scale=max(.002,2*np.median(np.abs(np.diff(y[i-8:i+1]))));future=y[i+1:i+9]
    mild=bool((future>y[i]).all() and future[4:].mean()>future[:4].mean() and 0<y[i+8]-y[i]<scale)
    start=z.date.iloc[i];end=z.date.iloc[i+8];sp=spans.get(key)
    overlap=[] if sp is None else sp[(pd.to_datetime(sp.start_date)<=end)&(pd.to_datetime(sp.end_date)>=start)].process_id.tolist()
    rows.append(dict(era=key[0],industry_code=key[1],block=int(key[2]),run=int(run),i=i,date=str(start.date()),end=str(end.date()),industry_name=z.industry_name.iloc[i],scale=scale,net_gain=float(np.expm1(y[i+8]-y[i])),mild=mild,overlap=bool(overlap),parent_ids='|'.join(overlap)))
 d=pd.DataFrame(rows);bounds=d.groupby('era').scale.quantile([.25,.75]).unstack();d['volatility_band']='MIDDLE'
 for era,b in bounds.iterrows():
  d.loc[d.era.eq(era)&d.scale.le(b.loc[.25]),'volatility_band']='LOW'
  d.loc[d.era.eq(era)&d.scale.ge(b.loc[.75]),'volatility_band']='HIGH'
 d.to_parquet(out/'all_diagnostic_windows.parquet',index=False);bounds.to_csv(out/'scale_quartiles.csv')
 mild=d[d.mild&d.volatility_band.ne('MIDDLE')];counts=mild.groupby(['era','volatility_band','overlap']).size().rename('overlapping_windows').reset_index();counts.to_csv(out/'diagnostic_counts.csv',index=False)
 selected=mild.sort_values(['date','industry_code']).groupby(['era','volatility_band','overlap'],sort=True).head(1).sort_values(['era','volatility_band','overlap']);selected.to_csv(out/'selected_cases.csv',index=False)
 fig,axes=plt.subplots(4,2,figsize=(14,16));traces=[]
 for ax,(_,r) in zip(axes.ravel(),selected.iterrows()):
  z=segments[(r.era,r.industry_code,r.block,r.run)];i=int(r.i);q=z.iloc[i-8:i+9].copy();q['rebased']=np.exp(q.y-z.y.iloc[i]);q['case_key']=f'{r.era}/{r.industry_code}/{r.date}';traces.append(q)
  x=np.arange(-8,9);ax.plot(x,q.rebased,marker='o',ms=3);ax.axvline(0,color='grey');ax.axhline(1,color='grey',lw=.6);ax.axhline(np.exp(r.scale),color='orange',ls='--',label='local scale')
  ax.set_title(f'{r.era} {r.industry_code} {r.date}\n{r.volatility_band}; confirmed overlap={r.overlap}');ax.set_xlabel('complete trading weeks from reference');ax.legend(fontsize=8)
 for ax in axes.ravel()[len(selected):]:ax.axis('off')
 fig.tight_layout();fig.savefig(out/'cases.png',dpi=130);plt.close(fig)
 if traces:pd.concat(traces).to_parquet(out/'selected_case_paths.parquet',index=False)
 summary={'supported_windows':len(d),'mild_windows':int(d.mild.sum()),'selected_cases':len(selected),'counts':counts.to_dict('records'),'limits':'Overlapping descriptive windows, not new process labels or method recall. No signal-list input.'}
 (out/'receipt.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in files},'summary':summary,'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}},ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
