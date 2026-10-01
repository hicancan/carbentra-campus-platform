# Infrastructure ownership

- `../compose.yaml`: explicit localhost-only simulated development deployment, separate control/simulation and forecast-analysis processes
- `../compose.dev.yaml`: optional Python hot reload override
- `../compose.prod.yaml`: standalone production configuration; never combine with development Compose
- `nginx.conf`: non-root static SPA, authenticated API/spatial reverse proxy, model compression and SSE
- `postgres-init.sh`: PostGIS extension and non-superuser application role on an empty volume
- `container-entrypoint.py`: reads explicitly mounted secret files before process execution
- `edge.Dockerfile`: builds the single platform Edge plus shared IoT contract and two operator status/migration tools; no hardware checkout build context

No MQTT broker, enabled physical relay adapter, public endpoint, auto-deployment or campus credential is configured by default. The user must separately authorize and commission physical integration. See `../docs/OPERATIONS.md` and the latest verification report before deployment.
