"""Consume immutable njupt-map runtime and verified njupt-search snapshots.

Run the producer in njupt-map first. This importer does not edit either source,
create physical room identities, georeference schematic interiors, or infer
occupancy. The 129 map assets and 7 unmatched search buildings are distinct.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from fetch_search_snapshot import canonical, references, verify_manifest, PIN
from public_snapshot import project as public_snapshot

PACKAGE=Path(__file__).resolve().parents[1]
# Explicit source-scope association; never a display-name join.
MAP_CAMPUS_SOURCE_ID='campus-0d7550977cd648ac5ea5'


def read(path): return json.loads(path.read_text(encoding='utf8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(data)+b'\n')
def cid(value): return 'campus:'+value
def fid(value): return 'floor:search:'+value
def sid(value): return 'space:search:'+value
def famid(value): return 'family:search:'+value

def path_in(root,relative):
    rel=PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\\' in relative:
        raise ValueError(f'Unsafe artifact path: {relative}')
    path=root/relative
    if not path.resolve().is_relative_to(root.resolve()): raise ValueError('Artifact escapes package root')
    return path

def verify_files(root,refs):
    for ref in refs:
        path=path_in(root,ref['path'])
        if path.stat().st_size!=ref['bytes'] or sha(path)!=ref['sha256']:
            raise ValueError(f'Artifact hash/size mismatch: {ref["path"]}')

def unique(items,key):
    result={item[key]:item for item in items}
    if len(result)!=len(items) or any(not k for k in result): raise ValueError(f'Duplicated/missing {key}')
    return result

def load_sources(map_root,search_root):
    m=read(map_root/'manifest.json')
    if m['format']!='njupt-map-runtime' or m['schema_version']!=1: raise ValueError('Unsupported map runtime')
    if m['version']!=hashlib.sha256(canonical({k:v for k,v in m.items() if k!='version'})).hexdigest():
        raise ValueError('Map runtime content identity mismatch')
    verify_files(map_root,[dict(path=p,**ref) for p,ref in m['artifacts'].items()])
    # Optional producer products must be hash-listed before exposing their URLs.
    for key in ('context_mesh_url','context_local_geojson_url'):
        if m.get(key) and m[key] not in m['artifacts']:
            raise ValueError(f'Unverified map resource: {key}')
    for building in m['buildings']:
        for key in ('mesh_url','detail_mesh_url','detail_report_url'):
            if building.get(key) and building[key] not in m['artifacts']:
                raise ValueError(f'Unverified map building resource: {key}')
    s,documents=public_snapshot(search_root)
    collections={}
    for name in ['campuses','buildings','floors','space_families','aliases','connectors']:
        doc=documents[s['artifacts'][name]['path']]
        if doc['source_id']!=s['source_id']: raise ValueError(f'Source mismatch in {name}')
        collections[name]=doc[name]
    collections['spaces']=[]
    for ref in s['artifacts']['space_units']:
        doc=documents[ref['path']]
        if doc['source_id']!=s['source_id']: raise ValueError('Unit source mismatch')
        collections['spaces'].extend(doc['space_units'])
    for name,key in [('campuses','campus_id'),('buildings','building_id'),('floors','floor_id'),('space_families','space_family_id'),('spaces','space_unit_id')]:
        unique(collections[name],key)
    for name,count in [('campuses','campus_count'),('buildings','building_count'),('floors','floor_count'),('space_families','space_family_count'),('spaces','space_unit_count')]:
        if len(collections[name])!=s[count]: raise ValueError(f'Source count mismatch {name}')
    collections['_documents']=documents
    return m,s,collections


def build(map_root,search_root,output):
    map_root=Path(map_root).resolve();search_root=Path(search_root).resolve();output=Path(output).resolve()
    if any(output==src or output in src.parents or src in output.parents for src in [map_root,search_root]):
        raise ValueError('Output must not contain or overwrite source artifacts')
    if output.exists() and any(output.iterdir()):
        if not (output/'manifest.json').exists() or read(output/'manifest.json').get('format')!='carbentra-spatial-runtime':
            raise ValueError('Refusing to replace non-package output directory')
    m,s,src=load_sources(map_root,search_root)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.spatial-build-',dir=output.parent) as temp:
        stage=Path(temp)/'dist';stage.mkdir()
        # These are pinned public runtime products, never GPKG/Blender authoring sources.
        for relative in [*m['artifacts'],'manifest.json']:
            source=path_in(map_root,relative);target=stage/'map'/relative
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        for relative in [r['path'] for r in references(s)]+['manifest.json']:
            target=stage/'search'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            write(target,s if relative=='manifest.json' else src['_documents'][relative])
        sb=unique(src['buildings'],'building_id')
        sf=unique(src['floors'],'floor_id')
        families=unique(src['space_families'],'space_family_id')
        units=unique(src['spaces'],'space_unit_id')
        source_campuses=unique(src['campuses'],'campus_id')
        if MAP_CAMPUS_SOURCE_ID not in source_campuses: raise ValueError('Explicit map campus association is missing')
        mappings={}
        links=[]
        for b in m['buildings']:
            search_id=b.get('search_building_id')
            if search_id:
                if search_id not in sb or search_id in mappings: raise ValueError('Invalid explicit map/search crosswalk')
                if sb[search_id]['campus_id']!=MAP_CAMPUS_SOURCE_ID: raise ValueError('Cross-campus map association mismatch')
                mappings[search_id]='building:map:'+b['asset_id']
                links.append({'asset_id':b['asset_id'],'building_id':mappings[search_id],
                              'search_building_id':search_id,'match_status':'explicit_source_id',
                              'evidence':'GeoPackage buildings.space_id','map_feature_id':b.get('map_feature_id')})
        for b in src['buildings']: mappings.setdefault(b['building_id'],'building:search:'+b['building_id'])
        def provenance(namespace,source_id,**fields):
            return {'source_namespace':namespace,'source_id':source_id,
                    'source_version':m['source']['source_gpkg_sha256'] if namespace=='njupt-map' else s['snapshot_id'],
                    'synthetic':False,**fields}
        campuses=[{'id':cid(c['campus_id']),'name':c['name'],
                   **provenance('njupt-search',c['campus_id'],geometry_status=c['geometry_accuracy'],
                                coordinate_frame=c['coordinate_system'],source_geometry={'point':c['point'],'footprint':c['footprint']})}
                  for c in src['campuses']]
        wgs=read(map_root/'buildings.geojson')
        # Use the producer's local center and projected CRS for metric calculations.
        wgs_by_id={f['id']:f['geometry'] for f in wgs['features']}
        buildings=[]
        for b in m['buildings']:
            buildings.append({'id':'building:map:'+b['asset_id'],'campus_id':cid(MAP_CAMPUS_SOURCE_ID),
                'name':b['name'] or b['asset_id'],'asset_id':b['asset_id'],
                'search_building_id':b.get('search_building_id'),'levels':b.get('levels'),
                'levels_source':b.get('levels_source'),'height_m':b['height_m'],'height_source':b.get('height_source'),
                'center_local_m':b['center_local_m'],'bounds_local_m':b['bounds_local_m'],
                'centroid_wgs84':b['centroid_wgs84'],'geometry_wgs84':wgs_by_id[b['asset_id']],
                'mesh_url':'map/'+b['mesh_url'],
                **provenance('njupt-map',b['asset_id'],geometry_status=b['geometry_status'],
                              geometry_role=b['geometry_role'],confidence=b['confidence'],
                              coordinate_frame='campus_local_east_north_up_m',
                              campus_association='explicit_producer_xianlin_extent')})
        for b in src['buildings']:
            if b['building_id'] in {x['search_building_id'] for x in links}:continue
            buildings.append({'id':mappings[b['building_id']],'campus_id':cid(b['campus_id']),'name':b['name'],
                'asset_id':None,'search_building_id':b['building_id'],'levels':None,'height_m':None,
                'center_local_m':None,'bounds_local_m':None,'centroid_wgs84':None,'geometry_wgs84':None,'mesh_url':None,
                **provenance('njupt-search',b['building_id'],geometry_status='missing_metric_geometry',
                              confidence=b['geometry_accuracy'],source_geometry={'point':b['point'],'footprint':b['footprint']},
                              coordinate_frame='schematic')})
        floors=[];unit_floor={}
        for f in src['floors']:
            if f['building_id'] not in sb:raise ValueError('Floor references missing building')
            building=sb[f['building_id']]
            rec={'id':fid(f['floor_id']),'campus_id':cid(building['campus_id']),
                'building_id':mappings[f['building_id']],'level':f['level'],'name':f['level']+'层',
                'geometry_url':None,
                'metric_transform':None,'north_confidence':f['north_confidence'],
                'north_rotation_degrees':f['north_rotation_degrees'],
                **provenance('njupt-search',f['floor_id'],geometry_status=f['geometry_accuracy'],
                              coordinate_frame=f['local_coordinate_system'])}
            floors.append(rec)
            for unit_id in f['space_unit_ids']:
                if unit_id not in units or unit_id in unit_floor:raise ValueError('Invalid or repeated floor/unit association')
                unit_floor[unit_id]=f['floor_id']
        family_rows=[]
        for f in src['space_families']:
            if f['building_id'] not in sb or (f['floor_id'] is not None and f['floor_id'] not in sf):raise ValueError('Family references unknown hierarchy')
            family_rows.append({'id':famid(f['space_family_id']),'building_id':mappings[f['building_id']],
                'campus_id':cid(sb[f['building_id']]['campus_id']),
                'floor_id':fid(f['floor_id']) if f['floor_id'] else None,'name':f['room_number'],
                'unit_ids':[sid(x) for x in f['space_unit_ids']],'aliases':f['aliases'],
                'evidence_status':f['evidence_status'],'availability_eligible':f['availability_eligible'],
                **provenance('njupt-search',f['space_family_id'])})
        regions=read(map_root/'source-regions.json')
        if regions.get('schema_version') != 2 or regions.get('format') != 'njupt-indoor-region-catalog':
            raise ValueError('Map producer must publish current indoor region catalog v2')
        if regions.get('geometry_publication') != 'metadata_only':
            raise ValueError('Map indoor publication must contain identity metadata only')
        region_by_id=unique(regions['regions'], 'region_id')
        region_units=defaultdict(list)
        spaces=[]
        for u in src['spaces']:
            f=families.get(u['space_family_id'])
            if f is None or u['space_unit_id'] not in f['space_unit_ids']:raise ValueError('Unit family back-reference mismatch')
            floor_id=unit_floor.get(u['space_unit_id'])
            if floor_id != f['floor_id']:raise ValueError('Unit/family floor mismatch')
            if floor_id is not None and sf[floor_id]['building_id']!=f['building_id']:raise ValueError('Unit floor/building mismatch')
            matched=[r for r in u['evidence_refs'] if r in region_by_id]
            for r in matched:
                expected_asset=next((link['asset_id'] for link in links if link['search_building_id']==f['building_id']),None)
                if expected_asset is None or region_by_id[r]['asset_id']!=expected_asset:
                    raise ValueError('Region reference crosses explicitly linked buildings')
                if str(region_by_id[r]['floor_level'])!=sf[floor_id]['level']:
                    raise ValueError('Region reference crosses floors')
                region_units[r].append(sid(u['space_unit_id']))
            spaces.append({'id':sid(u['space_unit_id']),'family_id':famid(u['space_family_id']),
                'building_id':mappings[f['building_id']],'campus_id':cid(sb[f['building_id']]['campus_id']),
                'floor_id':fid(floor_id) if floor_id else None,'name':u['canonical_label'],
                'kind':u['space_type'],'confidence':u['geometry_confidence'],
                'identity_confidence':u['identity_confidence'],'availability_eligible':u['availability_eligible'],
                'evidence_status':f['evidence_status'],'region_ids':matched,'evidence_refs':u['evidence_refs'],
                'polygon_normalized':None,'label_point_normalized':None,
                'observed_occupancy':'unknown','planned_occupancy':'unknown',
                **provenance('njupt-search',u['space_unit_id'],geometry_status='not_published_reference_geometry',
                              coordinate_frame='unavailable')})
        crosswalk={'schema_version':1,'source_map_version':m['version'],'source_search_snapshot_id':s['snapshot_id'],
            'buildings':links,
            'unmatched_map_asset_ids':[b['asset_id'] for b in m['buildings'] if not b['search_building_id']],
            'unmatched_search_building_ids':[b for b in sb if b not in {x['search_building_id'] for x in links}],
            'regions':[{'region_id':r['region_id'],'asset_id':r['asset_id'],'source_space_key':r['source_space_key'],
                        'space_ids':region_units[r['region_id']],
                        'status':'explicit_evidence_reference' if region_units[r['region_id']] else 'unresolved'}
                       for r in regions['regions']],
            'multi_region_space_keys':regions['multi_region_space_keys'],
            'aliases':src['aliases'],
            'policy':'Only GPKG space_id and explicit source evidence_refs join sources. Labels never authorize a merge; upstream IDs may change after renaming.'}
        provenance={'map_runtime_version':m['version'],'map':m['source'],
            'search_snapshot_id':s['snapshot_id'],'search_source_id':s['source_id'],
            'search_source_url':'https://njupt.hicancan.top/generated/space/'+PIN,
            'search_upstream_snapshot_id':PIN,'indoor_geometry_publication':'metadata_only',
            'search_source_commit_reference':'d05a75aa4d8b998c7e0f5e408d94d8252793263f',
            'search_deployed_commit_verified':False,
            'importer_sha256':sha(Path(__file__)),
            'occupancy_policy':'Missing schedule/sensor observations remain unknown; eligibility is not occupancy.',
            'upstream_rename_policy':'Namespaced import IDs are deterministic for the pinned source. Upstream renamed IDs require explicit historical reconciliation before production re-import.'}
        source_version=hashlib.sha256(canonical(provenance)).hexdigest()
        seed={'schema_version':1,'format':'carbentra-spatial-seed','source_version':source_version,
            'campuses':campuses,'buildings':buildings,'floors':floors,'space_families':family_rows,
            'spaces':spaces,'crosswalk':links,'provenance':provenance}
        for name in ['campuses','buildings','floors','space_families','spaces']:
            seed[name].sort(key=lambda r:r['id']);unique(seed[name],'id')
        write(stage/'seed.json',seed);write(stage/'crosswalk.json',crosswalk)
        floor_rows = {f['id']: f for f in floors}
        room_index = {'schema_version': 1, 'format': 'carbentra-room-spatial-index',
            'source_version': source_version,
            'binding_key': 'space_id', 'dynamic_state_source': 'authenticated_classroom_api',
            'policy': 'Geometry is static. Join timestamped classroom states by exact space_id; missing observations remain unknown. Never use labels, proximity or floorplan colors as occupancy evidence.',
            'spaces': [{
                'space_id': room['id'], 'family_id': room['family_id'],
                'campus_id': room['campus_id'], 'building_id': room['building_id'],
                'floor_id': room['floor_id'], 'name': room['name'], 'kind': room['kind'],
                'geometry_status': room['geometry_status'],
                'display_geometry': {
                    'resource': floor_rows[room['floor_id']]['geometry_url'] if room['floor_id'] else None,
                    'feature_key': 'space_id', 'feature_id': room['id'],
                    'coordinate_frame': room['coordinate_frame'],
                    'label_point_normalized': room['label_point_normalized'],
                    'has_polygon': bool(room['polygon_normalized']), 'metric_transform': None},
                'source_regions': [{
                    'region_id': rid, 'resource': 'map/source-regions.json',
                    'floorplan_id': region_by_id[rid]['floorplan_id'],
                    'geometry_status': 'not_published_reference_geometry',
                    'binding_status': 'explicit_evidence_reference'} for rid in room['region_ids']],
                'identity_confidence': room['identity_confidence'],
                'availability_eligible': room['availability_eligible']
            } for room in sorted(spaces, key=lambda r:r['id'])]}
        write(stage/'room-spatial-index.json', room_index)
        geo=read(map_root/'buildings.local.geojson')
        for feature in geo['features']:
            feature['properties']['building_id']='building:map:'+feature['id']
        write(stage/'buildings.local.geojson',geo)
        write(stage/'ATTRIBUTION.json',{'map':read(map_root/'ATTRIBUTION.json'),
            'search':{'attribution':'hicancan / njupt-search','source':'https://github.com/hicancan/njupt-search',
                'code_license':'AGPL-3.0','data_notice':'Identity metadata only; reference-derived floorplan polygons, coordinates and originals are excluded.',
                'geometry_publication':'metadata_only','upstream_snapshot_id':PIN},
            'platform_notice':'Pinned public runtime. No restricted originals, floorplan traces or plan SVGs are bundled.'})
        files={p.relative_to(stage).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
               for p in sorted(stage.rglob('*')) if p.is_file()}
        manifest={'schema_version':1,'format':'carbentra-spatial-runtime','source_version':source_version,
            'coordinate_frame':m['coordinate_frame'],'provenance':provenance,
            'counts':{'campuses':len(campuses),'map_buildings':len(m['buildings']),'registry_buildings':len(buildings),
                'search_buildings':len(sb),'floors':len(floors),'space_families':len(family_rows),'space_units':len(spaces),
                'floorplans':0,'explicit_building_links':len(links),'search_unresolved_count':s['unresolved_count']},
            'buildings':[{**b,'building_id':'building:map:'+b['asset_id'],
                **{key:'map/'+b[key] for key in ('mesh_url','detail_mesh_url','detail_report_url') if b.get(key)}}
                for b in m['buildings']],
            'campus_mesh_url':'map/campus-lod1.glb','local_geojson_url':'buildings.local.geojson',
            'wgs84_geojson_url':'map/buildings.geojson','seed_url':'seed.json','crosswalk_url':'crosswalk.json',
            'room_spatial_index_url':'room-spatial-index.json',
            'floorplans':{},
            'artifacts':files,'limitations':m['limitations']+['Search rooms are reference identities, not installation-verified physical assets',
                  'Indoor reference-derived geometry is not published; room identity metadata remains available']}
        for key in ('context_mesh_url','context_local_geojson_url'):
            if m.get(key):manifest[key]='map/'+m[key]
        if m.get('context'):manifest['context']=m['context']
        manifest['version']=hashlib.sha256(canonical(manifest)).hexdigest()
        write(stage/'manifest.json',manifest)
        # Replace only our prior generated package after all validation succeeds.
        if output.exists(): shutil.rmtree(output)
        shutil.move(str(stage),str(output))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map-runtime',type=Path,required=True)
    p.add_argument('--search-snapshot',type=Path,required=True)
    p.add_argument('--output',type=Path,default=PACKAGE/'dist')
    args=p.parse_args();m=build(args.map_runtime,args.search_snapshot,args.output)
    print(json.dumps({'version':m['version'],'counts':m['counts'],'output':str(args.output)},ensure_ascii=False))
