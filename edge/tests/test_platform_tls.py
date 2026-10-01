"""Local HTTPS proof: explicit private CA via SSL_CERT_FILE, name verification,
no CA bypass, no redirects and no implicit environment proxy. Ephemeral test
keys never leave a temporary directory and are deleted when the test exits.
"""
import datetime
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import os
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from platform_http import PlatformHTTP

class PlatformTLSTests(unittest.TestCase):
 def test_private_ca_hostname_and_no_redirect_proxy(self):
  key=ec.generate_private_key(ec.SECP256R1());leaf_key=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc);day=datetime.timedelta(days=1)
  subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Ephemeral local transport CA')])
  ca=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-day).not_valid_after(now+day).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256())
  leaf=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])).issuer_name(subject).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-day).not_valid_after(now+day).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]),critical=False).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).sign(key,hashes.SHA256())
  seen=[]
  class Handler(BaseHTTPRequestHandler):
   def do_GET(self):
    seen.append((self.path,self.headers.get('Authorization')))
    if self.path=='/api/v1/redirect':
     self.send_response(302);self.send_header('Location','/api/v1/destination');self.end_headers();return
    payload=json.dumps({'data':'private TLS verified'}).encode();self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
   def log_message(self,*_):pass
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ca_path=root/'ca.crt';cert_path=root/'server.crt';key_path=root/'test-only.key'
   ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM));cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM));key_path.write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));key_path.chmod(0o600)
   server=HTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert_path,key_path);server.socket=context.wrap_socket(server.socket,server_side=True)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    url='https://localhost:'+str(server.server_port);http=PlatformHTTP(url,'ephemeral-test-only')
    with patch.dict(os.environ,{'SSL_CERT_FILE':str(root/'absent.crt')}):
     with self.assertRaises(OSError):http.request('GET','/api/v1/probe')
    with patch.dict(os.environ,{'SSL_CERT_FILE':str(ca_path),'HTTPS_PROXY':'http://127.0.0.1:1','https_proxy':'http://127.0.0.1:1'}):
     self.assertEqual(http.request('GET','/api/v1/probe'),{'data':'private TLS verified'})
     with self.assertRaises(OSError):PlatformHTTP('https://127.0.0.1:'+str(server.server_port),'ephemeral-test-only').request('GET','/api/v1/probe')
     with self.assertRaises(ValueError):http.request('GET','/api/v1/redirect')
    self.assertEqual(seen,[('/api/v1/probe','Bearer ephemeral-test-only'),('/api/v1/redirect','Bearer ephemeral-test-only')])
   finally:server.shutdown();server.server_close();thread.join(timeout=5)
  self.assertFalse(key_path.exists())

if __name__=='__main__':unittest.main()
