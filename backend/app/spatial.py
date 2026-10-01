"""Verified reference-only registry import, separate from simulated instrumentation.

A package update may add identities and update descriptive metadata. Removing a
source identity or changing its parent/source identity requires an explicit historical
reconciliation outside this importer; existing device bindings are never rewritten.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
from sqlalchemy import select, text
from .common import DomainError, audit
from .db import utcnow, iso
from .models import Campus, Building, Floor, Space, State

RESOURCES={"campuses":Campus,"buildings":Building,"floors":Floor,"spaces":Space}
PARENTS={"campuses":(),"buildings":("campus_id",),"floors":("building_id",),"spaces":("campus_id","building_id","floor_id")}
NAMESPACES={"njupt-map","njupt-search"}


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_package(settings,expected_version=None):
    try:
        manifest_raw=settings.spatial_manifest_path.read_bytes()
        manifest=json.loads(manifest_raw)
        raw=settings.spatial_seed_path.read_bytes()
        seed=json.loads(raw)
        if manifest.get('schema_version')!=1 or manifest.get('format')!='carbentra-spatial-runtime' or seed.get('schema_version')!=1 or seed.get('format')!='carbentra-spatial-seed':
            raise ValueError('Unsupported reference package format')
        version=manifest['version']
        if version!=sha(canonical({key:value for key,value in manifest.items() if key!='version'})):
            raise ValueError('Manifest content hash differs from its pinned version')
        if expected_version is not None and version!=expected_version:
            raise ValueError('Package version differs from the operator-selected release')
        relative=PurePosixPath(manifest['seed_url'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
            raise ValueError('Unsafe seed path')
        if (settings.spatial_manifest_path.parent/str(relative)).resolve()!=settings.spatial_seed_path.resolve():
            raise ValueError('Configured seed is not the artifact referenced by the manifest')
        reference=manifest['artifacts'][str(relative)]
        if reference['bytes']!=len(raw) or reference['sha256']!=sha(raw):
            raise ValueError('Seed size/hash does not match the manifest')
        if seed['source_version']!=manifest['source_version']:
            raise ValueError('Seed and manifest describe different source versions')
        for resource in RESOURCES:
            rows=seed[resource]
            if not isinstance(rows,list) or len(rows)>100000:
                raise ValueError('Invalid or excessive reference collection')
            ids=[row['id'] for row in rows]
            if len(set(ids))!=len(ids):
                raise ValueError('Duplicate reference identity')
            for row in rows:
                if row['source_namespace'] not in NAMESPACES or row.get('synthetic') is not False or not row.get('source_id') or not row.get('source_version'):
                    raise ValueError('Reference provenance is incomplete or not source-only')
        campuses={x['id']:x for x in seed['campuses']};buildings={x['id']:x for x in seed['buildings']};floors={x['id']:x for x in seed['floors']}
        for row in buildings.values():
            if row['campus_id'] not in campuses:
                raise ValueError('Building parent is absent from package')
        for row in floors.values():
            if row['building_id'] not in buildings:
                raise ValueError('Floor parent is absent from package')
        for row in seed['spaces']:
            building=buildings.get(row['building_id']);floor=floors.get(row.get('floor_id'))
            if not building or row['campus_id']!=building['campus_id'] or (row.get('floor_id') and (not floor or floor['building_id']!=building['id'])):
                raise ValueError('Space hierarchy is inconsistent')
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        raise DomainError('spatial_package_invalid','Reference package integrity/structure verification failed',422,{'reason':str(exc)}) from None
    identity={'package_version':version,'source_version':seed['source_version'],'seed_sha256':sha(raw),'manifest_sha256':sha(manifest_raw)}
    return seed,identity


def infer_category(name):
    for chars,category in [('食堂','dining'),('宿舍','residential'),('图书','library'),('教','teaching'),('实验','research'),('体育','sports'),('行政','administration')]:
        if chars in name:
            return category
    return 'other'


def source_integer(value,nullable=False):
    if value is None and nullable:
        return None
    try:
        integer=int(value)
        if isinstance(value,bool) or float(value)!=integer or not -2**31<=integer<2**31:
            raise ValueError()
    except (ValueError,TypeError,OverflowError):
        raise DomainError('spatial_level_invalid','Source storey/level value requires an exact finite integer mapping',422) from None
    return integer


def projected(resource,entry):
    values={'name':entry['name'],'source':entry['source_namespace'],'provenance':entry}
    if resource=='campuses':
        values.update(timezone='Asia/Shanghai',source_mode='REFERENCE')
    elif resource=='buildings':
        levels=entry.get('levels')
        values.update(campus_id=entry['campus_id'],category=infer_category(entry['name']),floors=source_integer(levels,nullable=True),
            area_m2=None,centroid=entry.get('centroid_wgs84'),geometry=entry.get('geometry_wgs84'),external_space_id=entry.get('search_building_id'),source_mode='REFERENCE')
    elif resource=='floors':
        values.update(building_id=entry['building_id'],level=source_integer(entry['level']))
    else:
        values.update(campus_id=entry['campus_id'],building_id=entry['building_id'],floor_id=entry.get('floor_id'),kind=entry.get('kind','unknown'),confidence=entry.get('confidence','unverified'))
    return values


def plan_import(db,seed,identity):
    plan={**identity,'resources':{},'applicable':True,'reference_only':True,'changes_device_bindings':False}
    for resource,model in RESOURCES.items():
        current={row.id:row for row in db.scalars(select(model))}
        incoming={entry['id']:entry for entry in seed[resource]}
        changes={'additions':[],'updates':[],'removals':[],'conflicts':[],'unchanged':0}
        for ident,entry in incoming.items():
            values=projected(resource,entry);row=current.get(ident)
            if row is None:
                changes['additions'].append(ident);continue
            provenance=row.provenance or {}
            conflicts=[key for key in PARENTS[resource] if getattr(row,key)!=values[key]]
            if row.source!=entry['source_namespace'] or provenance.get('source_id')!=entry['source_id']:
                conflicts.append('source_identity')
            if conflicts:
                changes['conflicts'].append({'id':ident,'fields':conflicts});continue
            fields=[key for key,value in values.items() if getattr(row,key)!=value]
            if fields:
                changes['updates'].append({'id':ident,'fields':fields})
            else:
                changes['unchanged']+=1
        changes['removals']=sorted(ident for ident,row in current.items() if ident not in incoming and row.source in NAMESPACES and (row.provenance or {}).get('source_id'))
        if changes['removals'] or changes['conflicts']:
            plan['applicable']=False
        plan['resources'][resource]=changes
    return plan


def import_package(db,settings,apply=False,expected_version=None,actor='spatial-import'):
    seed,identity=read_package(settings,expected_version)
    # Registry import is an operator task; serialize separate invocations on PostgreSQL.
    if apply and db.bind.dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(48392717)'))
    plan=plan_import(db,seed,identity)
    if not apply:
        return plan
    if not plan['applicable']:
        raise DomainError('spatial_reconciliation_required','Reference removals or source/parent identity changes require explicit historical reconciliation; no rows changed',409,plan)
    old=db.get(State,'spatial')
    changed=any(r['additions'] or r['updates'] for r in plan['resources'].values())
    for resource,model in RESOURCES.items():
        wanted=set(plan['resources'][resource]['additions'])|{row['id'] for row in plan['resources'][resource]['updates']}
        for entry in seed[resource]:
            if entry['id'] not in wanted:
                continue
            values=projected(resource,entry);row=db.get(model,entry['id'])
            if row is None:
                db.add(model(id=entry['id'],**values))
            else:
                for key,value in values.items():
                    setattr(row,key,value)
        db.flush()
    if changed or not old or any(old.value.get(key)!=value for key,value in identity.items()):
        content={**identity,'available':True,'status':'synchronized','imported_at':iso(utcnow()),'measurement_claim':False,'base_url':'/assets/spatial',
            **{name:len(seed[name]) for name in RESOURCES},'last_import_changes':plan['resources']}
        if old:
            old.value=content
        else:
            db.add(State(key='spatial',value=content))
        audit(db,actor,'imported','spatial',identity['package_version'],{'package_version':identity['package_version'],'reference_only':True,
            'counts':{name:{key:len(value) for key,value in row.items() if isinstance(value,list)} for name,row in plan['resources'].items()}})
    db.flush()
    return {**plan,'applied':True,'changed':changed}


def spatial_status(db,settings):
    imported=db.get(State,'spatial')
    imported_value=dict(imported.value) if imported else {'available':False}
    imported_value['verification']='manifest_and_seed_verified' if imported_value.get('package_version') and imported_value.get('manifest_sha256') else 'legacy_unverified' if imported else 'not_imported'
    try:
        _,bundled=read_package(settings)
        bundled={'available':True,**bundled}
    except DomainError as exc:
        bundled={'available':False,'error':exc.code}
    synchronized=bool(imported and bundled.get('available') and all(imported_value.get(key)==bundled.get(key) for key in ('package_version','seed_sha256','manifest_sha256')))
    return {**imported_value,'bundled':bundled,'imported':imported_value,'synchronized':synchronized,
        'status':'synchronized' if synchronized else 'not_imported' if not imported else 'package_differs_from_registry'}
