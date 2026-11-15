"""Causal feature regeneration from daily basket prefixes; no label computation."""
import pandas as pd
from common import *
from build_panel import price_features
from inference_bundle_r101 import INPUT,capture
from versioned_observations import verify_bundle,source_copy

DAILY=KEY+['date','block','nav','coverage','members','breadth21','breadth63']

def regenerate(daily,market,cutoff):
    cutoff=pd.Timestamp(cutoff)
    if daily.duplicated(KEY+['date']).any():raise ValueError('duplicate daily identity')
    if not market.index.is_unique:raise ValueError('duplicate benchmark date')
    daily=daily[daily.date.le(cutoff)].copy();market=market.loc[market.index<=cutoff].sort_index()
    if not daily.date.isin(market.index).all():raise ValueError('basket date absent from benchmark')
    calendar=pd.Series(market.index,index=market.index)
    ends=calendar.groupby(calendar.index.to_period('M')).max()
    ends=ends[[p.end_time.normalize()<=cutoff for p in ends.index]]
    parts=[]
    for _,g in daily.groupby(KEY+['block'],sort=False):
        f=price_features(g);b=f.date.map(market)
        for h in [20,60]:f[f'past_excess{h}']=f[f'mom{h}']-(b/b.shift(h)-1)
        f['price_ready']=f[['mom20','mom60','vol20','dd60']].notna().all(axis=1)&f.coverage.ge(.8)&f.members.ge(5)
        parts.append(f.loc[f.date.isin(ends.values),INPUT])
    return pd.concat(parts,ignore_index=True).sort_values(KEY+['date']).reset_index(drop=True) if parts else pd.DataFrame(columns=INPUT)

def run():
    out=ROOT/'outputs/r102';out.mkdir(exist_ok=True)
    inputs=[CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
    daily=pd.concat([pd.read_parquet(p,columns=DAILY) for p in inputs[:2]],ignore_index=True)
    daily=daily[daily.era.eq('SW2021')];market=pd.read_parquet(inputs[2]).close
    reads={str(p):sha(p) for p in inputs+[Path(__file__),ROOT/'src/build_panel.py',ROOT/'protocols/r102.json']}
    archive=ROOT/'data/feature_store_r102';archive.mkdir(exist_ok=True)
    bundles=[]
    for cutoff in json.loads((ROOT/'protocols/r102.json').read_text())['cutoffs']:
        prefix=daily[daily.date.le(cutoff)];benchmark=market.loc[:cutoff]
        dp=archive/f'daily_{cutoff}.parquet';bp=archive/f'benchmark_{cutoff}.parquet'
        prefix.to_parquet(dp,index=False);benchmark.to_frame('close').to_parquet(bp)
        archived={k:source_copy(p,archive) for k,p in [('daily',dp),('benchmark',bp),('code',Path(__file__)),('price_features_code',ROOT/'src/build_panel.py')]}
        frame=regenerate(prefix,benchmark,cutoff)
        fp=out/f'features_{cutoff}.parquet';frame.to_parquet(fp,index=False)
        exact=frame[frame.date.eq(cutoff)].reset_index(drop=True)
        ep=out/f'exact_{cutoff}.parquet';exact.to_parquet(ep,index=False)
        provenance=out/f'provenance_{cutoff}.json'
        js(provenance,dict(cutoff=cutoff,reads=reads,archived=archived,daily_prefix_rows=len(prefix),benchmark_prefix_rows=len(benchmark),latest_completed_snapshot=str(frame.date.max().date()),exact_date_rows=len(exact),quality='Historical-proxy daily baskets, no labels read'))
        bundle=capture(ROOT/'data/inference_store_r102',cutoff,ep,ROOT/'outputs/universe_current.csv',[ROOT/f'outputs/{r}/fold_ledger.csv' for r in ['r02','r16']],[ROOT/f'outputs/{r}/model_parameters.json' for r in ['r02','r16']],provenance)
        m=verify_bundle(bundle)
        bundles.append(dict(cutoff=cutoff,path=str(bundle),manifest_sha256=sha(bundle/'manifest.json'),feature_sha256=sha(fp),rows=len(frame),exact_rows=len(exact),formal_rows=m['formal_rows']))
    js(out/'bundles.json',bundles);print(bundles)

if __name__=='__main__':run()
