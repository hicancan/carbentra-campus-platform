# Generated HTTP contracts

The editable source is `backend/app/schemas.py` (requests), `backend/app/responses.py` (public responses), and route declarations. `openapi.json` is generated from the live FastAPI application without starting its database or demo seed:

```
backend/.venv/bin/python backend/tools/export_openapi.py
backend/.venv/bin/python backend/tools/export_openapi.py --check
```

The frontend generates `src/lib/generated-api.ts` from this artifact using pinned openapi-typescript. Do not manually edit generated response shapes. HTTP/schema tests exercise actual endpoint responses, exact uint64 decimal strings, nullable unknowns, command lifecycle results, and failure without exposing unexpected internal fields.

Core auth/device/telemetry/command/accounting/forecast/control-eligibility responses have explicit DTOs. Some remaining operational/reference responses are still dynamic dictionaries; this is not a claim that every route has an exhaustive response schema. Canonical device-wire schemas remain separately generated from the hardware producer's single editable contract, never reauthored here.
