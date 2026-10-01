# Optional product display quantization

This is an offline candidate producer, not an alternative editable model or an API/runtime dependency. The canonical CAD/ECAD and original display GLB remain in the pinned hardware repository. The sole publishing entry point remains `backend/tools/import_product_asset.py`; these tools never write `packages/product/dist`.

## Reproduce

From the repository root, install the isolated, pinned tool dependencies:

```sh
npm ci --ignore-scripts --prefix packages/product/tools
uv venv --python 3.12 .venv
uv sync --locked --group assets
npm test --prefix packages/product/tools
uv run --locked --group assets python -m unittest discover -s packages/product/tools -p 'test_*.py' -v
```

Use a separate candidate folder and the exact source fingerprint. This command does not change the source or publish its output:

```sh
node --max-old-space-size=512 packages/product/tools/optimize-display.mjs \
  --source /path/to/pinned-hardware/visuals/rev_b/exports/carbentra_twin_light.glb \
  --output /path/to/candidates/plug.glb \
  --report /path/to/candidates/optimization.json \
  --expected-sha256 dc25e3965a9e653eb5c91a4514fcc1a3e051ffa47593778d7e70a71071e439d0
python packages/product/tools/validate-display.py \
  --source /path/to/pinned-hardware/visuals/rev_b/exports/carbentra_twin_light.glb \
  --candidate /path/to/candidates/plug.glb \
  --report /path/to/candidates/validation.json
```

Run the pinned official Khronos validator before promotion; this entry point binds its complete report to the candidate bytes:

```sh
node --max-old-space-size=512 packages/product/tools/validate-khronos.mjs \
  --candidate /path/to/candidates/plug.glb \
  --report /path/to/candidates/khronos-validation.json
```

Retain all three reports. A successful optimization command only yields `candidate_requires_independent_validation`; it is not acceptance.

## Invariants

- `@gltf-transform/functions` 4.3.0 quantizes only POSITION and NORMAL, both to 16 bits, per mesh, with automatic cleanup disabled
- Only superseded accessors with no non-root references are disposed. Without this storage cleanup the library retains old float data and can enlarge the file
- No join, flatten, simplify, generic prune or dedup runs. Named nodes, meshes, topology, material assignments, PBR material values and provenance extras remain intact
- The candidate requires only `KHR_mesh_quantization`, supported directly by the shipped Three.js loader. There is no decoder download, external model resource or new browser CSP/Wasm requirement
- Independent Python/NumPy validation parses GLB bytes itself. It compares every named part's vertex topology, world-space positions, per-part bounds, inverse-transpose-transformed normals, unchanged nonquantized attributes, PBR materials and extras
- Acceptance limits are 0.00001 m world-position/bounds error and 0.01° normal error. These are display-conversion tolerances, not measurement or physical manufacturing claims
- A candidate must be smaller than its source. Source/display SHA-256, exact versions, options, tolerances and complete per-part results must be retained by the importer

## Measured candidate

Against source SHA `dc25e3965a9e653eb5c91a4514fcc1a3e051ffa47593778d7e70a71071e439d0`, the tested candidate is `920e1c0de851eb64bcf4b36a4838bc83ed4820f0e833a0a4457fb3ce125f3277`:

- 30,337,768 → 22,318,016 bytes, 26.4% smaller
- Khronos glTF Validator 2.0.0-dev.3.10: zero errors and zero warnings; four informational unused UV attributes are retained from source
- All 227 named parts and 666,556 triangles retained
- Maximum world-position error: 1.3779013533 µm
- Maximum per-part bounds error: 0.6539036725 µm
- Maximum world-normal deviation: 0.0014988351°
- Transform: approximately 0.99 seconds, 244,940 KiB peak child RSS in the measured environment. This is not a browser frame-rate or memory claim

The display remains a design reference, not evidence that a registered device is installed, commissioned or safe for mains use.
