#!/usr/bin/env python3
"""Operator-invoked, local-only creation. Never overwrite existing secrets."""
import argparse
import getpass
from pathlib import Path
import secrets

parser = argparse.ArgumentParser()
parser.add_argument("--directory", default=".secrets")
args = parser.parse_args()
directory = Path(args.directory)
if directory.exists() and any(directory.iterdir()):
    raise SystemExit("Refusing to overwrite an existing secrets directory")
password = getpass.getpass("Choose the production administrator password (16+ characters): ")
if len(password.strip()) < 16 or password.lower() in {"development-only", "change-me-please-now", "your-password-here"}:
    raise SystemExit("Use a unique, non-placeholder password of at least 16 characters")
if password != getpass.getpass("Confirm administrator password: "):
    raise SystemExit("Passwords did not match")
if "\n" in password or "\r" in password:
    raise SystemExit("Password must be a single line")
directory.mkdir(mode=0o700, parents=True, exist_ok=True)
directory.chmod(0o700)
db_password = secrets.token_urlsafe(36)
values = {
    "postgres_password": secrets.token_urlsafe(36),
    "database_password": db_password,
    "database_url": f"postgresql+psycopg://carbentra:{db_password}@db:5432/carbentra",
    "admin_password": password,
}
for name, value in values.items():
    path = directory / name
    with path.open("x", encoding="utf-8") as handle:
        handle.write(value + "\n")
    # Compose bind-mounted secrets retain file ownership. Directory 0700 protects
    # host access; 0444 lets the non-root container read its individual mount.
    path.chmod(0o444)
print(f"Created {len(values)} local secret files. Keep {directory} private and out of Git.")
