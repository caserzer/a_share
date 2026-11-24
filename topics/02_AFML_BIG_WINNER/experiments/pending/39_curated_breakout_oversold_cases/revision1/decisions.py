"""Build the prespecified fixed-seat overlay using signal-close information only."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EP = HERE.parent
OUT = HERE / "results/decisions"
KEY = ["pool", "signal_date", "instrument"]
DAY = KEY[:2]
SEEDS = (39, 139, 239, 339, 439)
FITS = ["natural", "hard", *(f"random_{s}" for s in SEEDS)]
MODELS = ["full", *FITS, "legacy_local", *(f"shuffle_{s}" for s in SEEDS)]


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def source():
    panel_path = EP/"results/panel.parquet"
    risk_path = HERE/"results/fit/scores.parquet"
    old_path = EP/"results/training_fit/scores.parquet"
    panel = pd.read_parquet(panel_path, columns=KEY+["scope", "selected", "oversold", "score"])
    predictions = pd.read_parquet(risk_path, columns=KEY+["model", "loss_prob"])
    assert set(predictions.model.unique()) == set(FITS)
    risk = predictions.pivot(index=KEY, columns="model", values="loss_prob")
    assert risk.index.sort_values().equals(panel[panel.oversold.eq(True)].set_index(KEY).index.sort_values())
    assert np.isfinite(risk.to_numpy()).all() and risk.min().min()>=0 and risk.max().max()<=1
    old = pd.read_parquet(old_path, columns=KEY+["score"], filters=[("model","=","oversold_curated")])
    assert len(old)==len(panel)
    p = panel.merge(risk.reset_index(), on=KEY, how="left", validate="1:1").merge(
        old.rename(columns={"score":"old_score"}), on=KEY, validate="1:1")
    assert len(p)==len(panel) and p.old_score.notna().all()
    return p, [panel_path, risk_path, old_path]


def choose(model, review, count, pool, date):
    if model == "full" or count == 0:
        return review.iloc[:0]
    if model.startswith("shuffle_"):
        seed = int(model.split("_")[-1])
        rng = np.random.default_rng([seed, int(pool[3:]), int(date.strftime("%Y%m%d"))])
        ordered = review.sort_values("instrument")
        return ordered.iloc[rng.permutation(len(ordered))[:count]]
    risk = "old_score" if model == "legacy_local" else model
    return review.sort_values([risk, "instrument"], ascending=[model == "legacy_local", True]).iloc[:count]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, paths = source()
    scores, actions, days = [], [], []
    for (pool, date), g in data.groupby(DAY):
        g = g.sort_values(["score","instrument"], ascending=False).reset_index(drop=True)
        seats = len(g)//10
        assert g.selected.tolist() == [True]*seats+[False]*(len(g)-seats)
        review = g[g.selected & g.oversold.eq(True)]
        reserve = g[~g.selected & g.oversold.eq(False)]
        triggered = int(review.natural.gt(.5).sum())
        count = min(triggered, len(reserve))
        candidates = reserve.iloc[:count]
        scope = g.scope.iloc[0]
        for model in MODELS:
            dropped = choose(model, review, count, pool, date)
            n = len(dropped)
            added = candidates.iloc[:n]
            picks = g.selected.copy()
            picks.loc[dropped.index] = False
            picks.loc[added.index] = True
            assert picks.sum() == seats
            assert picks[g.selected & ~g.oversold.eq(True)].all()
            if model == "natural":
                assert dropped.natural.gt(.5).all()
            valid = g.index[picks]
            coded = g.score if model == "full" else len(g)-g.index.to_numpy()+len(g)*picks.to_numpy()
            result = g[KEY].assign(model=model, score=coded)
            assert set(result.nlargest(seats, "score").index) == set(valid) or model == "full"
            scores.append(result)
            for pos, (v, a) in enumerate(zip(dropped.itertuples(), added.itertuples()), start=1):
                actions.append(dict(pool=pool, scope=scope, signal_date=date, model=model, slot=pos,
                    outgoing=v.instrument, incoming=a.instrument, orig_rank_out=v.Index+1, orig_rank_in=a.Index+1,
                    natural_loss_prob=v.natural, full_score_out=v.score, full_score_in=a.score))
            days.append(dict(pool=pool, scope=scope, signal_date=date, model=model, eligible=len(g), seats=seats,
                review=len(review), above_threshold=triggered, reserve=len(reserve), changed=n))
    plans = pd.concat(scores, ignore_index=True)
    # Consumers can open the complete score file as soon as the final rename succeeds.
    pd.DataFrame(days).to_csv(OUT/"dates.csv", index=False)
    pd.DataFrame(actions).to_parquet(OUT/"swaps.parquet", index=False)
    tmp = OUT/"planned.partial.parquet"
    plans.to_parquet(tmp, index=False)
    tmp.replace(OUT/"planned.parquet")
    pathlist = [*paths, Path(__file__), HERE/"PROTOCOL.md", OUT/"planned.parquet", OUT/"dates.csv", OUT/"swaps.parquet"]
    (OUT/"receipt.json").write_text(json.dumps(dict(rows=len(plans), models=MODELS,
        hashes={str(p):digest(p) for p in pathlist}),indent=2)+"\n")


if __name__ == "__main__":
    main()

