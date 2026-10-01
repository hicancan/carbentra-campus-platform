"""Offline checks of the pinned importer, semantic references and runtime files."""
from __future__ import annotations
from collections import Counter
import copy
import os
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE/'scripts'))
from build_package import build, canonical, load_sources, path_in, read, sha, verify_files
from fetch_search_snapshot import PIN, verify_manifest
from public_snapshot import project

DIST=Path(os.environ.get('SPATIAL_TEST_DIST',str(PACKAGE/'dist'))).resolve()

class SpatialPackageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=read(DIST/'manifest.json')
        cls.seed=read(DIST/'seed.json')
        cls.crosswalk=read(DIST/'crosswalk.json')

    def test_every_artifact_and_package_content_hash(self):
        m=self.manifest
        self.assertEqual(m['version'],hashlib.sha256(canonical({k:v for k,v in m.items() if k!='version'})).hexdigest())
        verify_files(DIST,[dict(path=p,**v) for p,v in m['artifacts'].items()])
        load_sources(DIST/'map',DIST/'search')
        actual={p.relative_to(DIST).as_posix() for p in DIST.rglob('*') if p.is_file()}
        self.assertEqual(actual,set(m['artifacts'])|{'manifest.json'})

    def test_full_scope_counts_unique_ids_and_foreign_keys(self):
        s=self.seed
        for name,n in [('campuses',3),('buildings',136),('floors',41),('space_families',536),('spaces',603)]:
            self.assertEqual(len(s[name]),n)
            self.assertEqual(len({r['id'] for r in s[name]}),n)
            self.assertTrue(all(r['synthetic'] is False for r in s[name]))
        campuses={x['id'] for x in s['campuses']};buildings={x['id']:x for x in s['buildings']}
        floors={x['id']:x for x in s['floors']};families={x['id']:x for x in s['space_families']}
        for building in buildings.values():self.assertIn(building['campus_id'],campuses)
        for floor in floors.values():self.assertIn(floor['building_id'],buildings)
        for space in s['spaces']:
            self.assertEqual(space['building_id'],floors[space['floor_id']]['building_id'])
            self.assertEqual(space['floor_id'],families[space['family_id']]['floor_id'])
            self.assertIn(space['id'],families[space['family_id']]['unit_ids'])

    def test_only_explicit_source_crosswalk_and_multi_region_preservation(self):
        c=self.crosswalk
        self.assertEqual(len(c['buildings']),4)
        self.assertEqual({b['asset_id'] for b in c['buildings']},{'osm_way_223699451','osm_way_223699456','osm_way_155434036','osm_way_223699452'})
        self.assertEqual(len(c['unmatched_map_asset_ids']),125)
        self.assertEqual(len(c['unmatched_search_building_ids']),7)
        self.assertEqual(len(c['regions']),564)
        self.assertEqual(Counter(r['status'] for r in c['regions']),{'explicit_evidence_reference':563,'unresolved':1})
        self.assertEqual(len(c['multi_region_space_keys']),7)
        self.assertEqual(len([r for r in c['regions'] if r['source_space_key']=='仙林/教4/211']),3)
        unit_ids={x['id'] for x in self.seed['spaces']}
        for r in c['regions']:self.assertLessEqual(set(r['space_ids']),unit_ids)
        self.assertTrue(any(a['status']=='ambiguous' for a in c['aliases']))

    def test_no_schedule_or_missing_data_is_promoted_to_occupancy(self):
        for space in self.seed['spaces']:
            self.assertEqual(space['observed_occupancy'],'unknown')
            self.assertEqual(space['planned_occupancy'],'unknown')
        room=next(s for s in self.seed['spaces'] if s['source_id']=='space-unit-c1725379e5adbf1beb49')
        self.assertEqual(room['evidence_status'],'floor_plan_only')
        self.assertEqual(room['availability_eligible'],'ineligible')
        self.assertEqual(room['observed_occupancy'],'unknown')

    def test_reference_floorplan_geometry_is_not_public(self):
        self.assertEqual(self.manifest['floorplans'],{})
        self.assertEqual(sum(bool(s['polygon_normalized']) for s in self.seed['spaces']),0)
        self.assertFalse((DIST/'floorplans').exists())
        search=read(DIST/'search/manifest.json')
        self.assertEqual(search['source_snapshot_id'],PIN)
        self.assertEqual(search['geometry_publication'],'metadata_only')
        self.assertEqual(search['geometry_unit_count'],0)
        self.assertNotIn('geometry',search['artifacts'])
        for region in read(DIST/'map/source-regions.json')['regions']:
            for key in ('polygon_normalized','label_point_normalized','bounds_normalized'):
                self.assertNotIn(key,region)
        for floor in read(DIST/'search/floors.json')['floors']:
            self.assertIsNone(floor['geometry_path'])
            self.assertIsNone(floor['outline'])
        self.assertFalse(any(p.suffix.lower() in {'.png','.jpg','.blend','.svg','.gpkg'} for p in DIST.rglob('*')))

    def test_glb_pick_id_to_registry_roundtrip(self):
        glb=(DIST/self.manifest['campus_mesh_url']).read_bytes()
        magic,version,size=struct.unpack_from('<4sII',glb)
        self.assertEqual((magic,version,size),(b'glTF',2,len(glb)))
        json_size=struct.unpack_from('<I',glb,12)[0]
        doc=json.loads(glb[20:20+json_size])
        mapping={b['asset_id']:b['building_id'] for b in self.manifest['buildings']}
        registry={b['id'] for b in self.seed['buildings']}
        self.assertEqual(len(doc['nodes']),129)
        for node in doc['nodes']:
            self.assertEqual(node['name'],node['extras']['asset_id'])
            self.assertIn(mapping[node['name']],registry)
        geo=read(DIST/self.manifest['local_geojson_url'])
        for feature in geo['features']:
            self.assertEqual(feature['properties']['building_id'],mapping[feature['id']])

    def test_rebuild_is_deterministic_from_pinned_published_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'dist'
            a=build(DIST/'map',DIST/'search',out)
            first={p.relative_to(out).as_posix():(p.stat().st_size,sha(p)) for p in out.rglob('*') if p.is_file()}
            (out/'retired-resource').write_text('remove this generated artifact', encoding="utf-8")
            b=build(DIST/'map',DIST/'search',out)
            self.assertEqual(a,b)
            self.assertEqual(first,{p.relative_to(out).as_posix():(p.stat().st_size,sha(p)) for p in out.rglob('*') if p.is_file()})
            # A changed importer intentionally changes publication provenance,
            # while the canonical entity facts remain stable.
            expected=copy.deepcopy(self.seed)
            expected['provenance']['importer_sha256']=sha(PACKAGE/'scripts/build_package.py')
            expected['source_version']=hashlib.sha256(canonical(expected['provenance'])).hexdigest()
            self.assertEqual(read(out/'seed.json'),expected)

    def test_corrupt_snapshot_fails_closed_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'search';shutil.copytree(DIST/'search',src)
            (src/'floors.json').write_text('{}', encoding="utf-8")
            output=Path(tmp)/'dist';output.mkdir();(output/'keep.txt').write_text('not generated', encoding="utf-8")
            with self.assertRaisesRegex(ValueError,'non-package'):build(DIST/'map',src,output)
            self.assertEqual((output/'keep.txt').read_text(encoding="utf-8"),'not generated')
            with self.assertRaisesRegex(ValueError,'hash/size'):build(DIST/'map',src,Path(tmp)/'new')
            self.assertFalse((Path(tmp)/'new').exists())


    def test_optional_context_and_detail_paths_are_prefixed_and_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'map';shutil.copytree(DIST/'map',source)
            m=read(source/'manifest.json')
            # Fixture reuses a verified GLB; production geometry belongs to the producer.
            m['context_mesh_url']=m['campus_mesh_url']
            m['context_local_geojson_url']=m['local_geojson_url']
            m['context']={'tree_geometry_included':False}
            m['buildings'][0]['detail_mesh_url']=m['buildings'][0]['mesh_url']
            m['buildings'][0]['detail_report_url']='source-regions.json'
            m['version']=hashlib.sha256(canonical({k:v for k,v in m.items() if k!='version'})).hexdigest()
            (source/'manifest.json').write_bytes(canonical(m)+b'\n')
            out=build(source,DIST/'search',root/'dist')
            self.assertEqual(out['context_mesh_url'],'map/'+m['campus_mesh_url'])
            self.assertEqual(out['context_local_geojson_url'],'map/'+m['local_geojson_url'])
            self.assertEqual(out['buildings'][0]['detail_mesh_url'],'map/'+m['buildings'][0]['mesh_url'])
            self.assertEqual(out['buildings'][0]['detail_report_url'],'map/source-regions.json')
            self.assertEqual({b['building_id'] for b in out['buildings']},{b['building_id'] for b in self.manifest['buildings']})
            m['buildings'][0]['detail_mesh_url']='not-hash-listed.glb'
            m['version']=hashlib.sha256(canonical({k:v for k,v in m.items() if k!='version'})).hexdigest()
            (source/'manifest.json').write_bytes(canonical(m)+b'\n')
            with self.assertRaisesRegex(ValueError,'Unverified map building resource'):
                load_sources(source,DIST/'search')

    def test_manifest_and_path_tampering_rejected(self):
        m=read(DIST/'search/manifest.json');m['building_count']+=1
        with self.assertRaises(ValueError):verify_manifest(m,PIN)
        for relative in ['../outside.json','/tmp/absolute.json','..\\outside.json']:
            with self.assertRaises(ValueError):path_in(DIST,relative)
        with self.assertRaises(ValueError):build(DIST/'map',DIST/'search',DIST)

    def test_native_manifest_is_hash_listed_and_content_addressed(self):
        original=read(DIST/'map/manifest.json')
        native=original['source'].get('native_blender') or {}
        if not native.get('manifest_url'):
            self.skipTest('This explicit lightweight fixture has no native detail package')
        relative=native['manifest_url']
        self.assertIn(relative,original['artifacts'])
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'map';shutil.copytree(DIST/'map',source)
            missing=copy.deepcopy(original)
            missing['artifacts'].pop(relative)
            missing['version']=hashlib.sha256(canonical({k:v for k,v in missing.items() if k!='version'})).hexdigest()
            (source/'manifest.json').write_bytes(canonical(missing)+b'\n')
            with self.assertRaisesRegex(ValueError,'Unverified native detail manifest'):
                load_sources(source,DIST/'search')
            mismatched=copy.deepcopy(original)
            mismatched['source']['native_blender']['package_version']='0'*64
            mismatched['version']=hashlib.sha256(canonical({k:v for k,v in mismatched.items() if k!='version'})).hexdigest()
            (source/'manifest.json').write_bytes(canonical(mismatched)+b'\n')
            with self.assertRaisesRegex(ValueError,'Native detail manifest identity/source mismatch'):
                load_sources(source,DIST/'search')

    def test_rehashed_reference_geometry_cannot_enter_public_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'search';shutil.copytree(DIST/'search',root)
            manifest=read(root/'manifest.json')
            ref=manifest['artifacts']['floors']
            doc=read(root/ref['path'])
            doc['floors'][0]['outline']=[[0,0],[1,0],[1,1],[0,0]]
            raw=canonical(doc)+b'\n';(root/ref['path']).write_bytes(raw)
            ref.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            manifest['snapshot_id']=hashlib.sha256(canonical({k:v for k,v in manifest.items() if k!='snapshot_id'})).hexdigest()
            (root/'manifest.json').write_bytes(canonical(manifest)+b'\n')
            with self.assertRaisesRegex(ValueError,'Reference geometry'):
                project(root)

if __name__=='__main__':unittest.main()

class RoomStateOverlayContracts(unittest.TestCase):
    def test_all_room_state_binding_keys_are_exact_source_ids(self):
        manifest=read(DIST/'manifest.json')
        index=read(DIST/manifest['room_spatial_index_url'])
        seed=read(DIST/'seed.json')
        self.assertEqual(index['format'],'carbentra-room-spatial-index')
        self.assertEqual(index['source_version'],seed['source_version'])
        self.assertEqual(index['binding_key'],'space_id')
        self.assertEqual(len(index['spaces']),603)
        self.assertEqual({r['space_id'] for r in index['spaces']},{r['id'] for r in seed['spaces']})
        for room in index['spaces']:
            self.assertNotIn('occupancy',room)
            self.assertNotIn('power_w',room)
            g=room['display_geometry']
            self.assertIsNone(g['metric_transform'])
            self.assertEqual(g['feature_id'],room['space_id'])
            if g['resource']:
                plan=read(DIST/g['resource'])
                self.assertEqual(plan['floor_id'],room['floor_id'])
                self.assertIn(room['space_id'],{r['space_id'] for r in plan['space_units']})
            for r in room['source_regions']:
                self.assertEqual(r['geometry_status'],'not_published_reference_geometry')
                self.assertNotIn('bounds_normalized',r)
                self.assertNotIn('coordinate_frame',r)
                self.assertEqual(r['binding_status'],'explicit_evidence_reference')
