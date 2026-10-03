"""How much of the relevant work do you find if you read papers in score order?

    uv run python evaluate_ranking.py v1 bm25

Every record is graded. There is no tuning, so there is no held-out split.
"""
import math
import sys

import pandas as pd

from utils import load_data, load_scores

SHARES = (0.05, 0.10, 0.20, 0.30, 0.50)
TARGET = 0.95  # Aim to find 95% of the relevant papers.


def ranked(d):
    """Highest score first. Records with no abstract go first: a person must read them.
    Ties break by id, so the order is the same on every run."""
    d = d.assign(score=d.score.fillna(float("inf")))
    return d.sort_values(["score", "id"], ascending=[False, True]).reset_index(drop=True)


def curve(d):
    d = ranked(d)
    n, total = len(d), int(d.label_included.sum())
    found = d.label_included.cumsum().to_numpy()
    reach = int((found >= TARGET * total).argmax()) + 1
    return {
        "n": n,
        "total": total,
        "recall": {s: found[math.ceil(n * s) - 1] / total for s in SHARES},
        "reach": reach,
        "wss": TARGET - reach / n,  # work saved over random order at 95% recall
    }


def main(tags):
    n_all = len(load_data())
    runs = {}
    for tag in tags:
        df = load_scores(tag)
        if len(df) < n_all:
            sys.exit(f"'{tag}' scores {len(df)} of {n_all} records. Finish the run (no --limit) first.")
        runs[tag] = df

    first = curve(runs[tags[0]])
    print(f"\n{first['n']} records, {first['total']} relevant")
    print("Recall after reading the top share of the ranked list (random order gets the share itself):")
    table = pd.DataFrame({tag: {f"{s:.0%}": round(curve(df)["recall"][s], 2) for s in SHARES} for tag, df in runs.items()})
    table["random"] = list(SHARES)
    print(table.to_string())

    print(f"\nReading to {TARGET:.0%} recall:")
    for tag, df in runs.items():
        c = curve(df)
        print(f"  {tag}: {c['reach']} of {c['n']} records ({c['reach'] / c['n']:.0%}), WSS@95 = {c['wss']:.2f}")
        missing = int(df.no_abstract.sum())
        if missing:
            print(f"    {missing} record(s) have no abstract and were put first.")

    for tag, df in runs.items():
        print(f"\n[{tag}] Relevant papers scored lowest:")
        for x in df[df.label_included == 1].nsmallest(10, "score").itertuples():
            print(f"  {x.score:.2f}  {x.title[:90]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: evaluate_ranking.py TAG [TAG ...]")
    main(sys.argv[1:])
