# Continuous verification

`.github/workflows/verify.yml` runs Node 24 frontend tests/build/audit and Python
3.12 backend, HTTP/domain, PostgreSQL, Edge and spatial checks. Python dependencies
come from the root cross-platform `uv.lock`, after explicit `uv venv` creation.
The workflow uses read-only repository permissions and never deploys or obtains
production credentials. Compiled firmware integration gates and browser scenarios
have separate local runners; CI skips must not be read as hardware success.

Local success does not establish a remote GitHub Actions run. Check the actual
run for the published commit before claiming remote CI completion.

Official action release commits are pinned:

- checkout v4.2.2: `11bd71901bbe5b1630ceea73d27597364c9af683`
- setup-node v4.4.0: `49933ea5288caeca8642d1e84afbd3f7d6820020`
- [setup-uv v10.1.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.1.0): `bec219d24cd3e171d82865faccec33120bb574f4`, resolved from the official Git ref on 2026-10-01

Refresh pins deliberately and rerun the relevant checks. Disposable CI Postgres
trust authentication never applies to `compose.prod.yaml`.
