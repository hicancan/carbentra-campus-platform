#!/usr/bin/env python3
"""Create a NEW dedicated demo acceptance DB on the disposable loopback CI server.

Never resets/drops a database or changes an existing role. Trust authentication is
only the existing isolated test-server convention, not a deployment configuration.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def prepare(raw_url):
    url = make_url(raw_url)
    if url.host not in {"127.0.0.1", "localhost"} or url.database != "acceptance" or url.username != "qa":
        raise ValueError("Only the existing disposable loopback qa/acceptance test server is permitted")
    engine = create_engine(url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname='carbentra_public_demo')")) or connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='carbentra_public_demo')")):
                raise RuntimeError("Demo test database or role already exists; use a NEW disposable test server")
            connection.execute(text("CREATE ROLE carbentra_public_demo LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"))
            connection.execute(text("CREATE DATABASE carbentra_public_demo"))
    finally:
        engine.dispose()
    demo_admin_url = url.set(database="carbentra_public_demo")
    engine = create_engine(demo_admin_url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    try:
        with engine.connect() as connection:
            for command in (
                "CREATE EXTENSION postgis",
                "REVOKE ALL ON DATABASE carbentra_public_demo FROM PUBLIC",
                "GRANT CONNECT ON DATABASE carbentra_public_demo TO carbentra_public_demo",
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
                "GRANT USAGE, CREATE ON SCHEMA public TO carbentra_public_demo",
                "COMMENT ON DATABASE carbentra_public_demo IS 'CARBENTRA_PUBLIC_SIMULATION_ONLY_V1:test-generation'",
            ):
                connection.execute(text(command))
    finally:
        engine.dispose()
    demo_url = url.set(database="carbentra_public_demo", username="carbentra_public_demo", password=None).render_as_string(hide_password=False)
    env = {key: value for key, value in os.environ.items() if not key.startswith("CARBENTRA_")}
    env.update(CARBENTRA_DATABASE_URL=demo_url, CARBENTRA_ENV="production", CARBENTRA_DEPLOYMENT_MODE="public_simulation",
        CARBENTRA_PUBLIC_DEMO_ID="test-generation", CARBENTRA_COOKIE_SECURE="true", CARBENTRA_AUTO_MIGRATE="false",
        CARBENTRA_WORKER_ENABLED="false", CARBENTRA_SIMULATION_ENABLED="true", CARBENTRA_ALLOWED_ORIGINS='["https://demo.example.org"]')
    subprocess.run([sys.executable, "-m", "app.public_demo", "migrate"], cwd=Path(__file__).resolve().parents[1] / "backend", env=env, check=True)
    print("Prepared fresh restricted-role public demo acceptance database; no operational database was modified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-disposable-local-test", required=True, action="store_true")
    args = parser.parse_args()
    prepare(os.environ["ACCEPTANCE_DATABASE_URL"])


if __name__ == "__main__":
    main()
