"""Deploy Athena views defined in SQL files under /sql

Usage:
  python tools/create_views.py
"""

import glob
import os
from data.athena_client import AthenaClient


def deploy_views(sql_dir: str = "sql"):
    client = AthenaClient()
    sql_files = glob.glob(os.path.join(sql_dir, "*.sql"))
    for sql_file in sql_files:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        print(f"Deploying {sql_file}...")
        client.execute_query(sql)
    print("Done deploying views.")


if __name__ == '__main__':
    deploy_views()
