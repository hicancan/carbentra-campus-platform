#!/usr/bin/env python3
"""Authenticated HTTP identity/compression proof for all three pinned product families.

Local development fixtures only. No authentication headers, cookies or asset bytes
are persisted. This is not a browser WebGL/rendering claim.
"""
import argparse,gzip,hashlib,json
from http.cookiejar import CookieJar
from urllib.parse import urlparse
from urllib.request import build_opener,HTTPCookieProcessor,ProxyHandler,Request
from urllib.error import HTTPError
p=argparse.ArgumentParser()
p.add_argument('--base-url',default='http://127.0.0.1:8080')
p.add_argument('--development-fixture',required=True,action='store_true')
p.add_argument('--require-gzip',action='store_true')
a=p.parse_args();base=a.base_url.rstrip('/');url=urlparse(base)
assert url.scheme=='http' and url.hostname in {'127.0.0.1','localhost','::1'} and not url.username and not url.password
client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
def get(route,headers=None):
    with client.open(Request(base+route,headers=headers or {}),timeout=300) as r:return r.read(),r.headers

def rejected(route,status):
    try:get(route)
    except HTTPError as e:assert e.code==status,(route,e.code)
    else:raise AssertionError('Unexpectedly accepted '+route)

for family in ('PLUG','SWITCH','PRESENCE'):
    rejected('/api/v1/assets/product/manifest?family='+family,401)
with client.open(Request(base+'/api/v1/auth/login',data=json.dumps({'username':'admin','password':'development-only'}).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=120) as response:assert response.status==200
raw,headers=get('/api/v1/system/status',{'Accept-Encoding':'gzip'});status=json.loads(raw)['data']
assert not headers.get('Content-Encoding') and status['mode'] in {'development','test'} and not status['physical_control']['enabled']
rejected('/api/v1/assets/product/model',422)
rejected('/api/v1/assets/product/model?family=UNKNOWN',422)
results=[]
for family in ('PLUG','SWITCH','PRESENCE'):
    raw,headers=get('/api/v1/assets/product/manifest?family='+family,{'Accept-Encoding':'gzip'})
    assert not headers.get('Content-Encoding'),'Authenticated manifest JSON compressed'
    manifest=json.loads(raw)['data'];assert manifest['family']==family and manifest['source_mode']=='REFERENCE'
    row={'family':family,'source_commit':manifest['source_commit'],'model':{},'hero':{}}
    for kind,bytes_key,hash_key in [('model','bytes','display_sha256'),('hero','hero_bytes','hero_sha256')]:
        route=manifest[kind+'_url'];assert route=='/api/v1/assets/product/'+kind+'?family='+family
        wire,headers=get(route,{'Accept-Encoding':'gzip'});encoding=headers.get('Content-Encoding','identity')
        assert encoding in {'identity','gzip'}
        if a.require_gzip and kind=='model':
            assert encoding=='gzip','Model gzip negotiation failed'
            assert 'accept-encoding' in headers.get('Vary','').lower()
        decoded=gzip.decompress(wire) if encoding=='gzip' else wire
        assert len(decoded)==manifest[bytes_key]
        digest=hashlib.sha256(decoded).hexdigest();assert digest==manifest[hash_key]
        assert decoded.startswith(b'glTF' if kind=='model' else b'\x89PNG\r\n\x1a\n')
        cache_control=','.join(headers.get_all('Cache-Control',[])).lower()
        assert 'public' not in cache_control and ('private' in cache_control or 'no-store' in cache_control)
        row[kind]={'content_type':headers.get('Content-Type'),'content_encoding':encoding,'wire_bytes':len(wire),'decoded_bytes':len(decoded),'sha256':digest,'manifest_match':True,'cache_control':cache_control}
    results.append(row)
print(json.dumps({'passed':True,'families':results,'authenticated_json_compressed':False,'missing_and_unknown_family_rejected':True,'anonymous_manifest_rejected':True,'fixture_only':True,'browser_rendering_claim':False},indent=2))
