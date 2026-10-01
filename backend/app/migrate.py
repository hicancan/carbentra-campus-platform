"""Explicit operator migration entrypoint; no auto-schema changes in production."""
from pathlib import Path
from alembic import command
from alembic.config import Config


def main():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
