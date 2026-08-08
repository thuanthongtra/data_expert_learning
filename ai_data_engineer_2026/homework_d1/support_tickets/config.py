import os

from psycopg.conninfo import conninfo_to_dict, make_conninfo


DEFAULT_SECRET_KEY = "lakebase_connection_string"


def get_secret_key_name() -> str:
    return os.getenv("LAKEBASE_SECRET_KEY", DEFAULT_SECRET_KEY)


def get_connection_string() -> str:
    secret_key = get_secret_key_name()

    for env_name in ("LAKEBASE_CONNECTION_STRING", secret_key):
        direct = os.getenv(env_name)
        if direct:
            return direct

    try:
        import streamlit as st

        if secret_key in st.secrets:
            return str(st.secrets[secret_key])
        if "LAKEBASE_CONNECTION_STRING" in st.secrets:
            return str(st.secrets["LAKEBASE_CONNECTION_STRING"])
    except Exception:
        pass

    raise RuntimeError(
        "Lakebase connection string not found. Set LAKEBASE_CONNECTION_STRING or provide a secret named by LAKEBASE_SECRET_KEY."
    )


def build_connection_string() -> str:
    conninfo = get_connection_string()
    params = conninfo_to_dict(conninfo)

    required = {
        "host": params.get("host"),
        "dbname": params.get("dbname") or params.get("database"),
        "user": params.get("user"),
        "password": params.get("password"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Lakebase connection string is missing required fields: "
            + ", ".join(missing)
            + ". Update the secret 'database/"
            + get_secret_key_name()
            + "' with the full native Postgres connection string including password."
        )

    params.setdefault("sslmode", "require")
    return make_conninfo(**params)
