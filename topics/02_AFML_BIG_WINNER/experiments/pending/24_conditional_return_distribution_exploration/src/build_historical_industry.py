"""As-published industry identity and contemporaneous historical-pool peer state."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import OUT,EP
from download_historical_industry import CACHE
from build_margin_information import digest
DEST=OUT/'r32_historical_industry'
SOURCE=OUT/'local_cache/historical_peer_panel.parquet'
POOL=OUT/'local_cache/improvement_panel.parquet'
PANEL=OUT/'local_cache/historical_industry_panel.parquet'
IDENTITY=['industry_id','industry_age_days','industry_stale']
STATE=['industry_mom21','industry_mom63','industry_mom126','industry_breadth63','industry_peer_count','industry_relative63']

def identity(pool,date,releases):
    eligible=[r for r in releases if pd.Timestamp(r['published'])<date]
    out=pool.copy();out['industry_id']='unknown';out['industry_sector']='unknown';out['industry_published']=pd.NaT
    out['industry_age_days']=np.nan;out['industry_stale']=np.nan
    if not eligible:return out
    item=max(eligible,key=lambda x:x['published']);mapping=pd.read_parquet(item['table_path']).set_index('code')
    era='legacy' if pd.Timestamp(item['published']).year<=2021 else 'revised'
    codes=out.instrument.str[2:];out['industry_id']=codes.map(mapping.major).map(lambda x:era+':'+x if pd.notna(x) else 'unknown')
    out['industry_sector']=codes.map(mapping.sector).fillna('unknown');out['industry_published']=pd.Timestamp(item['published'])
    out['industry_age_days']=(date-pd.Timestamp(item['published'])).days;out['industry_stale']=float(out.industry_age_days.iloc[0]>365)
    return out

def peer_state(frame):
    result=frame.copy()
    for c in STATE:result[c]=np.nan
    for name,g in result.groupby('industry_id'):
        if name=='unknown':continue
        for idx,row in g.iterrows():
            peers=g.drop(index=idx);result.loc[idx,'industry_peer_count']=len(peers)
            if len(peers)<5:continue
            for k in [21,63,126]:
                v=peers[f'mom{k}'].dropna()
                if len(v)>=5:result.loc[idx,f'industry_mom{k}']=v.median()
            v=peers.mom63.dropna()
            if len(v)>=5:result.loc[idx,'industry_breadth63']=v.gt(0).mean()
    result['industry_relative63']=result.mom63-result.industry_mom63
    return result

def build():
    DEST.mkdir(exist_ok=True)
    for name in ['download_manifest.json','discovery_receipt.json']:
        (DEST/('source_manifest.json' if name=='download_manifest.json' else name)).write_text((CACHE/name).read_text())
    releases=json.loads((CACHE/'parse_manifest.json').read_text());assert len(releases)==19
    for r in releases:
        assert digest(Path(r['table_path']))==r['table_sha256'] and digest(Path(r['pdf_path']))==r['pdf_sha256']
    source_audit=json.loads((OUT/'r25_historical_peers/feature_audit.json').read_text());assert digest(SOURCE)==source_audit['feature_sha256']
    panel=pd.read_parquet(SOURCE);pool=pd.read_parquet(POOL);chunks=[];prefixes=[]
    pool=pool[pool.date.isin(panel.date.unique())][['date','instrument','mom21','mom63','mom126']]
    for date,g in pool.groupby('date',sort=True):
        out=peer_state(identity(g,date,releases));chunks.append(out)
        if str(date.date()) in ['2019-01-31','2021-01-29','2023-01-31','2024-02-29','2026-04-30']:
            cut=[r for r in releases if pd.Timestamp(r['published'])<date]
            pd.testing.assert_frame_equal(out,peer_state(identity(g,date,cut)));prefixes.append(str(date.date()))
    features=pd.concat(chunks,ignore_index=True)
    columns=['date','instrument']+IDENTITY+STATE+['industry_sector','industry_published']
    result=panel.merge(features[columns],on=['date','instrument'],how='left',validate='one_to_one',sort=False)
    pd.testing.assert_frame_equal(result[panel.columns],panel)
    assert result.industry_id.notna().all() and result.industry_published.lt(result.date).all()
    result.to_parquet(PANEL,index=False)
    bymonth=result.groupby('date').agg(rows=('instrument','size'),known=('industry_id',lambda x:x.ne('unknown').sum()),
        state_coverage=('industry_mom63',lambda x:x.notna().mean()),age_days=('industry_age_days','first'),stale=('industry_stale','first'))
    bymonth['known_fraction']=bymonth.known/bymonth.rows;bymonth.to_csv(DEST/'coverage_by_month.csv')
    evaluation=result[result.date.ge('2021-01-01')]
    audit=dict(technical_feature_integrity_passed=True,feature_sha256=digest(PANEL),source_sha256=digest(SOURCE),pool_sha256=digest(POOL),
        plan_sha256=digest(EP/'notes/r32_historical_industry.md'),rows=len(result),evaluation_rows=len(evaluation),
        evaluation_known_fraction=float(evaluation.industry_id.ne('unknown').mean()),evaluation_state_fraction=float(evaluation.industry_mom63.notna().mean()),
        evaluation_stale_fraction=float(evaluation.industry_stale.mean()),max_publication_age_days=int(result.industry_age_days.max()),
        prefix_checks=prefixes,release_receipts=releases,download_manifest_sha256=digest(CACHE/'download_manifest.json'),
        limitation='Published historical documents on migrated current website, not independently archived original bytes. 2021-2023 release gap; old/new regimes separate; pool peers not all A shares.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k!='release_receipts'},indent=2),flush=True)

if __name__=='__main__':build()
