"""Optional signed-time bootstrap for cold devices before TLS certificate validation.
Run only with an operator-supplied P-256 private key and an independently managed
accurate host clock. This creates no keys, identities, permissions or credentials.
The device must have the matching public key installed through commissioning.
"""
import argparse
import base64
import json
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

NONCE = re.compile(r'^[0-9a-f]{32}$')


def sign_time(nonce, unix_s, key):
    if not isinstance(nonce,str) or not NONCE.fullmatch(nonce):
        raise ValueError('invalid public challenge')
    if type(unix_s) is not int or not 1700000000 <= unix_s < 4102444800:
        raise ValueError('host time is not plausible')
    if not isinstance(key,ec.EllipticCurvePrivateKey) or not isinstance(key.curve,ec.SECP256R1):
        raise ValueError('P-256 signing key required')
    message=f'CARBENTRA_TIME_V1\n{nonce}\n{unix_s}\n'.encode('ascii')
    signature=key.sign(message,ec.ECDSA(hashes.SHA256()))
    return {'nonce':nonce,'unix_s':unix_s,'signature':base64.b64encode(signature).decode('ascii')}


def serve(address, port, key):
    from service import strict_json
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if self.path != '/time' or not 1 <= length <= 128 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('invalid request')
                request=strict_json(self.rfile.read(length))
                if not isinstance(request,dict) or set(request) != {'nonce'}:
                    raise ValueError('invalid challenge')
                payload=json.dumps(sign_time(request['nonce'],int(time.time()),key),separators=(',',':')).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
            except (ValueError,UnicodeError):
                self.send_error(400,'Invalid time challenge')
        def log_message(self,*_):
            pass
        def setup(self):
            super().setup();self.connection.settimeout(2)
    HTTPServer((address,port),Handler).serve_forever()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-key',required=True);parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--port',type=int,default=8087)
    args=parser.parse_args();path=Path(args.private_key)
    if path.stat().st_mode & 0o077:
        raise SystemExit('Signing key must not be group/world accessible; provision permissions separately')
    key=serialization.load_pem_private_key(path.read_bytes(),password=None)
    sign_time('0'*32,int(time.time()),key)  # Fail closed on incorrect type or clock.
    serve(args.bind,args.port,key)

if __name__ == '__main__':
    main()
