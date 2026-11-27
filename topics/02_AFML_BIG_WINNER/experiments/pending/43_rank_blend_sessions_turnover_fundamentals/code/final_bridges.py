from statistics43 import *
from fund_panel import A,F
import json
def main():
    mo=pd.read_parquet(SUM/'monthly.parquet');out=[]
    for fee in [1,2]:
        for fam in ['transfer','B','transfer_head','native300b']:
            parts=[]
            for pool,aa,bb in [(300,'B/D','W/R'),(800,fam+'/D',('W/R' if fam=='B' else fam+'/A'))]:
                g=mo[(mo.pool==pool)&(mo.multiple==fee)&mo.arm.isin([aa,bb])].pivot(index=['segment','month'],columns='arm',values='net')
                z=(g[aa]-g[bb]).dropna().reset_index(name='delta'+str(pool)).rename(columns={'segment':'segment'+str(pool)})
                parts.append(z)
            h=parts[0].merge(parts[1],on='month',validate='1:1');out.append(h.assign(multiple=fee,comparison800=fam))
    pd.concat(out).to_csv(SUM/'common_calendar.csv',index=False)
    audits=[];mapping=[]
    for pool in [300,800]:
        ref=frozen(pool==800);r=ref.refit_R if pool==800 else ref.R
        ranks=ref[['entry_idx','instrument']].assign(value=r)
        m=book(pool==800);ranks['stock']=m.symbols.get_indexer(ranks.instrument)
        g=ranks.groupby('entry_idx').value;ranks['score']=g.rank()/(g.transform('count')+1)-.5
        solver=pd.read_parquet(O/f'W1_solver_{pool}.parquet')
        for seg in range(1,4 if pool==800 else 3):
            a=O/f'accounts/{pool}/W/R/{seg}';b=O/f'accounts/{pool}/W/capK/{seg}';p=pd.read_parquet(a/'targets.parquet');q=pd.read_parquet(b/'targets.parquet')
            v=p.merge(q,on=['day','stock','phase'],how='outer',suffixes=('_R','_cap')).fillna(0)
            v['diff']=(v.target_weight_R-v.target_weight_cap).abs()
            diff=v.groupby('day')['diff'].max()
            locks=solver[(solver.arm=='capK')&(solver.segment==seg)].set_index('day').locked
            free=locks[locks==0].index.intersection(diff.index);audits.append((pool,seg,len(diff),len(free),int((diff.reindex(free)>1e-9).sum()),diff.reindex(free).max(),int((diff>1e-9).sum())))
            order=pd.read_parquet(O/f'accounts/{pool}/W/LP/{seg}/transactions.parquet')
            order=order.merge(ranks[['entry_idx','stock','score']],left_on=['day','stock'],right_on=['entry_idx','stock'],how='left')
            order['buys']=order.flow.clip(lower=0);order['sales']=(-order.flow).clip(lower=0)
            order['rank_bin']=pd.cut(order.score,[-1,-.4,0,.25,.4,.45,.475,.49,1]).astype(str)
            mapping.append(order.groupby('rank_bin')[['buys','sales','target','fee']].sum().reset_index().assign(segment=seg,pool=pool))
    pd.DataFrame(audits,columns='pool segment days unlocked_days unlocked_mismatch unlocked_max_abs_weight all_mismatch'.split()).to_csv(SUM/'capK_target_parity.csv',index=False)
    pd.concat(mapping).to_csv(SUM/'rank_order_mapping.csv',index=False)
    # Feature families in the source are actual column names, including the nine trading features.
    feature=pd.read_csv(E/'scale/a4/results/feature_map.csv')
    removed=CFG['directions']['B']['remove'];assert set(feature.query("family=='trading'").feature)==set(removed)
    folds=pd.DataFrame(json.loads(p.read_text()) for p in sorted((O/'models').glob('*.json')))
    assert len(folds)==62 and (pd.to_datetime(folds.max_maturity)<folds.quarter.map(lambda q:pd.Period(q).start_time)).all()
    folds.to_csv(SUM/'fold_clock.csv',index=False)
    cov=pd.read_parquet(F/'F2_daily.parquet');cov=cov[cov.date>='2021-01-08'].copy()
    cov['year']=cov.date.dt.year;agg=cov.groupby(['year','field'])[['valid','rows','valid_top','top']].sum();agg['coverage']=agg.valid/agg.rows;agg['head_coverage']=agg.valid_top/agg.top;agg.to_csv(SUM/'F2_year.csv')
    info=pd.read_parquet(F/'F3_information.parquet');info.groupby(['anchor',info.date.dt.year])[['raw_IC','neutral_IC','residual_IC','residual_head_excess_logH10']].mean().to_csv(SUM/'F3_IC_year.csv')
if __name__=='__main__':main()
