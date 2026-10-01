#!/bin/sh
set -eu
# The image bootstrap administrator is never used by application services.
if [ -n "${CARBENTRA_DB_PASSWORD_FILE:-}" ]; then
    CARBENTRA_DB_PASSWORD=$(cat "$CARBENTRA_DB_PASSWORD_FILE")
fi
: "${CARBENTRA_DB_PASSWORD:?Application database password must be provided}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=app_password="$CARBENTRA_DB_PASSWORD" <<'SQL'
CREATE ROLE carbentra LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT CONNECT ON DATABASE carbentra TO carbentra;
GRANT USAGE, CREATE ON SCHEMA public TO carbentra;
SQL
