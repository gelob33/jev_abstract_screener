"""Score every abstract against the inclusion criteria and save results/scores_<tag>.csv.

    uv run python score_abstracts.py --scorer jev --tag v1 --limit 20
    uv run python score_abstracts.py --scorer bm25 --tag bm25

Resumable: ids already in the output file are skipped, and each row is flushed on write.
"""
import argparse
import csv
import os
import re
import time

import requests
from rank_bm25 import BM25Okapi

from utils import INCLUSION_CRITERIA, has_abstract, load_data, scores_path

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"  # pinned so the model cannot change mid-test
RETRY_WAITS = (1, 2, 4, 8, 16)


def paper_text(row):
    return f"Title: {row.title}\n\nAbstract: {row.abstract}"


def tokens(text):
    return re.findall(r"\w+", text.lower())


# A scorer factory takes the full dataset and the criteria, and returns row -> score.
def jev_scorer(df, criteria):
    headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}"}
    question = {
        "type": "noul",
        "instructions": "This study meets all of the inclusion criteria below.\n\n" + criteria,
    }

    def score(row):
        body = {"model": MODEL, "state": paper_text(row), "questions": {"include": question}}
        for wait in RETRY_WAITS:
            r = requests.post(URL, json=body, headers=headers, timeout=60)
            if r.status_code in (429, 529):  # rate limit or overload: back off
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["answers"]["include"]["noul"]
        raise RuntimeError("gave up after retries")

    return score


def bm25_scorer(df, criteria):
    """Free baseline: keyword match between the criteria and each abstract."""
    corpus = df[df.abstract.map(has_abstract)]
    bm25 = BM25Okapi([tokens(paper_text(r)) for r in corpus.itertuples()])
    by_id = dict(zip(corpus.id, bm25.get_scores(tokens(criteria))))
    return lambda row: by_id[row.id]


SCORERS = {"jev": jev_scorer, "bm25": bm25_scorer}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scorer", choices=SCORERS, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--limit", type=int, help="score a stratified sample of this size")
    args = ap.parse_args()

    df = load_data()
    criteria = INCLUSION_CRITERIA.read_text(encoding="utf-8").strip()
    score = SCORERS[args.scorer](df, criteria)

    todo = df
    if args.limit:  # equal numbers of included and excluded, so the smoke test shows both
        todo = df.groupby("label_included").sample(args.limit // 2, random_state=0)

    out = scores_path(args.tag)
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        with open(out, newline="", encoding="utf-8") as f:
            done = {int(r["id"]) for r in csv.DictReader(f)}

    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not done:
            w.writerow(["id", "score", "no_abstract"])
        for n, row in enumerate(todo.itertuples(), 1):
            if row.id in done:
                continue
            missing = not has_abstract(row.abstract)
            w.writerow([row.id, "" if missing else score(row), missing])
            f.flush()
            if n % 50 == 0:
                print(n, "of", len(todo))
    print("saved", out)


if __name__ == "__main__":
    main()
