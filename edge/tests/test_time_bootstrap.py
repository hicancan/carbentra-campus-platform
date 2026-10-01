import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from time_bootstrap import sign_time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

class SignedTimeTests(unittest.TestCase):
    def setUp(self):
        # Ephemeral in-memory test keys only. Never saved or used as device credentials.
        self.key=ec.generate_private_key(ec.SECP256R1());self.nonce='ab'*16
    def test_signer_rejects_invalid_inputs(self):
        for nonce,stamp in [('A'*32,1800000000),('f'*31,1800000000),(self.nonce,0),(self.nonce,True)]:
            with self.assertRaises(ValueError):sign_time(nonce,stamp,self.key)
        with self.assertRaises(ValueError):sign_time(self.nonce,1800000000,ec.generate_private_key(ec.SECP384R1()))
    def test_real_firmware_crypto(self):
        executable=os.environ.get('CARBENTRA_TIME_TEST_BINARY')
        if not executable:self.skipTest('real C verifier executable not supplied; separately required crypto gate')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);pub=root/'public.txt';response=root/'response.json'
            pub.write_bytes(self.key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
            valid=sign_time(self.nonce,1800000000,self.key)
            def run(message,nonce=self.nonce,elapsed='1000'):
                response.write_text(message if isinstance(message,str) else json.dumps(message), encoding="utf-8")
                return subprocess.run([executable,str(pub),str(response),nonce,elapsed],capture_output=True).returncode
            self.assertEqual(run(valid),0)
            self.assertEqual(run(valid,elapsed='2000'),0)
            self.assertEqual(run(valid,elapsed='2001'),1)
            self.assertEqual(run(valid,nonce='cd'*16),1)
            self.assertEqual(run({**valid,'unix_s':1800000001}),1)
            self.assertEqual(run({**valid,'signature':base64.b64encode(b'bad').decode()}),1)
            self.assertEqual(run(json.dumps(valid)[:-1]+',"unix_s":1800000000}'),1)
            self.assertEqual(run({**valid,'extra':1}),1)
            self.assertEqual(run({**valid,'unix_s':1e300}),1)
            self.assertEqual(run(sign_time(self.nonce,1800000000,ec.generate_private_key(ec.SECP256R1()))),1)
            pub.write_bytes(ec.generate_private_key(ec.SECP384R1()).public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
            self.assertEqual(run(valid),1)

if __name__ == '__main__':unittest.main()
