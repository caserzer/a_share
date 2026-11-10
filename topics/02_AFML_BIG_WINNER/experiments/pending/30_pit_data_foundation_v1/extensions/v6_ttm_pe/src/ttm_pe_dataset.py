"""Verified additive PE adapter; distinct module name for existing D2 consumers."""
import json
from pathlib import Path
import pandas as pd
import numpy as np
from pe_common import OUT, sha
from pe_identity import Identity
from pit import AsOfResult

PROVIDERS = ('eastmoney', 'baostock')
QUALITY = ('Historical-proxy','PIT-certified','PIT-reconstructed','UNKNOWN/BLOCKED')

class D2TTMPEDataset:
    def __init__(self, release=None):
        self.root = Path(release or json.loads((OUT/'release.json').read_text())['path'])
        complete = json.loads((self.root/'COMPLETE.json').read_text())
        if sha(self.root/'FULL_MANIFEST.json') != complete['full_manifest_sha256']:
            raise ValueError('Changed PE manifest')
        self.files = {r['relative_path']:r['sha256'] for r in json.loads((self.root/'FULL_MANIFEST.json').read_text())}
        for name in ('securities','continuous_intervals','bse_intervals','calendar'):
            self._verify(f'inputs/{name}.parquet')
        self.identity = Identity(self.root/'inputs')
        self.calendar = pd.DatetimeIndex(self._read('inputs/calendar.parquet').date).sort_values()
        self.inventory_observed_at = pd.Timestamp(complete['identity_snapshot_observed_at'])

    def _verify(self, name):
        path = self.root/name
        if name not in self.files or not path.exists() or sha(path) != self.files[name]:
            raise ValueError('Changed or missing PE release file: '+name)

    def _read(self, name):
        self._verify(name)
        return pd.read_parquet(self.root/name)

    @staticmethod
    def _time(value):
        t = pd.Timestamp(value)
        return t.tz_localize('Asia/Shanghai') if t.tzinfo is None else t.tz_convert('Asia/Shanghai')

    def session(self, decision_time):
        t = self._time(decision_time)
        day = t.tz_localize(None).normalize()
        if day < self.calendar.min() or day > self.calendar.max():
            return None
        close_passed = t >= t.normalize()+pd.Timedelta(hours=15)
        candidates = self.calendar[self.calendar <= day if close_passed else self.calendar < day]
        return candidates[-1] if len(candidates) else None

    def join_universe(self, universe, decision_time, *, quality_tier='PIT-reconstructed',
                      provider='eastmoney', mode='historical'):
        if provider not in PROVIDERS or mode not in ('historical','archived') or quality_tier not in QUALITY:
            raise ValueError('Invalid provider, mode or quality tier')
        if 'security_id' not in universe or universe.security_id.isna().any() or universe.security_id.duplicated().any():
            raise ValueError('Universe needs unique non-null stable security_id values')
        reserved = ['pe_ttm','vendor_pe_ttm','pe_status','pe_date','pe_provider','pe_quality_tier',
                    'source_observed_at','pe_ingested_at','pe_known_at','earnings_vintage_status',
                    'pe_source_sha256','pe_response_sha256','pe_session_close',
                    'pe_provider_instrument','pe_identity_status']
        if set(reserved)&set(universe.columns):
            raise ValueError('Refuse overwriting existing PE/provenance columns')
        f = universe.copy()
        day = self.session(decision_time)
        f['pe_ttm'],f['vendor_pe_ttm'] = np.nan,np.nan
        f['pe_date'] = day if day is not None else pd.NaT
        f['pe_provider'] = provider
        f['pe_quality_tier'] = 'UNKNOWN'
        f['pe_status'] = 'NO_EXACT_SESSION_DATA'
        f['pe_known_at'] = pd.NaT
        f['source_observed_at'] = pd.Series(pd.NaT,index=f.index,dtype='datetime64[ns, UTC]')
        f['pe_ingested_at'] = pd.Series(pd.NaT,index=f.index,dtype='datetime64[ns, UTC]')
        f['earnings_vintage_status'] = 'UNPROVEN'
        for name in ('pe_source_sha256','pe_response_sha256','pe_provider_instrument','pe_identity_status'):
            f[name] = None
        f['pe_session_close'] = self._time(day)+pd.Timedelta(hours=15) if day is not None else pd.NaT
        if quality_tier != 'Historical-proxy':
            f['pe_status'] = 'VENDOR_EARNINGS_VINTAGE_UNPROVEN'
            return f
        if day is None:
            f['pe_status'] = 'OUTSIDE_FROZEN_CALENDAR_OR_BEFORE_FIRST_CLOSE'
            return f
        name = f'normalized/{provider}/{day.date()}.parquet'
        if name not in self.files:
            return f
        v = self._read(name)
        v = v[v.security_id.notna()].copy()
        if v.security_id.duplicated().any():
            raise ValueError('Ambiguous daily PE identities')
        if mode == 'archived':
            t = self._time(decision_time)
            v = v[(v.source_observed_at <= t) & (v.ingested_at <= t)]
        fields = ['security_id','pe_ttm','vendor_pe_ttm','pe_status','quality_tier',
                  'source_observed_at','ingested_at','known_at','earnings_vintage_status',
                  'source_sha256','response_sha256','session_close','provider_instrument','identity_status']
        v = v[fields].rename(columns={'quality_tier':'pe_quality_tier', 'ingested_at':'pe_ingested_at',
            'known_at':'pe_known_at','source_sha256':'pe_source_sha256',
            'response_sha256':'pe_response_sha256','session_close':'pe_session_close',
            'provider_instrument':'pe_provider_instrument','identity_status':'pe_identity_status'})
        f = f.drop(columns=[c for c in v.columns if c in f.columns and c!='security_id'])
        f = f.merge(v,on='security_id',how='left',validate='one_to_one')
        f['pe_status'] = f.pe_status.fillna('NOT_YET_ARCHIVED' if mode=='archived' else 'NO_SECURITY_OBSERVATION')
        f['pe_quality_tier'] = f.pe_quality_tier.fillna('UNKNOWN')
        f['earnings_vintage_status'] = f.earnings_vintage_status.fillna('UNPROVEN')
        return f

    def universe_asof(self, decision_time, *, quality_tier='PIT-reconstructed', provider='eastmoney', mode='historical'):
        if provider not in PROVIDERS or mode not in ('historical','archived') or quality_tier not in QUALITY:
            raise ValueError('Invalid provider, mode or quality tier')
        t = self._time(decision_time)
        day = t.tz_localize(None).normalize()
        if day < self.calendar.min() or day > self.calendar.max():
            f = pd.DataFrame(columns=['security_id','instrument','pe_ttm'])
            f.attrs['population_status'] = 'OUTSIDE_FROZEN_CALENDAR'
            return f
        if quality_tier != 'Historical-proxy' or (mode=='archived' and t<self.inventory_observed_at):
            f = pd.DataFrame(columns=['security_id','instrument','pe_ttm'])
            f.attrs['population_status'] = 'BLOCKED_UNCERTIFIED_OR_NOT_YET_ARCHIVED_UNIVERSE'
            return f
        f = self.identity.universe(t.tz_localize(None).normalize())
        # Inventory source provenance is distinct from the valuation provenance.
        f = f.rename(columns={'source_sha256':'membership_source_sha256'})
        f = self.join_universe(f,t,quality_tier=quality_tier,provider=provider,mode=mode)
        f.attrs['population_status'] = 'PROVISIONAL_HISTORICAL_MEMBERSHIP_NOT_CERTIFIED_TRADABILITY'
        return f

    def get_asof(self, security, field, decision_time, *, quality_tier='PIT-reconstructed', provider='eastmoney', mode='historical'):
        if field not in ('pe_ttm','vendor_pe_ttm'):
            raise ValueError('Unsupported PE field')
        inv = self.identity.inventory
        ids = set(inv.loc[inv.security_id.eq(security),'security_id'])
        if not ids:
            day = self._time(decision_time).tz_localize(None).normalize()
            a = self.identity.mapping(day)
            ids = set(a.loc[a.instrument.eq(security),'security_id'])
        if len(ids)!=1:
            raise KeyError('Unknown or ambiguous date-effective security')
        f = self.join_universe(pd.DataFrame({'security_id':list(ids)}),decision_time,
            quality_tier=quality_tier,provider=provider,mode=mode)
        r = f.iloc[0]
        return AsOfResult(None if pd.isna(r[field]) else float(r[field]),
                         'UNKNOWN' if pd.isna(r[field]) else r.pe_quality_tier,
                         r.pe_status,tuple(f.to_dict('records')))
