"""Explicit per-field temporal quality, including audit-only future metadata."""
import pandas as pd
import pyarrow.parquet as pq

from common import OUT, cache
from baselines import CONTROLS


def main():
    path=next((cache()/'data').glob('features_*.parquet'))
    fields=pq.read_schema(path).names+['market_mom20','market_rv20','market_return','turnover_percentile','high_turnover','low_eff','momentum_turnover','high_turnover_low_eff','size_group','liquidity_group']
    formulas={
        'atr':'MA20(turnover_rate)/MA250(turnover_rate)',
        'mavd':'MA21(volume)/MA200(volume)-1',
        'mavd_turnover':'MA21(turnover_rate)/MA200(turnover_rate)-1',
        'relative_volume':'volume/MA20(volume)',
        'abnormal_volume':'log(relative_volume)',
        'relative_turnover':'turnover_rate/MA20(turnover_rate)',
        'turnover20':'MA20(turnover_rate)',
        'eff':'abs(raw_close-raw_open)/max(raw_high-raw_low,epsilon)',
        'trend_decay':'max(mom20,0)*max(-OLS_slope_20(log(turnover_rate)),0)',
        'momentum_turnover':'mom60*ECDF_train(turnover20)',
        'high_turnover_low_eff':'I(relative_turnover>=train_q80)*I(eff<=train_q20)',
        'breakthrough_strength':'qfq_close/max(qfq_close[t-120:t])-1; excludes t',
        'log_float_cap_proxy':'log(raw_close*volume/turnover_rate); units and float shares unverified',
        'feature_start':'t0 minus 249 market sessions; insufficient_history separately masked',
        'known_at':'assumed t0 daily bar complete at 15:00, not first-vintage certification',
        'market_mom20':'sum observed mom20 / count jointly valid observed mom20 and rv20; availability-normalized proxy',
        'market_rv20':'sum observed rv20 / count jointly valid observed mom20 and rv20; availability-normalized proxy',
        'market_return':'mean observed daily log return among contemporaneously eligible identities',
        'provider_disagreement':'future retrospective provider audit flag; never a predictor',
        'is_delisted':'future retrospective inventory flag; never a predictor',
        'vendor_st':'contemporaneous vendor row flag only; no lifetime exclusion',
        'vendor_suspended':'contemporaneous vendor row status only; no actual tradability certification',
        'size_group':'training q1/3,q2/3 of log float cap proxy',
        'liquidity_group':'training q1/3,q2/3 of log money',
    }
    train_only={'turnover_percentile','high_turnover','low_eff','momentum_turnover','high_turnover_low_eff','size_group','liquidity_group'}
    audit_only={'is_delisted','provider_disagreement'}
    predictors=set(CONTROLS)|{'atr','mavd','momentum_turnover','abnormal_volume','high_turnover_low_eff','relative_volume','trend_decay'}
    rows=[]
    for field in sorted(set(fields)):
        if field.startswith('mom') and field[3:].isdigit():formula='qfq_close/qfq_close.shift('+field[3:]+')-1'
        elif field.startswith('rv') and field[2:].isdigit():formula='mean past '+field[2:]+' daily squared log close ratios'
        else:formula=formulas.get(field,'causal sealed daily-row transform or administrative field; see volume_price_features.py')
        rows.append(dict(field=field,quality='UNKNOWN_AT_T0_AUDIT_ONLY' if field in audit_only else 'Historical-proxy',
                         availability='TRAIN_ONLY_BEFORE_FIT_CUTOFF' if field in train_only else 'AUDIT_ONLY_NEVER_PREDICTOR' if field in audit_only else 'T0_DAILY_CLOSE_ASSUMED',
                         used_as_predictor=field in predictors,source='EP30 sealed raw/qfq bars and identity; train-only fitted boundaries where stated',formula=formula))
    pd.DataFrame(rows).to_csv(OUT/'audits/feature_field_lineage.csv',index=False)
    from ep30_adapter import EP30Adapter
    a=EP30Adapter();sources=[]
    for s in a.inventory.itertuples():
        name=f'normalized/prices_qfq/{s.security_id}.parquet'
        raw=next((n for n in [f'inputs/normalized/prices/{s.security_id}.parquet',f'inputs/inputs/baseline/normalized/prices/{s.security_id}.parquet'] if n in a.files),None)
        sources.append(dict(security_id=s.security_id,qfq_relative_path=name if name in a.files else None,
                            qfq_source_sha256=a.files[name]['sha256'] if name in a.files else None,
                            raw_relative_path=raw,raw_source_sha256=a.files[raw]['sha256'] if raw else None,
                            root_manifest_sha256=a.root.name,quality='Historical-proxy'))
    pd.DataFrame(sources).to_csv(OUT/'audits/security_source_lineage.csv',index=False)


if __name__=='__main__':main()
