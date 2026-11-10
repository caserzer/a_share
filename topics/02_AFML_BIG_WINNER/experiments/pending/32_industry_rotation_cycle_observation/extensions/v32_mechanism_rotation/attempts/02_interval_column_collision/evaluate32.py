"""Fixed diffusion falsification and descriptive leadership transitions."""
from pathlib import Path
import sys
import hashlib
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT.parent
sys.path.insert(0, str(EXT / 'v31_all_signal_economics/src'))
from common31 import sha, js, md, OLD, CACHE as ECON, block_interval, episode_starts, top_k
from evaluate31 import summarize
OUT = ROOT / 'outputs'
PRIVATE = OLD.parent / 'mechanism_v32'
IDENTITY = ['era','level','industry_code','date','threshold','benchmark']


def run():
    shuffled = pd.read_parquet(PRIVATE / 'shuffled_scores.parquet')
    outcomes = pd.read_parquet(ECON / 'outcomes.parquet').query("benchmark=='CSI_ALL' and months in [3,6]")
    labels = pd.read_parquet(OLD / 'stage_b_labels.parquet').query("threshold==0.15 and benchmark=='CSI_ALL'")
    calendar = pd.DatetimeIndex(pd.read_parquet(OLD / 'CSI_ALL.parquet').index).sort_values()
    economics=[]; contrasts=[]; rotation=[]; coverage=[]; label_rows=[]; market_rows=[]
    for frequency in ['W','BW','M']:
        f = pd.read_parquet(ECON / 'frames' / f'{frequency}_0.15_CSI_ALL.parquet')
        f = f[f.level.eq('L3')].reset_index(drop=True)
        f = f.merge(shuffled,on=IDENTITY,validate='one_to_one')
        assert f.shuffled_diffusion.notna().all()
        count = f.select_accepted.groupby([f.date,f.level]).transform('sum')
        eligible = f.state_eligible.eq(1) & f.market_up
        f['select_shuffled_matched'] = top_k(f,f.shuffled_diffusion,count,eligible)
        f['select_shuffled_fixed'] = f.risk_score.ge(.11)&f.shuffled_diffusion.ge(.11)&f.market_up
        for name in ['shuffled_matched','shuffled_fixed']:
            f['launch_'+name]=False
            chosen=f[f['select_'+name]]
            f.loc[chosen.index,'launch_'+name]=episode_starts(chosen,calendar)
        future_free=f.copy()
        f=f.merge(labels,on=['row_id','threshold','benchmark'],validate='one_to_one')
        f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
        outcome=f.merge(outcomes.drop(columns='benchmark'),on='row_id',validate='one_to_many')
        daily=[]
        methods=['accepted','capacity_matched','diffusion_matched','shuffled_matched','shuffled_fixed','no_market','momentum_matched']
        for method in methods:
            for unit,prefix in [('all_alerts','select_'),('six_month_launches','launch_')]:
                g=outcome[outcome[prefix+method]&outcome.months.eq(6)]
                economics.append(dict(frequency=frequency,method=method,unit=unit,**summarize(g)))
                s=g[g.outcome_status.eq('OK')].groupby('date').excess_return.mean().rename(method)
                daily.append((unit,method,s))
                if method in ['accepted','no_market']:
                    for up,part in g.groupby('market_up'):
                        market_rows.append(dict(frequency=frequency,method=method,unit=unit,market_up=up,**summarize(part)))
        for unit in ['all_alerts','six_month_launches']:
            p=pd.concat([s for u,_,s in daily if u==unit],axis=1)
            for left,right in [('diffusion_matched','capacity_matched'),('diffusion_matched','shuffled_matched'),('accepted','shuffled_fixed')]:
                pair=p[[left,right]].dropna()
                contrasts.append(dict(frequency=frequency,unit=unit,left=left,right=right,
                    paired_dates=len(pair),**block_interval(pair.index,pair[left]-pair[right])))
        # Original universe defines current leaders before future missing rows are removed.
        future_free['current_rank']=future_free.groupby(['date','era','level']).mom63.rank(method='first',ascending=False)
        future_free['current_leader']=future_free.current_rank.le(np.ceil(future_free.groupby(['date','era','level']).row_id.transform('size')*.2))
        for months in [3,6]:
            h=future_free.merge(outcomes[outcomes.months.eq(months)].drop(columns='benchmark'),on='row_id',validate='one_to_one')
            for key,group in h.groupby(['date','era','level']):
                good=group[group.outcome_status.eq('OK')].copy()
                coverage.append(dict(frequency=frequency,months=months,date=key[0],era=key[1],
                    observations=len(group),known=len(good),fraction=len(good)/len(group)))
                if len(good)<5:
                    continue
                top=int(np.ceil(len(good)*.2))
                good['future_leader']=good.excess_return.rank(method='first',ascending=False).le(top)
                seed=int(hashlib.sha256(('32:'+str((frequency,months,key))).encode()).hexdigest()[:8],16)
                good['permuted_leader']=np.random.default_rng(seed).permutation(good.future_leader.to_numpy())
                good['new_leader']=good.future_leader & ~good.current_leader
                good['permuted_new']=good.permuted_leader & ~good.current_leader
                for method in ['accepted','momentum_matched','capacity_matched','diffusion_matched']:
                    selected=good['select_'+method]
                    rotation.append(dict(frequency=frequency,months=months,date=key[0],method=method,
                        selected=int(selected.sum()),known=len(good),future_leaders=int(good.future_leader.sum()),
                        current_leaders=int(good.current_leader.sum()),new_leaders=int(good.new_leader.sum()),
                        retained=int((good.current_leader&good.future_leader).sum()),
                        retained_permuted=int((good.current_leader&good.permuted_leader).sum()),
                        hit_future=int((selected&good.future_leader).sum()),hit_new=int((selected&good.new_leader).sum()),
                        permuted_new_leaders=int(good.permuted_new.sum()),hit_permuted_new=int((selected&good.permuted_new).sum())))
                label_rows.append(good[['row_id','date','era','industry_code','current_leader','future_leader','new_leader']].assign(frequency=frequency,months=months))
        print('mechanism and leadership evaluated',frequency,flush=True)
    pd.DataFrame(economics).to_csv(OUT/'mechanism_economics.csv',index=False)
    pd.DataFrame(contrasts).to_csv(OUT/'mechanism_intervals.csv',index=False)
    pd.DataFrame(market_rows).to_csv(OUT/'market_state_economics.csv',index=False)
    daily=pd.DataFrame(rotation);daily.to_csv(OUT/'rotation_daily_counts.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'rotation_coverage.csv',index=False)
    pd.concat(label_rows).to_parquet(PRIVATE/'rotation_labels.parquet',index=False)
    summary=[]
    for key,g in daily.groupby(['frequency','months','method']):
        sums=g.select_dtypes('number').sum()
        ratio=lambda a,b: sums[a]/sums[b] if sums[b] else np.nan
        summary.append(dict(zip(['frequency','months','method'],key),dates=len(g),active_dates=int(g.selected.gt(0).sum()),
            current_leader_retention=ratio('retained','current_leaders'),
            permutation_retention=ratio('retained_permuted','current_leaders'),
            future_leader_precision=ratio('hit_future','selected'),
            new_leader_recall=ratio('hit_new','new_leaders'),
            new_leader_precision=ratio('hit_new','selected'),
            permuted_new_recall=ratio('hit_permuted_new','permuted_new_leaders'),
            note='descriptive count-weighted transition rates; not independent observations'))
    pd.DataFrame(summary).to_csv(OUT/'rotation_summary.csv',index=False)
    paired=[]
    for (frequency,months),g in daily.groupby(['frequency','months']):
        parts={name:v.set_index('date') for name,v in g.groupby('method')}
        a=parts['accepted']; b=parts['momentum_matched']
        x=(a.hit_new/a.new_leaders.replace(0,np.nan))-(b.hit_new/b.new_leaders.replace(0,np.nan))
        x=x.dropna()
        paired.append(dict(frequency=frequency,months=months,contrast='new_leader_recall_accepted_minus_momentum',
            dates=len(x),**block_interval(x.index,x)))
    pd.DataFrame(paired).to_csv(OUT/'rotation_intervals.csv',index=False)
    print(pd.DataFrame(summary).query("months==6 and method=='accepted'").to_string(index=False))


if __name__=='__main__':
    run()
