"""Fixed stratified signal/miss case review; no re-selection of methods or labels."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep34-mpl-cache')
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha
from v2_b06_replay import prepare


def main():
    out=EP/'outputs/v2_s02_case_audit'
    if out.exists():raise FileExistsError('Preserve fixed case review')
    out.mkdir()
    root=EP/'outputs/v2_s01';pp=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/processes.parquet'
    rawfile=PRIOR/'daily_industries.parquet';marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
    paths=[pp,rawfile,marketfile,root/'followup/all_new_paths.parquet',EP/'protocols/v2_s02/plan.md',EP/'src/v2_b06_replay.py',Path(__file__)]
    pmap=pd.read_parquet(pp).set_index('process_id');raw=pd.read_parquet(rawfile,columns=['era','industry_code','industry_name','block','date','day_i','nav'])
    groups={k:g.sort_values('day_i') for k,g in raw[raw.nav.gt(0)&raw.block.notna()].groupby(['era','industry_code','block'])}
    market=pd.read_parquet(marketfile).close
    follows=pd.read_parquet(paths[3]);follows=follows[follows.horizon.eq(20)]
    c=prepare();cg={k:g for k,g in c.groupby(['era','industry_code'])}
    chosen=[];denoms=[];misses=[]
    for arm in ['A','B']:
        evfile=root/arm/'events.parquet';qfile=root/'evaluation_parent_child/runs/v2_s01'/arm/'event_quality.parquet';pcfile=qfile.parent/'parent_coverage.parquet'
        paths.extend([evfile,qfile,pcfile]);ev=pd.read_parquet(evfile);q=pd.read_parquet(qfile);pc=pd.read_parquet(pcfile)
        x=q[q.kind.eq('NEW')].merge(ev[['event_id','r5','r20','block']],on='event_id',validate='one_to_one').merge(follows[follows.arm.eq(arm)][['event_id','status','absolute_return','max_drawdown']],on='event_id',suffixes=('','_20'),validate='one_to_one')
        masks={
            'TIMELY_SUPPORTED_POSITIVE20':x.status.eq('COVERED')&x.timing.eq('TIMELY')&x.status_20.eq('MATURE')&x.absolute_return.gt(0),
            'LATE_SUPPORTED_NONPOSITIVE20':x.status.eq('COVERED')&x.timing.eq('LATE')&x.status_20.eq('MATURE')&x.absolute_return.le(0),
            'SHORT_PROCESS_ALERT':x.status.eq('SHORT_OR_UNCONFIRMED_PROCESS'),
            'REPEAT_NEW':x.status.eq('REPEAT'),
            'UNKNOWN_NEW':x.status.str.contains('UNKNOWN')}
        for cat,mask in masks.items():
            for era in ['SW2014','SW2021']:
                z=x[mask&x.era.eq(era)].sort_values(['date','event_id'])
                denoms.append(dict(arm=arm,era=era,category=cat,count=len(z)))
                if not z.empty:
                    r=z.iloc[0].to_dict();chosen.append(dict(**r,arm=arm,category=cat,reference_date=r['date']))
        for row in pc[~pc.covered].itertuples():
            p=pmap.loc[row.process_id];g=cg.get((p.era,p.industry_code),pd.DataFrame())
            part=g[g.date.between(p.start_date,p.end_date)&g.block.eq(p.block)]
            valid=part.r40.notna();positive5=valid&part.r5.gt(0);eligible=positive5&part.r20.gt(0)
            price=groups[(p.era,p.industry_code,p.block)]
            base=np.exp(np.log(price[price.date.between(p.reference_week_start,p.start_date)].nav).median())
            aligned=eligible&part.nav.gt(base)
            reason=('NO_HISTORY_SUPPORTED_WEEK' if not valid.any() else 'NO_POSITIVE5_WEEK' if not positive5.any() else
                    'POSITIVE5_BUT_20_NOT_POSITIVE' if not eligible.any() else 'ELIGIBLE_BUT_NO_REFERENCE_ALIGNMENT' if not aligned.any() else
                    'ALIGNED_ELIGIBILITY_EXISTS_NEEDS_POOL_AUDIT')
            misses.append(dict(arm=arm,process_id=row.process_id,era=p.era,industry_code=p.industry_code,industry_name=p.industry_name,
                block=p.block,start_date=p.start_date,end_date=p.end_date,visible_date=p.visible_date,right_open=p.right_open,
                weeks=len(part),history_supported=int(valid.sum()),positive5=int(positive5.sum()),eligible=int(eligible.sum()),
                aligned_eligible=int(aligned.sum()),preliminary_reason=reason))
        mm=pd.DataFrame([m for m in misses if m['arm']==arm])
        for era in ['SW2014','SW2021']:
            z=mm[mm.era.eq(era)&~mm.right_open].sort_values(['start_date','process_id'])
            denoms.append(dict(arm=arm,era=era,category='MISSED_CLOSED_PARENT',count=len(z)))
            if not z.empty:
                r=z.iloc[0].to_dict();chosen.append(dict(arm=arm,era=era,industry_code=r['industry_code'],block=r['block'],category='MISSED_CLOSED_PARENT',
                    parent_id=r['process_id'],event_id=None,date=None,reference_date=r['visible_date'],status='MISSED',
                    preliminary_reason=r['preliminary_reason'],eligible=r['eligible'],aligned_eligible=r['aligned_eligible']))
    selected=pd.DataFrame(chosen);miss=pd.DataFrame(misses);den=pd.DataFrame(denoms)
    selected.to_csv(out/'selected_cases.csv',index=False);den.to_csv(out/'case_category_denominators.csv',index=False);miss.to_parquet(out/'all_missed_parent_audit.parquet',index=False)
    miss.groupby(['arm','preliminary_reason']).size().rename('count').to_csv(out/'miss_reason_counts.csv')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc';font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
    reviewrows=[]
    for (arm,era),cases in selected.groupby(['arm','era']):
        fig,axes=plt.subplots(len(cases),1,figsize=(12,3.1*len(cases)),squeeze=False)
        for ax,r in zip(axes.flat,cases.itertuples()):
            g=groups[(r.era,r.industry_code,r.block)];target=pd.Timestamp(r.reference_date)
            targetrow=g[g.date.eq(target)].iloc[0];day=int(targetrow.day_i)
            z=g[g.day_i.between(day-60,day+60)];base=z.nav.iloc[0]
            ax.plot(z.date,z.nav/base*100,color='#333',label='行业同链价格')
            m=market.reindex(pd.DatetimeIndex(z.date));anchor=m.first_valid_index()
            if anchor is not None:ax.plot(z.date,m/m.loc[anchor]*100,color='#888',alpha=.7,label='市场同期变化')
            p=pmap.loc[r.parent_id] if pd.notna(r.parent_id) else None
            if p is not None:
                lo=max(pd.Timestamp(p.start_date),z.date.min());hi=min(pd.Timestamp(p.end_date),z.date.max())
                if lo<=hi:ax.axvspan(lo,hi,color='green',alpha=.12,label='事后父过程范围')
            ax.axvline(target,color='red',label='NEW提示' if pd.notna(r.event_id) else '未覆盖过程可辨参考点')
            name=g.industry_name.iloc[0]
            extra='' if pd.isna(r.absolute_return) else f'；后20日 {r.absolute_return:.1%}'
            ax.set_title(f'{arm} {name} {r.reference_date} {r.category}\n{r.event_id or r.parent_id}{extra}')
            ax.legend(fontsize=8);ax.grid(alpha=.2)
            reviewrows.append(dict(arm=arm,era=era,industry_name=name,industry_code=r.industry_code,category=r.category,
                                  event_id=r.event_id,parent_id=r.parent_id,reference_date=r.reference_date,
                                  absolute_return=None if pd.isna(r.absolute_return) else r.absolute_return,
                                  r5=None if pd.isna(r.r5) else r.r5,r20=None if pd.isna(r.r20) else r.r20))
        fig.tight_layout();fig.savefig(out/f'cases_{arm}_{era}.png',dpi=110);plt.close(fig)
    pd.DataFrame(reviewrows).to_csv(out/'readable_cases.csv',index=False)
    summary=dict(scope='Fixed historical case review and preliminary miss accounting; no label or method changes',
                 selected_cases=len(selected),category_denominators=den.to_dict('records'),
                 misses_by_arm=miss.groupby('arm').size().to_dict(),
                 limitations=['case selection is stratified, not a performance sample','eligibility is not full causal omission attribution',
                             'market paths are context, not stock/sector-specific causal evidence','future prices shown only for retrospective review'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in paths},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print('Selected',len(selected),'cases; misses',summary['misses_by_arm']);print(miss.groupby(['arm','preliminary_reason']).size().to_string())


if __name__=='__main__':main()
