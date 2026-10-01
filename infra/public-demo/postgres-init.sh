#!/bin/sh
set -eu
: "${CARBENTRA_PUBLIC_DEMO_ID:?An explicit isolated deployment ID is required}"
case "$CARBENTRA_PUBLIC_DEMO_ID" in *[!a-z0-9-]*|'') echo 'Invalid deployment ID' >&2; exit 1 ;; esac
[ "$POSTGRES_DB" = carbentra_public_demo ] || { echo 'Refusing non-demo database' >&2; exit 1; }
[ "$POSTGRES_USER" = carbentra_demo_bootstrap ] || { echo 'Refusing non-demo bootstrap role' >&2; exit 1; }
export CARBENTRA_INIT_DB_PASSWORD=$(cat /run/secrets/database_password)
[ ${#CARBENTRA_INIT_DB_PASSWORD} -ge 32 ] || { echo 'A strong independently supplied database password is required' >&2; exit 1; }
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=demo_marker="CARBENTRA_PUBLIC_SIMULATION_ONLY_V1:$CARBENTRA_PUBLIC_DEMO_ID" <<'SQL'
\getenv app_password CARBENTRA_INIT_DB_PASSWORD
CREATE ROLE carbentra_public_demo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 48 PASSWORD :'app_password';
CREATE EXTENSION IF NOT EXISTS postgis;
REVOKE ALL ON DATABASE carbentra_public_demo FROM PUBLIC;
GRANT CONNECT ON DATABASE carbentra_public_demo TO carbentra_public_demo;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO carbentra_public_demo;
ALTER ROLE carbentra_public_demo SET statement_timeout = '30s';
ALTER ROLE carbentra_public_demo SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE carbentra_public_demo SET temp_file_limit = '256MB';
COMMENT ON DATABASE carbentra_public_demo IS :'demo_marker';
SQL

unset CARBENTRA_INIT_DB_PASSWORD
