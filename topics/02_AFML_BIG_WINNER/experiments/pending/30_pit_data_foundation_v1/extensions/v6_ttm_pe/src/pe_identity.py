"""Date-effective identities and provisional listing universe, inherited from V5."""
import numpy as np
import pandas as pd

class Identity:
    def __init__(self, root):
        self.inventory = pd.read_parquet(root / 'securities.parquet')
        continuous = pd.read_parquet(root / 'continuous_intervals.parquet').rename(
            columns={'valid_until_exclusive': 'valid_to'})
        bse = pd.read_parquet(root / 'bse_intervals.parquet').rename(
            columns={'historical_instrument': 'instrument'})
        cols = ['security_id', 'instrument', 'valid_from', 'valid_to']
        special = pd.concat([continuous[cols], bse[cols]], ignore_index=True)
        base = self.inventory.loc[~self.inventory.security_id.isin(special.security_id),
                                  ['security_id', 'instrument']].copy()
        base['valid_from'] = pd.NaT
        base['valid_to'] = pd.NaT
        self.intervals = pd.concat([base, special], ignore_index=True)
        for col in ['valid_from', 'valid_to']:
            self.intervals[col] = pd.to_datetime(self.intervals[col])

    def mapping(self, day):
        day = pd.Timestamp(day).normalize()
        a = self.intervals
        a = a[(a.valid_from.isna() | a.valid_from.le(day)) &
              (a.valid_to.isna() | a.valid_to.gt(day))].copy()
        if a.instrument.duplicated().any() or a.security_id.duplicated().any():
            raise ValueError('Ambiguous effective identity; no implicit winner allowed')
        return a[['security_id', 'instrument']]

    def universe(self, day):
        day = pd.Timestamp(day).normalize()
        f = self.inventory.copy()
        listing = pd.to_datetime(f.listing_date.where(~f.exchange.eq('BJ'), f.bse_listing_proxy))
        delisting = pd.to_datetime(f.delist_date)
        f = f[listing.le(day) & (delisting.isna() | delisting.gt(day)) & ~f.identity_date_conflict].copy()
        f = f.rename(columns={'instrument': 'canonical_instrument'})
        f = f.merge(self.mapping(day), on='security_id', how='left', validate='one_to_one')
        f['membership_quality'] = 'Historical-proxy'
        return f

def normalize(frame, day, receipt, identity, provider='baostock'):
    if provider == 'baostock':
        if frame.empty or not frame.date.eq(day).all() or not frame.adjustflag.eq('3').all():
            raise ValueError('Empty, wrong-date or adjusted daily source')
        f = frame[['date', 'code', 'peTTM']].copy()
        f['instrument'] = f.code.str[:2].str.upper() + f.code.str[3:]
        raw = pd.to_numeric(f.peTTM, errors='coerce')
    elif provider == 'eastmoney':
        if frame.empty or not pd.to_datetime(frame.TRADE_DATE).eq(pd.Timestamp(day)).all():
            raise ValueError('Empty or wrong-date daily source')
        f = pd.DataFrame({'date': pd.to_datetime(frame.TRADE_DATE),
                          'instrument': frame.SECUCODE.str[-2:]+frame.SECUCODE.str[:6]})
        raw = pd.to_numeric(frame.PE_TTM, errors='coerce')
    else:
        raise ValueError('Unsupported source')
    if f.instrument.duplicated().any():
        raise ValueError('Duplicate source security')
    finite = pd.Series(np.isfinite(raw), index=f.index)
    f['vendor_pe_ttm'] = raw.where(finite)
    f['pe_ttm'] = raw.where(finite & raw.gt(0))
    f['pe_status'] = np.select(
        [raw.isna(), ~finite, raw.eq(0), raw.lt(0)],
        ['MISSING', 'NONFINITE', 'ZERO_OR_UNDEFINED', 'NONPOSITIVE_EARNINGS_PROXY'],
        default='POSITIVE')
    f['date'] = pd.to_datetime(f.date)
    f['session_close'] = pd.Timestamp(day, tz='Asia/Shanghai') + pd.Timedelta(hours=15)
    f['source_observed_at'] = pd.Timestamp(receipt['observed_at'])
    f['ingested_at'] = pd.Timestamp(receipt['ingested_at'])
    f['known_at'] = pd.NaT
    f['quality_tier'] = 'Historical-proxy'
    f['provider'] = provider
    f['earnings_vintage_status'] = 'UNPROVEN'
    f['source_sha256'] = receipt['parquet_sha256']
    f['response_sha256'] = '|'.join(receipt['response_sha256'])
    f = f.drop(columns=['code', 'peTTM'],errors='ignore').rename(columns={'instrument':'provider_instrument'})
    mapping = identity.mapping(day)
    f = f.merge(mapping.rename(columns={'instrument':'provider_instrument'}), on='provider_instrument', how='left', validate='one_to_one')
    direct = f.security_id.notna()
    # The vendor retrospectively rewrites old rows using current security codes.
    # Permit only already-reviewed, unique stable-identity aliases; preserve that fact.
    aliases = identity.intervals[['instrument','security_id']].drop_duplicates()
    counts = aliases.groupby('instrument').security_id.nunique()
    aliases = aliases[aliases.instrument.isin(counts[counts.eq(1)].index)]
    fallback = f.provider_instrument.map(aliases.set_index('instrument').security_id)
    f['security_id'] = f.security_id.fillna(fallback)
    f['instrument'] = f.security_id.map(mapping.set_index('security_id').instrument)
    f['identity_status'] = np.select([direct,f.security_id.notna()],
        ['DATE_EFFECTIVE_CODE_PROXY','RETROSPECTIVE_VENDOR_CODE_MAPPED_BY_REVIEWED_ALIAS'],default='UNMAPPED')
    f['provider_aliases'] = f.provider_instrument
    f['alias_rows'] = 1
    f['alias_reconciliation'] = 'SINGLE_ROW'
    duplicated = f.security_id.notna() & f.security_id.duplicated(keep=False)
    if duplicated.any():
        reconciled = []
        for sid, group in f[duplicated].groupby('security_id',sort=True):
            # Prefer the actual historical code only when values agree. Keep every
            # raw source row in the sealed input; conflicting aliases yield no PE.
            group = group.assign(_direct=group.provider_instrument.eq(group.instrument)).sort_values('_direct',ascending=False)
            row = group.iloc[0].drop(labels='_direct').copy()
            row['provider_aliases'] = '|'.join(sorted(group.provider_instrument))
            row['alias_rows'] = len(group)
            if group.vendor_pe_ttm.nunique(dropna=False)==1 and group.pe_status.nunique()==1:
                row['alias_reconciliation'] = 'IDENTICAL_VALUES_DEDUPLICATED'
            else:
                row['vendor_pe_ttm'],row['pe_ttm'] = np.nan,np.nan
                row['pe_status'] = 'ALIAS_VALUE_CONFLICT'
                row['alias_reconciliation'] = 'CONFLICT_NORMALIZED_UNKNOWN'
            reconciled.append(row)
        f = pd.concat([f[~duplicated],pd.DataFrame(reconciled)],ignore_index=True)
    return f
