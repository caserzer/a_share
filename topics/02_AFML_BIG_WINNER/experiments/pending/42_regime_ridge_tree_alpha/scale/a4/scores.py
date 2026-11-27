"""Group the actual 78 frozen columns and perturb one family at a time on 300/800."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scale_common import *
import json
import re
OUT=Path(__file__).resolve().parent/'results'
FROZEN=next(EP42.parent.glob('40_*/lightgbm/followup/csi800_69/results'))
FAMILIES=['short','medium','volatility','trading','candle','market','other']

def family(c):
    if c.startswith('market_'):return 'market'
    if c.startswith(('money_rel','turnover_rel','volume_rel')):return 'trading'
    if c.startswith(('vol','amp')):return 'volatility'
    if c.startswith(('ret_lag','xsret_lag')):
        return 'short' if int(re.search(r'\d+$',c).group())<=5 else 'medium'
    if c in ['mom1','mom3','mom5','seg2_5']:return 'short'
    if c.startswith(('pos','dd','seg','mom')):return 'medium'
    if c.startswith(('body','upvolume','price_volume_corr')):return 'candle'
    return 'other'

def main():
    mapping=pd.DataFrame({'feature':COLS,'family':[family(c) for c in COLS]})
    mapping.to_csv(OUT/'feature_map.csv',index=False)
    checks=[];splits=[]
    narrow=data(COLS)
    s300=pd.read_parquet(SCORES,columns=KEY+['R','T'])
    s800=pd.read_parquet(FROZEN/'scores.parquet',columns=KEY+['refit_R','refit_T']).rename(columns={'refit_R':'R','refit_T':'T'})
    for pool in ['300','800']:
        for q,tr,te in outer_folds(narrow):
            if pool=='800':
                g=pd.read_parquet(EP42/'events/results/features'/f'{q}.parquet',columns=KEY+['entry_idx']+COLS)
            else:g=te[KEY+['entry_idx']+COLS]
            g=g.merge(s300 if pool=='300' else s800,on=KEY,validate='1:1')
            root=FROZEN/'models'/('transfer' if pool=='300' else 'refit')/str(q)
            cfg=json.loads((root/'ridge.json').read_text())
            tree=lgb.Booster(model_file=str(root/'tree.txt'))
            cols=cfg['columns'];assert list(cols)==list(COLS)
            med=np.array(cfg['median']);coef=np.array(cfg['coef'])
            orig=g[cols].to_numpy()
            x=(np.where(np.isfinite(orig),orig,med)-cfg['mean'])/np.array(cfg['sd'])
            out=g[KEY+['entry_idx','R','T']].copy()
            out['intercept']=cfg['intercept']
            rp=cfg['intercept']+x@coef
            err_r=np.abs(rp-g.R).max()
            assert err_r<1e-10,(pool,q,err_r)
            mt=pd.read_json(root/'medians.json',typ='series').reindex(STOCK)
            xx=g[STOCK].fillna(mt).to_numpy()
            t=tree.predict(xx,num_threads=1)
            err_t=np.abs(t-g['T']).max()
            assert err_t<1e-10,(pool,q,err_t)
            for fam in FAMILIES:
                subset=[i for i,c in enumerate(cols) if family(c)==fam]
                sd=np.array(cfg['sd']);mu=np.array(cfg['mean'])
                out['contribution_'+fam]=x[:,subset]@coef[subset]
                out['R_mask_'+fam]=rp-out['contribution_'+fam]+((med[subset]-mu[subset])/sd[subset])@coef[subset]
                ti=[j for j,c in enumerate(STOCK) if family(c)==fam]
                if ti:
                    v=xx.copy();v[:,ti]=mt.to_numpy()[ti]
                    out['T_mask_'+fam]=tree.predict(v,num_threads=1)
                else:out['T_mask_'+fam]=t
                splits.append((pool,str(q),fam,len(subset),len(ti),tree.feature_importance('split')[ti].sum(),tree.feature_importance('gain')[ti].sum(),int(np.isnan(orig[:,subset]).sum())))
            rec=out.filter(like='contribution_').sum(axis=1)+out.intercept
            err_sum=abs(rec-g.R).max()
            assert err_sum<1e-10
            checks.append((pool,str(q),len(g),err_r,err_t,err_sum))
            dest=OUT/('scores_'+pool);dest.mkdir(exist_ok=True)
            atomic_parquet(out,dest/f'{q}.parquet')
        print('A4',pool,len(checks),flush=True)
    pd.DataFrame(checks,columns='pool fold rows ridge_max_error tree_max_error family_sum_max_error'.split()).to_csv(OUT/'parity.csv',index=False)
    pd.DataFrame(splits,columns='pool fold family ridge_columns tree_columns splits gain missing_inputs'.split()).to_csv(OUT/'family_splits.csv',index=False)
if __name__=='__main__':main()
