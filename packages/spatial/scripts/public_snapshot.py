"""Project a verified search snapshot to distributable identity metadata only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from fetch_search_snapshot import canonical, references, verify_manifest, PIN

FORMAT = 'njupt-space-metadata-snapshot'
FIELDS = {
    'campuses': ('aliases','campus_id','evidence_refs','name'),
    'buildings': ('aliases','building_id','campus_id','evidence_refs','floor_ids','name'),
    'floors': ('building_id','connector_ids','floor_id','level','space_unit_ids','source_image_refs'),
    'space_families': ('aliases','availability_eligible','building_id','evidence_status',
                       'floor_id','room_number','space_family_id','space_unit_ids'),
    'space_units': ('availability_eligible','canonical_label','evidence_refs','identity_confidence',
                   'raw_labels','space_family_id','space_type','space_unit_id'),
    'aliases': ('alias','normalized_alias','sources','space_family_id','space_unit_id','status'),
    'connectors': ('connector_id','building_id','floor_id','from_floor_id','to_floor_id','type','evidence_refs'),
}


def project(root):
    """Return a self-contained projection, preserving upstream hashes as provenance."""
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    verify_manifest(manifest,PIN)
    documents={}
    for ref in references(manifest):
        relative=ref['path']
        if Path(relative).name!=relative or '\\' in relative:
            raise ValueError('Unsafe search artifact path')
        raw=(root/relative).read_bytes()
        if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
            raise ValueError(f'Artifact hash/size mismatch: {relative}')
        documents[relative]=json.loads(raw)
    if manifest['format']==FORMAT:
        for collection,fields in FIELDS.items():
            group=manifest['artifacts'][collection]
            refs=group if isinstance(group,list) else [group]
            extra={'campuses':('point','footprint','geometry_accuracy','coordinate_system'),
                   'buildings':('point','footprint','geometry_accuracy'),
                   'floors':('geometry_path','outline','north_rotation_degrees','north_confidence',
                             'local_coordinate_system','geometry_accuracy'),
                   'space_units':('geometry_confidence',)}.get(collection,())
            for ref in refs:
                doc=documents[ref['path']]
                if doc.get('geometry_publication')!='metadata_only':
                    raise ValueError('Unreviewed geometry publication')
                for record in doc[collection]:
                    if set(record)-set(fields)-set(extra):
                        raise ValueError('Unexpected field in public identity metadata')
                    for field in ('point','footprint','geometry_path','outline','north_rotation_degrees'):
                        if record.get(field) is not None:
                            raise ValueError('Reference geometry is not public metadata')
        return manifest,documents
    output={}
    artifacts={}
    for collection,fields in FIELDS.items():
        group=manifest['artifacts'][collection]
        refs=group if isinstance(group,list) else [group]
        new_refs=[]
        for ref in refs:
            records=[]
            for record in documents[ref['path']][collection]:
                row={key:record[key] for key in fields if key in record}
                if collection in ('campuses','buildings'):
                    row.update(point=None,footprint=None,geometry_accuracy='not_published_reference_geometry')
                    if collection=='campuses':row['coordinate_system']='unavailable'
                elif collection=='floors':
                    row.update(geometry_path=None,outline=None,north_rotation_degrees=None,
                               north_confidence='unknown',local_coordinate_system='unavailable',
                               geometry_accuracy='not_published_reference_geometry')
                elif collection=='space_units':
                    row['geometry_confidence']='not_published_reference_geometry'
                records.append(row)
            doc={'source_id':manifest['source_id'],'geometry_publication':'metadata_only',
                 'source_artifact_sha256':ref['sha256'],collection:records}
            raw=canonical(doc)+b'\n'
            output[ref['path']]=doc
            new_refs.append({'path':ref['path'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        artifacts[collection]=new_refs if isinstance(group,list) else new_refs[0]
    public={key:manifest[key] for key in ('source_id','building_count','campus_count','floor_count',
                                        'space_family_count','space_unit_count','unresolved_count')}
    public.update(format=FORMAT,source_snapshot_id=PIN,geometry_publication='metadata_only',
                  geometry_unit_count=0,artifacts=artifacts,
                  projector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    public['snapshot_id']=hashlib.sha256(canonical(public)).hexdigest()
    return public,output
