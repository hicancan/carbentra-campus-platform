"""Single authenticated HTTP boundary, with no redirects or implicit proxy use."""
import urllib.parse
import urllib.request
from service import strict_json

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*_args,**_kwargs):raise ValueError('redirect refused')

class PlatformHTTP:
    def __init__(self,origin,token):
        parsed=urllib.parse.urlsplit(origin)
        if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'','/'}:
            raise ValueError('platform origin required')
        if parsed.scheme != 'https' and parsed.hostname not in {'localhost','127.0.0.1','::1'}:
            raise ValueError('HTTPS required outside loopback')
        if not isinstance(token,str) or not token or any(c in token for c in '\r\n'):
            raise ValueError('explicit operator adapter token required')
        self.origin=origin.rstrip('/');self.token=token
    def request(self,method,path,payload=None):
        if not path.startswith('/api/v1/') or '://' in path:raise ValueError('invalid API route')
        request=urllib.request.Request(self.origin+path,data=None if payload is None else payload.encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'},method=method)
        opener=urllib.request.build_opener(NoRedirect(),urllib.request.ProxyHandler({}))
        with opener.open(request,timeout=5) as response:
            if response.status not in {200,201}:raise ValueError('unexpected platform status')
            data=response.read(32769)
        return strict_json(data,maximum=32768)
