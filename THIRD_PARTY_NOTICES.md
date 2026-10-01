# Third-party source and attribution inventory

This file records the materials present in the source projects. It does not assign a new license to all newly authored platform code or grant rights to third-party marks, photographs or documents.

## Campus spatial assets

The generated spatial package derives from [hicancan/njupt-map](https://github.com/hicancan/njupt-map). Its pinned source identities and per-file hashes are in `packages/spatial/dist/manifest.json` and the nested source manifests.

The upstream [material-specific notice](third-party/njupt-map-LICENSES.md) is preserved verbatim:

- Spatial database / OpenStreetMap-derived data: ODbL 1.0; © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
- Original modeling and scene composition: CC BY 4.0; attribution `hicancan / njupt-map`
- Original source code: AGPL-3.0-or-later; license text at [third-party/AGPL-3.0.txt](third-party/AGPL-3.0.txt)
- Third-party assets retain their own notices; university names and marks do not imply endorsement

The referenced source repository includes the editable GeoPackage and authoring project. Generated geometry is not a replacement for source provenance. Restricted original floorplan photographs, school documents and optional private observation material are not bundled into this platform.

## Search reference and semantic snapshot

[njupt-search](https://github.com/hicancan/njupt-search) supplies a pinned public semantic snapshot and user-interface design reference. Upstream identifies its source code as AGPL-3.0. This platform's React interface is independently implemented; source attribution and snapshot identity are retained in `packages/spatial/README.md` and its manifest. Do not assume that every third-party item mentioned by a search result inherits the repository's source-code license.

## Hardware wire contract

`backend/app/wire_contract` is generated from the separately maintained CARBENTRA hardware repository. Its manifest records the exact source files and hashes. Update through the import script, not by editing the generated copy. The hardware repository's rights and source notices remain separate from the web platform's dependencies.

## Package dependencies

Python versions are recorded in backend lock files; JavaScript versions and package metadata are recorded in `frontend/package-lock.json`. Container image sources and immutable digests appear in the Dockerfiles and Compose files. Their upstream licenses remain applicable. Build tooling and verification environments are not represented as original CARBENTRA software.

This is an independent project, not an official 南京邮电大学 service or endorsement. Before external distribution, the project owner should retain the material-specific source and attribution information with the chosen distribution.
