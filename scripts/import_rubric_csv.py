#!/usr/bin/env python3
"""
Fetch the AI Trust Stack CSV and generate a draft config/rubric.json.

This script applies simple heuristics to suggest `match_meta` keys from the attribute text.
Run it from the project root: python3 scripts/import_rubric_csv.py
"""
import csv
import io
import json
import os
import re
import urllib.request
from datetime import datetime

CSV_URL = "https://raw.githubusercontent.com/andrewdeutsch/authenticity-ratio/master/docs/AI_Trust_Stack_Master_Table.csv"
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
RUBRIC_PATH = os.path.join(PROJECT_ROOT, "config", "rubric.json")
BACKUP_PATH = RUBRIC_PATH + ".bak-" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def suggest_keys(attr_text: str):
    """Return a list of suggested meta keys derived from the attribute text."""
    t = attr_text.lower()
    # heuristics: pick words that look like keys, strip punctuation
    candidates = re.split(r"[\s/,-]+", t)
    # remove stopwords and short words
    stop = {"the", "and", "or", "if", "is", "a", "an", "of", "in", "on", "by", "with"}
    keys = []
    for c in candidates:
        c = re.sub(r"[^a-z0-9_]+", "", c)
        if len(c) < 3:
            continue
        if c in stop:
            continue
        keys.append(c)
    # return unique, preserve order
    seen = set()
    out = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:5]


def main():
    print("Fetching CSV...", end=" ")
    resp = urllib.request.urlopen(CSV_URL)
    s = resp.read().decode("utf-8")
    print("done")
    reader = csv.DictReader(io.StringIO(s))
    rows = list(reader)

    attrs = []
    for r in rows:
        attr = r.get("Attribute (Objective Signal)", "").strip()
        if not attr:
            continue
        suggested = suggest_keys(attr)
        entry = {
            "id": re.sub(r"[^a-z0-9_]+", "_", attr.lower()).strip("_ ")[:80],
            "label": attr,
            "match_meta": suggested,
            "effect": "bonus",
            "value": 0,
            "enabled": True,
            "source_row": r,
        }
        attrs.append(entry)

    # load existing rubric for base template
    if os.path.exists(RUBRIC_PATH):
        with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
            base = json.load(f)
    else:
        base = {
            "version": "1.0",
            "dimension_weights": {
                "provenance": 0.14705882352941177,
                "resonance": 0.17647058823529413,
                "coherence": 0.2647058823529412,
                "transparency": 0.16176470588235295,
                "verification": 0.25,
            },
            "thresholds": {"authentic": 75, "suspect": 40},
            "attributes": [],
            "defaults": {"max_total_bonus": 50, "max_total_penalty": -50, "normalize_weights": True},
        }

    # backup current rubric
    if os.path.exists(RUBRIC_PATH):
        print(f"Backing up existing rubric to {BACKUP_PATH}")
        with open(RUBRIC_PATH, "r", encoding="utf-8") as fr:
            with open(BACKUP_PATH, "w", encoding="utf-8") as fw:
                fw.write(fr.read())

    base["attributes"] = attrs
    with open(RUBRIC_PATH, "w", encoding="utf-8") as fw:
        json.dump(base, fw, indent=2, ensure_ascii=False)

    print(f"Wrote {len(attrs)} attribute entries to {RUBRIC_PATH}")


if __name__ == "__main__":
    main()
