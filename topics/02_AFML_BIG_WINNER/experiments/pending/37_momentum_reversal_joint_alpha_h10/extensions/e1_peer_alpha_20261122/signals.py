"""Construct dated signals from frozen E1 predictions and backward-looking inputs."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EP = ROOT.parents[1]
sys.path.insert(0, str(EP / 'code'))
from core import PRIVATE, assign_deciles, dump, sha

OUT = ROOT / 'results'
PRED = EP / 'extensions/original78_rankic_20261118/local_cache/predictions.parquet'


def sectors(days, symbols):
    table = pd.read_parquet(PRIVATE / 'industry.parquet')
    codes = sorted(table.l1_code.dropna().unique())
    ids = {name: i for i, name in enumerate(codes)}
    panel = np.full((len(days), len(symbols)), -1, dtype=int)
    for row in table.itertuples():
        s = row.ts_code[-2:] + row.ts_code[:6]
        if s not in symbols or pd.isna(row.in_date):
            continue
        start = days.searchsorted(pd.Timestamp(row.in_date))
        end = len(days) if pd.isna(row.out_date) else days.searchsorted(pd.Timestamp(row.out_date))
        view = panel[start:end, symbols.get_loc(s)]
        code = ids.get(row.l1_code, -2)
        view[:] = np.where((view == -1) | (view == code), code, -2)
    return panel, codes


def panels(r, industry, members, money):
    peers = np.full_like(r, np.nan)
    leaders = np.full_like(r, np.nan)
    is_leader = np.zeros_like(r, dtype=bool)
    for t in range(len(r)):
        classified = members[t] & (industry[t] >= 0)
        for group in np.unique(industry[t, classified]):
            idx = np.flatnonzero(classified & (industry[t] == group))
            if len(idx) < 5:
                continue
            vals = r[t, idx]
            count = np.isfinite(vals).sum() - np.isfinite(vals).astype(int)
            peers[t, idx] = np.divide(np.nansum(vals) - np.nan_to_num(vals), count,
                                      out=np.full(len(idx), np.nan), where=count >= 4)
            eligible = idx[np.isfinite(money[t, idx])]
            if len(eligible) < 3:
                continue
            top = eligible[np.argsort(-money[t, eligible], kind='stable')[:3]]
            is_leader[t, top] = True
            leaders[t, idx] = r[t, top].mean()
    return peers, leaders, is_leader


def regress(X, y, valid):
    ok = valid & np.isfinite(X).all(axis=1) & np.isfinite(y)
    if ok.sum() < 80:
        return None
    beta, _, rank, _ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
    return beta if rank == X.shape[1] else None


def build():
    source_names = ['qfq_close', 'daily_members', 'money', 'market', 'turnover_rate', 'industry',
                    'qfq_open', 'open', 'opening_trade_status_v2', 'limits/daily', 'suspensions/daily']
    inputs = [PRIVATE / (name + '.parquet') for name in source_names]
    inputs += [PRED, ROOT / 'PROTOCOL.md', Path(__file__), ROOT / 'matching.py', ROOT / 'evaluate.py',
               EP / 'code/core.py', EP / 'code/accounts.py', EP / 'config.yaml']
    dump(OUT / 'inputs.json', {str(p.relative_to(EP.parent)): sha(p) for p in inputs})
    close = pd.read_parquet(PRIVATE / 'qfq_close.parquet').sort_index()
    days, symbols = close.index, close.columns
    def read(name):
        return pd.read_parquet(PRIVATE / (name + '.parquet')).reindex_like(close)
    daily = close.pct_change(fill_method=None)
    r = daily.to_numpy()
    market = pd.read_parquet(PRIVATE / 'market.parquet').close.reindex(days).pct_change(fill_method=None).to_numpy()
    members = read('daily_members').eq(True).to_numpy()
    money = read('money').rolling(20, min_periods=16).mean().shift().to_numpy()
    turn = read('turnover_rate')
    normal = turn.rolling(20, min_periods=16).median().shift()
    rel = turn.div(normal.where(normal > 0)).where(turn > 0).to_numpy()
    industry, codes = sectors(days, symbols)
    peers, leaders, is_leader = panels(r, industry, members, money)
    predictions = pd.read_parquet(PRED).sort_values(['signal_date','instrument'])
    output = []
    for date, group in predictions.groupby('signal_date'):
        t = days.get_loc(date)
        group = group.copy()
        group['decile'] = assign_deciles(group, 'E1_78')
        properties = []
        hist = np.arange(t - 139, t - 19)
        obs = np.arange(t - 19, t + 1)
        window = np.arange(t - 4, t + 1)
        for s in group.instrument:
            j = symbols.get_loc(s)
            k = industry[t, j]
            d = {'industry': codes[k] if k >= 0 else None}
            properties.append(d)
            if not members[t, j] or k < 0:
                continue
            same = (industry[:, j] == k) & members[:, j]
            y = r[:, j]
            p = peers[:, j]
            lead = leaders[:, j]
            rs = y[obs]
            if np.isfinite(rs).all():
                d.update(mom5=close.iat[t,j]/close.iat[t-5,j]-1,
                         mom20=close.iat[t,j]/close.iat[t-20,j]-1, vol=rs.std(ddof=1))
            X = np.column_stack((np.ones(140),market[t-139:t+1],(p-market)[t-139:t+1]))
            b = regress(X[:120], y[hist], same[hist])
            if b is not None:
                err = rs - X[120:] @ b
                ok = same[obs] & np.isfinite(err)
                down = ok & (p[obs] < 0)
                if ok.sum() >= 16 and down.sum() >= 5 and (ok & ~down).sum() >= 3:
                    d.update(H1=err[down].mean(), ordinary=err[ok].mean())
            follower = same & ~is_leader[:,j]
            if (follower[window] & follower[window-1]).all():
                lead5 = np.prod(1 + lead[window]) - 1
                stock5 = np.prod(1 + y[window]) - 1
                excess5 = lead5 - (np.prod(1 + market[window]) - 1)
                if excess5 > 0 and lead5 > stock5:
                    X2 = np.column_stack((np.ones(120),market[hist],lead[hist]-market[hist],
                                          y[hist-1],market[hist-1],lead[hist-1]-market[hist-1]))
                    b2 = regress(X2,y[hist],follower[hist] & follower[hist-1])
                    if b2 is not None:
                        d.update(H2=b2[-1]*excess5, lag_gap=lead5-stock5)
            ratio = rel[t-9:t+1,j]
            ret10 = np.prod(1 + y[t-9:t+1])-1
            if same[t-9:t+1].all() and ret10 < 0 and np.isfinite(ratio).all() and ratio[-5:].mean() >= 1:
                down_move = np.maximum(-y[t-9:t+1],0)
                impact = down_move / ratio
                d.update(H3=impact[:5].mean()-impact[-5:].mean(),
                         plain=down_move[:5].mean()-down_move[-5:].mean(),
                         ret10=ret10, turn5=ratio[-5:].mean())
        output.append(pd.concat([group.reset_index(drop=True),pd.DataFrame(properties)],axis=1))
    result = pd.concat(output,ignore_index=True)
    assert not result.duplicated(['signal_date','instrument']).any()
    result.to_parquet(OUT / 'signals.parquet',index=False)


if __name__ == '__main__':
    build()
