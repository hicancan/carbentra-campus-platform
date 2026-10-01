"""Public-certificate-only host proof of mbedTLS date/CA/hostname enforcement."""
import datetime
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

class CertificateTests(unittest.TestCase):
 def test_dates_ca_and_hostname(self):
  executable=os.environ.get('CARBENTRA_CERT_TEST_BINARY')
  if not executable:self.skipTest('real C certificate verifier not supplied; separately required crypto gate')
  now=datetime.datetime.now(datetime.timezone.utc);day=datetime.timedelta(days=1)
  key=ec.generate_private_key(ec.SECP256R1());name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Ephemeral host-test CA')])
  def root_for(k):return x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(k.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-day).not_valid_after(now+day*365).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(k,hashes.SHA256())
  ca=root_for(key)
  def leaf(start,end):return x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'broker.test.invalid')])).issuer_name(name).public_key(ec.generate_private_key(ec.SECP256R1()).public_key()).serial_number(x509.random_serial_number()).not_valid_before(start).not_valid_after(end).add_extension(x509.SubjectAlternativeName([x509.DNSName('broker.test.invalid')]),critical=False).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).sign(key,hashes.SHA256())
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/'ca.txt';target=Path(directory)/'leaf.txt';root.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
   def check(cert,host='broker.test.invalid'):
    target.write_bytes(cert.public_bytes(serialization.Encoding.PEM));return subprocess.run([executable,str(root),str(target),host],capture_output=True,text=True)
   self.assertEqual(check(leaf(now-day,now+day)).returncode,0)
   expired=check(leaf(now-day*2,now-day));self.assertEqual(expired.returncode,1);self.assertNotEqual(int(expired.stdout.strip().split('=')[1])&1,0)
   future=check(leaf(now+day,now+day*2));self.assertEqual(future.returncode,1);self.assertNotEqual(int(future.stdout.strip().split('=')[1])&512,0)
   self.assertEqual(check(leaf(now-day,now+day),'wrong.test.invalid').returncode,1)
   root.write_bytes(root_for(ec.generate_private_key(ec.SECP256R1())).public_bytes(serialization.Encoding.PEM));self.assertEqual(check(leaf(now-day,now+day)).returncode,1)

if __name__=='__main__':unittest.main()
