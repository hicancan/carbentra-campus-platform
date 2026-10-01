# CARBENTRA Campus maintenance

- Maintain the campus-scale platform. Simulated, replayed and real sources remain explicit. Unknown/stale is never zero, vacant or safe. No measured-savings or mains-qualification claims without evidence.
- Backend uses FastAPI/SQLAlchemy/Pydantic and PostgreSQL+PostGIS; SQLite is explicit local/test storage. Frontend uses React/TypeScript. Keep ingestion, workers and Edge separate where their lifecycles require it.
- packages/iot-contract is the protocol authority. Edge adapts Sense/Plug/three-channel Switch without inventing physical feedback. Sense B is wired radar plus raw light; Switch meters aggregate power and ACK is unverified execution.
- Authoring geometry belongs to njupt-map. Import pinned spatial products with hashes and attribution; no second authored database. Public indoor catalogs retain identity metadata and exclude unreviewed floorplan traces.
- Preserve namespaced IDs, explicit spatial/electrical topology, historical bindings, Wh units, quality, observed/received time, boot/sequence, durable deduplication and coverage gaps. No parent/child meter double counting.
- Frontend uses scoped authenticated API only. Maintain RBAC, CSRF/session protection and audit history. Production rejects placeholders/development shortcuts, starts unseeded and does not silently permit simulation.
- Physical actuation remains disabled until commissioning and authorization. Commands require ID, sequence, expiry, capability and explicit states. Late receipts cannot downgrade final states; preserve manual/maintenance authority.
- Use PowerShell 7, root uv workspace .venv, Node and local Docker. Temporary environments, identities, databases and logs use task-specific external directories; never commit production credentials.
- Run meaningful unit, PostgreSQL/migration, Edge mTLS, production HTTPS and browser checks after behavior changes; record actual evidence and limits. Configuration validation is not a successful cold start.
- Keep one maintained implementation/deployment path. Git preserves retired QEMU/legacy-edge workflows. Apply LICENSES.md by material and keep upstream attribution.
