"""Create Databricks secrets needed by the project."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace
import getpass


def main() -> None:
    w = WorkspaceClient()

    try:
        w.secrets.create_scope(scope="database")
    except Exception:
        pass

    w.secrets.put_secret(
        scope="database",
        key="lakebase_connection_string",
        string_value=getpass.getpass("Paste the Lakebase connection string: "),
    )
    w.secrets.put_acl(
        scope="database",
        principal="users",
        permission=workspace.AclPermission.READ,
    )


if __name__ == "__main__":
    main()
