#!/usr/bin/env python3
"""Operator-run first provisioning; never prints, replaces, or commits credentials.

Run only after approving the demo host/account setup. The parent directory must
already exist outside this checkout. Existing output directories are rejected.
"""
import argparse
import os
from pathlib import Path
import secrets


def provision(destination):
    if os.name != "posix":
        raise ValueError("This helper requires POSIX permission enforcement; use an audited secret provider on other hosts")
    destination = Path(destination)
    checkout = Path(__file__).resolve().parents[1]
    if not destination.is_absolute() or destination.resolve().is_relative_to(checkout):
        raise ValueError("Choose an absolute private directory outside the checkout")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("Prepare a trusted parent directory first")
    # Exclusive creation also rejects a preexisting symlink or nonempty directory.
    destination.mkdir(mode=0o700)
    values = {name: secrets.token_urlsafe(32) for name in (
        "postgres_password", "database_password", "admin_password", "demo_visitor_password", "demo_operator_password")}
    values["database_url"] = "postgresql+psycopg://carbentra_public_demo:" + values["database_password"] + "@db:5432/carbentra_public_demo"
    for name, value in values.items():
        descriptor = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value + "\n")
        # Local Compose file secrets are bind mounts: uid/gid/mode are not remapped.
        # Private 0700 parent restricts host traversal; each service receives only its
        # selected files, readable by its unprivileged UID, through a read-only mount.
        os.chmod(destination / name, 0o444)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    directory = provision(args.directory)
    print(f"Created six secret files in {directory}; values were not printed. Keep this directory private and outside backups shared with visitors.")


if __name__ == "__main__":
    main()
