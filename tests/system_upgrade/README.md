# Browser and migration acceptance

The maintained browser entrypoint is `browser.mjs`. It uses the current root
`package-lock.json` and installed Microsoft Edge by default. `QA_BROWSER_CHANNEL`
can select another Playwright channel; `CHROMIUM_PATH` supplies an explicit
compatible executable. Chromium sandboxing stays enabled.

Run against a disposable development Compose stack, with physical control disabled:

```powershell
npm ci
Get-Content tests/system_upgrade/browser_fixture.py -Raw |
  docker compose exec -T api python - --describe |
  Set-Content D:/Temp/carbentra-fixture.json -Encoding utf8NoBOM
node tests/system_upgrade/browser.mjs http://127.0.0.1:8080 D:/Temp/carbentra-browser D:/Temp/carbentra-fixture.json
```

The normal simulator and workers remain running. The `--describe` helper only
reads the deterministic seed identity; it does not rewrite historical data.
The browser verifies authentication, all 13 application routes, the 603-room
matrix, three Switch channels sharing aggregate power, observed timelines,
persisted anomalies, metadata-only indoor list fallback, a genuine UI simulation command with manual hold and
sibling isolation, and persisted SHADOW evaluation without dispatch. Output
contains independently passed/failed groups and actual viewport screenshots. Repeated runs wait up to six minutes for the unchanged minimum-dwell gate; they do not reset clocks or overwrite command history.

`test_classrooms_postgres.py` requires a separate migrated PostgreSQL database
through `SYSTEM_UPGRADE_DATABASE_URL`; `tools/verify-local.ps1` provisions it.
`asset_transport.py` verifies authenticated family asset routing, bytes and hashes.
`check_restart_persistence.py` checks a previously saved SHADOW evaluation.

QEMU guest provisioning, failed browser retries, restored seed substitutes and
historical evidence copies were removed. Current native Docker cold-start and
browser results are in [the verification record](../../docs/DOCKER_VERIFICATION.md).
No hardware, production credential or remote CI result is implied.
