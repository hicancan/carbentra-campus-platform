"""Load explicitly mounted runtime secrets without baking them into images."""
import os
from pathlib import Path
import sys

for name in ("CARBENTRA_DATABASE_URL", "CARBENTRA_ADMIN_PASSWORD", "CARBENTRA_ADAPTER_TOKEN"):
    filename = os.environ.pop(name + "_FILE", None)
    if filename:
        if name in os.environ:
            raise SystemExit(f"Set either {name} or {name}_FILE, never both")
        value = Path(filename).read_text(encoding="utf-8").rstrip("\r\n")
        if not value.strip() or "\n" in value or "\r" in value:
            raise SystemExit(f"{name}_FILE must contain one non-empty line")
        os.environ[name] = value
if len(sys.argv) < 2:
    raise SystemExit("A service command is required")
os.execvp(sys.argv[1], sys.argv[1:])
