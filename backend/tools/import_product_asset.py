"""Single three-family reference publisher; optional quantization is hash-bound."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FAMILIES={
 'PLUG':{'name':'CARBENTRA Plug Rev B','model':'visuals/rev_b/exports/carbentra_twin_light.glb','hero':'visuals/rev_b/renders/01_hero_ivory.png','manifest':'manifest.json','display':'carbentra-plug-reference.glb','hero_file':'plug-hero.png','repository':'https://github.com/hicancan/carbentra-smart-plug'},
 'SWITCH':{'name':'CARBENTRA Switch','model':'mechanical/exports/carbentra_smart_switch.glb','hero':'presentation/model_01_exterior_hero_light.png','manifest':'switch.manifest.json','display':'carbentra-switch-reference.glb','hero_file':'switch-hero.png','repository':'carbentra-smart-switch'},
 'PRESENCE':{'name':'CARBENTRA Sense B','model':'mechanical/exports/carbentra_presence_sensor.glb','hero':'visuals/01_exterior_hero.png','manifest':'sense.manifest.json','display':'carbentra-sense-reference.glb','hero_file':'sense-hero.png','repository':'carbentra-presence-sensor'},
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def metadata(path):
    with path.open('rb') as stream:
        magic,version,size=struct.unpack('<4sII',stream.read(12))
        length,kind=struct.unpack('<I4s',stream.read(8))
        if magic!=b'glTF' or version!=2 or size!=path.stat().st_size or kind!=b'JSON' or length>2*1024*1024:
            raise ValueError('Invalid GLB container/metadata')
        data=json.loads(stream.read(length))
    nodes,meshes,accessors=data.get('nodes',[]),data.get('meshes',[]),data.get('accessors',[])
    if len({node.get('name') for node in nodes})!=len(nodes) or any(not node.get('name') for node in nodes):
        raise ValueError('Display parts require unique source node names')
    if any(buffer.get('uri') for buffer in data.get('buffers',[])) or data.get('images') or data.get('textures'):
        raise ValueError('This pinned product must remain self-contained geometry without external resources')
    triangles=0
    for mesh in meshes:
        for primitive in mesh.get('primitives',[]):
            if primitive.get('mode',4)!=4:
                raise ValueError('Unexpected primitive mode')
            accessor=primitive.get('indices',primitive.get('attributes',{}).get('POSITION'))
            triangles+=accessors[accessor]['count']//3
    return data,triangles


def validate_promotion(source_hash,display_hash,source_bytes,display_bytes,optimization,validation,khronos):
    if not display_bytes<source_bytes:
        raise ValueError('Optimized display must be smaller than its source')
    for report in (optimization,validation):
        if report.get('source_sha256')!=source_hash or report.get('display_sha256')!=display_hash:
            raise ValueError('Source/display report hashes do not bind these bytes')
    if optimization.get('tool')!='@gltf-transform/functions' or optimization.get('operation')!='quantize' or optimization.get('physical_geometry_claim') is not False:
        raise ValueError('Unexpected optimization operation or geometry claim')
    if optimization.get('options')!={'quantizePosition':16,'quantizeNormal':16,'quantizationVolume':'mesh','cleanup':False,'pattern':'^(POSITION|NORMAL)$'}:
        raise ValueError('Quantization settings differ from reviewed display-only settings')
    if validation.get('status')!='passed' or any(validation.get(key) is not True for key in ('topology_unchanged','part_ids_unchanged','materials_unchanged','extras_unchanged')) or validation.get('physical_geometry_claim') is not False:
        raise ValueError('Independent part/material/topology invariants failed')
    for field,limit in [('max_world_position_error_m',1e-5),('max_world_bounds_error_m',1e-5),('max_world_normal_error_degrees',.01)]:
        value=validation.get(field)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=limit:
            raise ValueError('Independent numerical tolerance failed')
    if khronos.get('status')!='passed' or khronos.get('candidate_sha256')!=display_hash or khronos.get('candidate_bytes')!=display_bytes:
        raise ValueError('Khronos execution report is not bound to this candidate')
    issues=khronos.get('report',{}).get('issues',{})
    if any(type(issues.get(key)) is not int or issues[key]!=0 for key in ('numErrors','numWarnings')) or issues.get('truncated') is not False:
        raise ValueError('Khronos validation has errors/warnings or a truncated report')


def main():
    from PIL import Image, __version__ as pillow_version
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--family',required=True,choices=sorted(FAMILIES))
    options=parser.add_mutually_exclusive_group()
    options.add_argument('--optimized-candidate',type=Path)
    options.add_argument('--optimize',action='store_true',help='Invoke the pinned offline optimizer and both validators')
    parser.add_argument('--reports',type=Path,help='Directory containing optimization.json, validation.json and khronos-bound-validation.json')
    parser.add_argument('--validator-python',default=sys.executable,help='Workspace interpreter with the root assets dependency group installed')
    args=parser.parse_args();source=args.source.resolve();spec=FAMILIES[args.family];relative=Path(spec['model']);model=source/relative;hero=source/spec['hero']
    source_data,triangles=metadata(model);source_hash=digest(model)
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--',str(relative),spec['hero']],text=True).strip():
        raise SystemExit('Source display artifact has uncommitted changes; pin it before import')
    if hero.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':raise ValueError('Reference hero must be a PNG')
    target=ROOT/'packages/product/dist';target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='carbentra-product-import-') as work:
        work=Path(work);candidate=args.optimized_candidate;reports=args.reports
        hero_display=work/'hero.png'
        with Image.open(hero) as original:
            source_hero_size=list(original.size)
            thumb=original.convert('RGBA');thumb.thumbnail((640,640),Image.Resampling.LANCZOS)
            hero_size=list(thumb.size);thumb.save(hero_display,format='PNG',optimize=True,compress_level=9)
        if args.optimize:
            tools=ROOT/'packages/product/tools';candidate=work/'candidate.glb';reports=work
            subprocess.run(['node','--max-old-space-size=512',str(tools/'optimize-display.mjs'),'--source',str(model),'--output',str(candidate),'--report',str(work/'optimization.json'),'--expected-sha256',source_hash],check=True)
            subprocess.run([args.validator_python,str(tools/'validate-display.py'),'--source',str(model),'--candidate',str(candidate),'--report',str(work/'validation.json')],check=True)
            subprocess.run(['node','--max-old-space-size=512',str(tools/'validate-khronos.mjs'),'--candidate',str(candidate),'--report',str(work/'khronos-bound-validation.json')],check=True)
        display=candidate.resolve() if candidate else model
        data,display_triangles=metadata(display);display_hash=digest(display);optimization_info=None
        if candidate:
            if not reports:
                raise SystemExit('An optimized candidate requires all three hash-bound validation reports')
            docs={name:json.loads((reports/name).read_text(encoding="utf-8")) for name in ('optimization.json','validation.json','khronos-bound-validation.json')}
            validate_promotion(source_hash,display_hash,model.stat().st_size,display.stat().st_size,*docs.values())
            if [node['name'] for node in source_data['nodes']]!=[node['name'] for node in data['nodes']] or triangles!=display_triangles or data.get('materials')!=source_data.get('materials'):
                raise SystemExit('Candidate metadata changes source part order, topology counts or PBR materials')
            if set(data.get('extensionsRequired',[]))-{'KHR_mesh_quantization'}:
                raise SystemExit('Candidate requires an unreviewed decoder/extension')
            evidence=target/'reports';evidence.mkdir(exist_ok=True)
            references={}
            for name,doc in docs.items():
                (evidence/name).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding="utf-8")
                references[name]={'path':'reports/'+name,'sha256':digest(evidence/name)}
            validation=docs['validation.json']
            optimization_info={'tool':docs['optimization.json']['tool'],'tool_version':docs['optimization.json']['tool_version'],
                'options':docs['optimization.json']['options'],'source_bytes':model.stat().st_size,'bytes_saved':model.stat().st_size-display.stat().st_size,
                'position_tolerance_m':1e-5,'normal_tolerance_degrees':.01,
                'max_world_position_error_m':validation['max_world_position_error_m'],'max_world_bounds_error_m':validation['max_world_bounds_error_m'],
                'max_world_normal_error_degrees':validation['max_world_normal_error_degrees'],'reports':references,'geometry_qualification':False}
        nodes,meshes=data.get('nodes',[]),data.get('meshes',[])
        manifest={'version':2,'family':args.family,'product_name':spec['name'],'name':spec['name']+' · Engineering reference','source_mode':'REFERENCE',
            'source_repository':spec['repository'],'source_commit':commit,'source_path':relative.as_posix(),
            'source_sha256':source_hash,'display_sha256':display_hash,'model_url':'/api/v1/assets/product/model?family='+args.family,'hero_url':'/api/v1/assets/product/hero?family='+args.family,'hero_sha256':digest(hero_display),'hero_bytes':hero_display.stat().st_size,'source_hero_path':spec['hero'],'source_hero_sha256':digest(hero),'source_hero_bytes':hero.stat().st_size,'hero_derivation':{'operation':'bounded_thumbnail','max_dimension_px':640,'resampling':'LANCZOS','tool':'Pillow '+pillow_version,'source_size_px':source_hero_size,'size_px':hero_size},'bytes':display.stat().st_size,
            'source_bytes':model.stat().st_size,'mime':'model/gltf-binary','units':'m','axis':'Y-up','node_count':len(nodes),'mesh_count':len(meshes),'triangle_count':triangles,
            'parts':[{'id':node['name'],'name':node['name'],'node_index':index,'provenance':node.get('extras',{})} for index,node in enumerate(nodes)],
            'optimized':bool(candidate),'optimization':optimization_info,'materials_preserved':True,'extensions':data.get('extensionsUsed',[]),
            'physical_qualification':False,'device_binding':False,
            'provenance':'Validated loss-bounded display quantization of the pinned source; authoritative CAD/ECAD remains upstream' if candidate else 'Byte-identical display artifact from the pinned source; authoritative CAD/ECAD remains upstream',
            'license':'No repository-wide redistribution license was declared in the inspected source; review before external redistribution',
            'limitations':['Product reference only; not the placement of a registered device','Engineering development; physical verification remains pending',
                'No mains safety, calibration or voltage-absence proof','Optional display asset; load only after an explicit user action','No frame-rate or browser-memory claim without a measured viewer test']}
        staged_model=target/'.display-import.tmp'
        shutil.copyfile(display,staged_model);staged_model.replace(target/spec['display'])
        staged_manifest=target/'.manifest-import.tmp'
        staged_manifest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n', encoding="utf-8");staged_manifest.replace(target/spec['manifest'])
        staged_hero=target/'.hero-import.tmp';shutil.copyfile(hero_display,staged_hero);staged_hero.replace(target/spec['hero_file'])
        catalog_path=target/'catalog.json'
        catalog=json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {'schema_version':1,'format':'carbentra-product-catalog','products':{}}
        catalog['products'][args.family]={'manifest':spec['manifest'],'model':spec['display'],'hero':spec['hero_file']}
        staged_catalog=target/'.catalog-import.tmp';staged_catalog.write_text(json.dumps(catalog,ensure_ascii=False,sort_keys=True,indent=2)+'\n', encoding="utf-8");staged_catalog.replace(catalog_path)
    print(json.dumps({'family':args.family,'bytes':manifest['bytes'],'nodes':manifest['node_count'],'triangles':triangles,'display_sha256':display_hash,'source_sha256':source_hash,'optimized':manifest['optimized'],'source_commit':commit}))


if __name__=='__main__':
    main()
