# Acceptance tests

Run the maintained backend/domain/HTTP/PostgreSQL suite from the repository root:

```powershell
uv venv --python 3.12 .venv
uv sync --locked --all-groups
pwsh -File tools/verify-local.ps1 -OutputDirectory D:/Temp/carbentra-check
```

The PowerShell runner creates a disposable Docker PostGIS instance, performs
old-schema-to-head and repeated migration checks, then runs backend, acceptance,
classroom, infrastructure, Edge, spatial and frontend checks. It removes only
its own test Compose project when done. Existing projects are rejected.
`compose.test.yaml` binds PostgreSQL to localhost; trust authentication is only
for this disposable fixture. Without explicit PostgreSQL test URLs, DB-specific
tests report skips.

`live_stack.py` is a separate authenticated HTTP check for an explicitly local
SIMULATED development deployment. Current browser checks are documented in
[system_upgrade](../system_upgrade/README.md). Multi-device transport and actual
FastAPI-to-MQTT integration are maintained in `edge/tools`.

Retired browser revisions, QEMU-only orchestration, duplicate historical logs
and scripts referencing the former hardware-repository Edge were removed.
Their outcomes are not counted as current validation. No software fixture
qualifies radio, electrical safety, physical switching or measured savings.
