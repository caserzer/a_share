"""R34 exact-key union of audited input families, preserving every original row."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_panel import EP,OUT
from build_margin_information import digest,INDIVIDUAL,MARKET as MARGIN_MARKET
from build_price_volume_features import ACTIVITY as PRICE_ACTIVITY,PATH as PRICE_PATH
from build_historical_peers import PEER0,PEER63
from build_global_risk import RISK,MACRO as GLOBAL_MACRO
from build_financial_quality import GROUPS as FINANCIAL
from build_historical_industry import IDENTITY,STATE
from build_domestic_macro import ACTIVITY as DOMESTIC_ACTIVITY,CREDIT
from run_historical_peer_models import CONTROL
DEST=OUT/'r34_joint_information'
SOURCE=OUT/'local_cache/historical_peer_panel.parquet'
PANEL=OUT/'local_cache/joint_information_panel.parquet'
FAMILIES={'price_path':PRICE_ACTIVITY+PRICE_PATH,'linked_peers':PEER0+PEER63,'margin':INDIVIDUAL+MARGIN_MARKET,
          'global':RISK+GLOBAL_MACRO,'financial':FINANCIAL['changes'],'industry':IDENTITY+STATE,'domestic':DOMESTIC_ACTIVITY+CREDIT}
ADDED=sum(FAMILIES.values(),[])
FULL=CONTROL+ADDED
SOURCES={'margin':('margin_information_panel.parquet','r27_margin_information'),
         'global':('global_risk_panel.parquet','r29_global_risk'),
         'financial':('financial_quality_panel.parquet','r31_financial_quality'),
         'industry':('historical_industry_panel.parquet','r32_historical_industry'),
         'domestic':('domestic_macro_panel.parquet','r33_domestic_macro')}


def attach(original,source,columns):
    keys=['date','instrument']
    assert not source.duplicated(keys).any() and not original.duplicated(keys).any()
    assert not set(columns)&set(original.columns)
    # A left join alone can conceal missing rows: enforce exact membership first.
    assert len(source)==len(original)
    left=pd.MultiIndex.from_frame(original[keys]);right=pd.MultiIndex.from_frame(source[keys]);assert set(left)==set(right)
    result=original.merge(source[keys+columns],on=keys,how='left',sort=False,validate='one_to_one')
    pd.testing.assert_frame_equal(result[original.columns],original)
    return result


def build():
    DEST.mkdir(exist_ok=True)
    source_audit=OUT/'r25_historical_peers/feature_audit.json';fa=json.loads(source_audit.read_text());assert digest(SOURCE)==fa['feature_sha256']
    integrity=json.loads((OUT/'r25_historical_peers/feature_integrity_audit.json').read_text());assert integrity['technical_feature_integrity_passed']
    original=pd.read_parquet(SOURCE);result=original.copy();receipts=[]
    assert len(CONTROL)==38 and len(FULL)==131 and len(set(FULL))==len(FULL)
    assert set(FAMILIES['price_path']+FAMILIES['linked_peers']).issubset(result.columns)
    for name,(filename,folder) in SOURCES.items():
        path=OUT/'local_cache'/filename;ap=OUT/folder/'feature_audit.json';audit=json.loads(ap.read_text())
        assert audit['technical_feature_integrity_passed'] and digest(path)==audit['feature_sha256']
        assert audit['source_sha256']==digest(SOURCE)
        source=pd.read_parquet(path)
        pd.testing.assert_frame_equal(source[original.columns],original)
        result=attach(result,source,FAMILIES[name])
        receipts.append(dict(family=name,path=str(path),sha256=digest(path),audit_path=str(ap),audit_sha256=digest(ap),columns=FAMILIES[name]))
    pd.testing.assert_frame_equal(result[original.columns],original)
    assert result.industry_id.map(lambda x:isinstance(x,str)).all()
    assert not np.isinf(result[[c for c in FULL if c!='industry_id']]).any().any()
    assert not any(c.startswith(('y_','end_','target_')) for c in FULL)
    result.to_parquet(PANEL,index=False)
    coverage=result.assign(period=np.where(result.date.ge('2021-01-01'),'evaluation','training')).groupby('period')[FULL].agg(lambda x:x.notna().mean())
    coverage.to_csv(DEST/'feature_coverage.csv')
    audit=dict(technical_feature_integrity_passed=True,source_sha256=digest(SOURCE),feature_sha256=digest(PANEL),
        source_audit_sha256=digest(source_audit),plan_sha256=digest(EP/'notes/r34_joint_information.md'),
        rows=len(result),evaluation_rows=int(result.date.ge('2021-01-01').sum()),features=len(FULL),control_features=CONTROL,added_families=FAMILIES,
        all_source_columns_and_population_unchanged=True,source_receipts=receipts,
        limitation='Inherits every source time, vintage, publication-gap, missing-data and population limitation. No new original vintage certification.')
    (DEST/'feature_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k not in ['source_receipts','control_features','added_families']},indent=2))

if __name__=='__main__':build()
