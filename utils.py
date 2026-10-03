"""Paths and loaders shared by every script, so file formats are defined once."""
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATA = Path("data/jeyaraman.csv")  # id, title, abstract, label_included
RESULTS = Path("results")
INCLUSION_CRITERIA = Path("inclusion_criteria.md")


def load_data():
    return pd.read_csv(DATA)


def has_abstract(abstract):
    return isinstance(abstract, str) and abstract.strip() != ""


def scores_path(tag):
    return RESULTS / f"scores_{tag}.csv"  # id, score, no_abstract


def load_scores(tag):
    """Scores for one run, joined to the labels."""
    labels = load_data()[["id", "title", "label_included"]]
    return pd.read_csv(scores_path(tag)).merge(labels, on="id")
