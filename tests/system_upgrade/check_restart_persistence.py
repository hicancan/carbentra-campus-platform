"""Read-only API evidence after operators restart the disposable Docker API."""
import argparse,json
from pathlib import Path
from http.cookiejar import CookieJar
from urllib.parse import urlparse
from urllib.request import build_opener,HTTPCookieProcessor,ProxyHandler,Request
p=argparse.ArgumentParser()
p.add_argument('--summary',type=Path,required=True)
p.add_argument('--base-url',default='http://127.0.0.1:8080')
a=p.parse_args()
url=urlparse(a.base_url)
assert url.scheme=='http' and url.hostname in {'localhost','127.0.0.1'} and not url.username and not url.password
summary=json.loads(a.summary.read_text(encoding='utf-8'))
client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
base=a.base_url.rstrip('/')+'/api/v1'
with client.open(Request(base+'/auth/login',data=json.dumps({'username':'admin','password':'development-only'}).encode(),headers={'Content-Type':'application/json'}),timeout=180) as r:assert r.status==200

def get(route):
 with client.open(base+route,timeout=300) as r:assert r.status==200;return json.load(r)['data']
checks=[]
for row in summary['checks']:
 detail=row.get('detail') or {}
 if row['status']!='passed':continue
 if 'evaluationId' in detail:
  result=get('/classrooms/evaluations/'+detail['evaluationId']);assert result['id']==detail['evaluationId'] and result['command_ids']==[]
  checks.append({'kind':'saved_shadow_evaluation','id':result['id'],'commands':result['command_ids'],'persisted':True})
 if 'commandId' in detail:
  result=get('/commands/'+detail['commandId']);assert result['status']=='acknowledged_unverified' and result['result'] is None and result['channel_id']==detail['channelId']
  checks.append({'kind':'channel_command','id':result['id'],'channel_id':result['channel_id'],'status':result['status'],'physical_result':result['result'],'persisted':True})
assert any(c['kind']=='saved_shadow_evaluation' for c in checks)
print(json.dumps({'passed':True,'scope':'Read-only actual API after container restart; no credential material retained','checks':checks,'command_check': 'passed' if any(c['kind']=='channel_command' for c in checks) else 'not_run_no_successful_browser_command'},indent=2))
