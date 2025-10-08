"""Generate a CSV manifest mapping run_id -> s3 paths for normalized and scores tables.

Usage:
  python tools/run_manifest.py --output ./output/run_manifest.csv

This is read-only: it queries Athena and writes a CSV manifest.
"""

import argparse
import os
from datetime import datetime
import pandas as pd

from data.athena_client import AthenaClient


QUERY_TEMPLATE = """
SELECT run_id, brand_id, source, "$path" AS s3_path, COUNT(*) AS rows_in_file
FROM {table}
WHERE run_id IS NOT NULL
GROUP BY run_id, brand_id, source, "$path"
ORDER BY brand_id, source, run_id
"""


def generate_manifest(output_path: str):
    client = AthenaClient()

    tables = [
        ("ar_mvp.ar_content_normalized_v2", "normalized"),
        ("ar_mvp.ar_content_scores_v2", "scores"),
    ]

    rows = []
    for table, table_label in tables:
        q = QUERY_TEMPLATE.format(table=table)
        exec_id = client.execute_query(q)
        df = client.get_query_results(exec_id)
        if df is None or df.empty:
            continue
        df = df.rename(columns={"s3_path": "s3_path", "rows_in_file": "rows_in_file"})
        df["table"] = table_label
        rows.append(df)

    if not rows:
        print("No runs found in either table.")
        return

    out_df = pd.concat(rows, ignore_index=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out_df.to_csv(output_path, index=False)
    print(f"Wrote manifest with {len(out_df)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default=f"output/run_manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    args = parser.parse_args()
    generate_manifest(args.output)


if __name__ == '__main__':
    main()
