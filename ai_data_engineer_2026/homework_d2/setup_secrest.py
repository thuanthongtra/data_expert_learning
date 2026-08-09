"""
One-time setup script: creates a Databricks secret scope and stores the
Lakebase connection string.

Run this locally with Databricks CLI/configured workspace access, or from a
notebook. Never commit the secret value anywhere.

Usage:
    python setup_secrest.py
"""

import getpass

from databricks.sdk import WorkspaceClient


SCOPE = "database"
KEY = "lakebase_connection_string"


def main() -> None:
    w = WorkspaceClient()

    try:
        w.secrets.create_scope(scope=SCOPE)
    except Exception:
        pass

    w.secrets.put_secret(
        scope=SCOPE,
        key=KEY,
        string_value=getpass.getpass("Paste your Lakebase connection string: "),
    )


if __name__ == "__main__":
    main()
