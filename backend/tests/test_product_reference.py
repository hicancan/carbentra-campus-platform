import hashlib
import json
from pathlib import Path


def test_product_artifacts_are_authenticated_and_optional(app,admin,tmp_path):
    application,client=app
    client.post('/api/v1/auth/logout',headers=admin[1])
    assert client.get('/api/v1/assets/product/manifest?family=PLUG').status_code==401
    assert client.get('/api/v1/assets/product/model?family=PLUG').status_code==401
    login=client.post('/api/v1/auth/login',json={'username':'viewer','password':'development-only'})
    assert login.status_code==200
    application.state.settings.product_asset_dir=tmp_path
    assert client.get('/api/v1/assets/product/manifest?family=PLUG').status_code==503
    assert client.get('/api/v1/assets/product/model?family=PLUG').status_code==503
    model=b'glTF' + b'fixture-only'
    hero=b'\x89PNG\r\n\x1a\nfixture-only'
    manifest={'family':'PLUG','product_name':'Plug fixture','model_url':'/api/v1/assets/product/model?family=PLUG','hero_url':'/api/v1/assets/product/hero?family=PLUG','hero_bytes':len(hero),'hero_sha256':hashlib.sha256(hero).hexdigest(),'bytes':len(model),'display_sha256':hashlib.sha256(model).hexdigest(),'source_mode':'REFERENCE','device_binding':False,'physical_qualification':False}
    (tmp_path/'carbentra-plug-reference.glb').write_bytes(model)
    (tmp_path/'manifest.json').write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path/'plug-hero.png').write_bytes(hero)
    (tmp_path/'catalog.json').write_text(json.dumps({'format':'carbentra-product-catalog','schema_version':1,'products':{'PLUG':{'manifest':'manifest.json','model':'carbentra-plug-reference.glb','hero':'plug-hero.png'}}}), encoding="utf-8")
    response=client.get('/api/v1/assets/product/manifest?family=PLUG')
    assert response.status_code==200 and response.json()['data']==manifest
    response=client.get('/api/v1/assets/product/model?family=PLUG')
    assert response.status_code==200 and response.content==model
    assert response.headers['content-type']=='model/gltf-binary'
    assert response.headers['etag']=='"'+manifest['display_sha256']+'"'
    assert client.get('/api/v1/assets/product/hero?family=PLUG').content==hero
    assert client.get('/api/v1/assets/product/model').status_code==422
    assert client.get('/api/v1/assets/product/model?family=UNKNOWN').status_code==422
    (tmp_path/'carbentra-plug-reference.glb').write_bytes(b'broken')
    assert client.get('/api/v1/assets/product/model?family=PLUG').status_code==503


def test_pinned_display_package_matches_producer_and_preserves_part_identity():
    root=Path(__file__).resolve().parents[2]/'packages/product/dist'
    manifest=json.loads((root/'manifest.json').read_text(encoding="utf-8"))
    with (root/'carbentra-plug-reference.glb').open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==manifest['display_sha256']
    assert manifest['source_bytes']==30337768 and manifest['bytes']==22318016 and manifest['node_count']==227 and manifest['triangle_count']==666556
    assert manifest['source_sha256']=='dc25e3965a9e653eb5c91a4514fcc1a3e051ffa47593778d7e70a71071e439d0'
    assert len({part['id'] for part in manifest['parts']})==227
    assert manifest['materials_preserved'] and manifest['optimized']
    for reference in manifest['optimization']['reports'].values():
        assert hashlib.sha256((root/reference['path']).read_bytes()).hexdigest()==reference['sha256']
    assert not manifest['physical_qualification'] and not manifest['device_binding']


def test_importer_rejects_unbound_or_failed_optimization_evidence():
    import importlib.util,copy
    path=Path(__file__).resolve().parents[1]/'tools/import_product_asset.py'
    spec=importlib.util.spec_from_file_location('product_importer',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=Path(__file__).resolve().parents[2]/'packages/product/dist'
    manifest=json.loads((root/'manifest.json').read_text(encoding="utf-8"))
    names=['optimization.json','validation.json','khronos-bound-validation.json']
    reports=[json.loads((root/'reports'/name).read_text(encoding="utf-8")) for name in names]
    args=(manifest['source_sha256'],manifest['display_sha256'],manifest['source_bytes'],manifest['bytes'])
    module.validate_promotion(*args,*reports)
    import pytest
    for index,key,value in [(0,'display_sha256','wrong'),(1,'materials_unchanged',False),(1,'max_world_position_error_m',1.0),(2,'candidate_sha256','wrong')]:
        changed=copy.deepcopy(reports);changed[index][key]=value
        with pytest.raises(ValueError):module.validate_promotion(*args,*changed)


def test_three_families_have_distinct_authenticated_verified_assets(app,admin):
    _,client=app
    hashes=set()
    for family in ('PLUG','SWITCH','PRESENCE'):
        response=client.get('/api/v1/assets/product/manifest',params={'family':family})
        assert response.status_code==200,response.text
        manifest=response.json()['data']
        assert manifest['family']==family and manifest['source_mode']=='REFERENCE'
        hero=client.get(manifest['hero_url'])
        assert hero.status_code==200 and hero.content.startswith(b'\x89PNG\r\n\x1a\n')
        assert hashlib.sha256(hero.content).hexdigest()==manifest['hero_sha256']
        model=client.get(manifest['model_url'])
        assert model.status_code==200 and hashlib.sha256(model.content).hexdigest()==manifest['display_sha256']
        hashes.add(manifest['display_sha256'])
    assert len(hashes)==3
