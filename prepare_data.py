"""Export SYNERGY's Jeyaraman_2020 review to data/jeyaraman.csv.

Jeyaraman_2020 only exists in the classic SYNERGY set (v1.0), not SYNERGY+, and the
classic data stores abstracts in `abstract_inverted_index` (exposed as
`abstract_original`), not the `_cleaned` field the default `abstract` var reads.
"""
import os

# Must be set before importing synergy_dataset, which reads it at import time.
os.environ["SYNERGY_SET"] = "classic"

from pathlib import Path

from synergy_dataset import Dataset
from synergy_dataset.base import download_raw_subset

from utils import DATA

NAME = "Jeyaraman_2020"

if not Path("~/.synergy_dataset_source/synergy-dataset-1.0", NAME).expanduser().exists():
    download_raw_subset(NAME, version="1.0")

df = (
    Dataset(NAME)
    .to_frame(vars=["title", "abstract_original"])
    .rename(columns={"abstract_original": "abstract"})
)
df.insert(0, "id", range(len(df)))

DATA.parent.mkdir(exist_ok=True)
df.to_csv(DATA, index=False, encoding="utf-8")
print(f"{len(df)} records, {int(df.label_included.sum())} included -> {DATA}")
