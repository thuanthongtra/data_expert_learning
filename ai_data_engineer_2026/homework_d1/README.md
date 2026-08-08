# Internal Support Tickets App

Streamlit app for Databricks Apps backed by Lakebase.

## Configuration

Store the Lakebase connection string in a Databricks secret named `lakebase_connection_string`.

Optional override if you want the app to read a different secret name:

- `LAKEBASE_SECRET_KEY`

Optional local override:

- `LAKEBASE_CONNECTION_STRING`

## Secret Setup

Use `setup_secrets.py` to create the secret scope and store the Lakebase connection string.

## Files

- `streamlit_app.py` - app entrypoint
- `support_tickets/` - database and UI helpers
- `sql/` - one DDL file per table
