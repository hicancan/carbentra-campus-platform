"""Small independent synthetic fixtures; no real product model or actuator is loaded."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import numpy as np
spec = importlib.util.spec_from_file_location('validator', Path(__file__).with_name('validate-display.py'))
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def fixture(quantized=False):
    positions = np.tile(np.array([[0,0,0], [1,0,0], [0,1,0]], dtype=float), (100, 1))
    normals = np.tile(np.array([[0,0,1]], dtype=float), (300, 1))
    arrays = [positions * (32767 if quantized else .1), normals * (32767 if quantized else 1)]
    binary = bytearray()
    views, accessors = [], []
    for array in arrays:
        dtype = np.dtype('<i2' if quantized else '<f4')
        values = array.astype(dtype)
        if quantized:
            aligned = np.zeros((len(values), 4), dtype=dtype)
            aligned[:, :3] = values
            values = aligned
        view = {'buffer': 0, 'byteOffset': len(binary), 'byteLength': values.nbytes, 'byteStride': 8 if quantized else 12}
        views.append(view)
        binary.extend(values.tobytes())
        accessors.append({'bufferView': len(views)-1, 'componentType': 5122 if quantized else 5126, 'count': len(array), 'type': 'VEC3', **({'normalized': True} if quantized else {})})
    data = {'asset': {'version':'2.0'}, 'scene':0, 'scenes':[{'nodes':[0]}], 'nodes':[{'name':'part-A','mesh':0,'extras':{'source':'Inert fixture'},**({'scale':[.1,.1,.1]} if quantized else {})}], 'meshes':[{'name':'mesh-A','primitives':[{'attributes':{'POSITION':0,'NORMAL':1},'material':0}]}], 'materials':[{'name':'material-A','pbrMetallicRoughness':{'roughnessFactor':.4}}], 'buffers':[{'byteLength':len(binary)}], 'bufferViews':views, 'accessors':accessors}
    return data, binary


def write(path, data, binary):
    metadata = json.dumps(data,separators=(',',':')).encode()
    metadata += b' ' * (-len(metadata) % 4)
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    body = struct.pack('<I4s',len(metadata),b'JSON')+metadata+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    path.write_bytes(struct.pack('<4sII',b'glTF',2,len(body)+12)+body)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.source, self.candidate = Path(self.folder.name)/'source.glb', Path(self.folder.name)/'candidate.glb'
        source, binary = fixture(False)
        write(self.source,source,binary)
        self.data,self.binary = fixture(True)
        write(self.candidate,self.data,self.binary)

    def tearDown(self): self.folder.cleanup()
    def run_validation(self):
        write(self.candidate,self.data,self.binary)
        return validator.validate(self.source,self.candidate)

    def test_accepts_bounded_quantized_geometry(self):
        result = self.run_validation()
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['part_count'],1)
        self.assertEqual(result['triangle_count'],100)

    def test_rejects_changed_part_identity(self):
        self.data['nodes'][0]['name']='renamed'
        with self.assertRaisesRegex(AssertionError,'Part names'): self.run_validation()

    def test_rejects_changed_pbr_material(self):
        self.data['materials'][0]['pbrMetallicRoughness']['roughnessFactor']=.8
        with self.assertRaisesRegex(AssertionError,'material changed'): self.run_validation()

    def test_rejects_changed_provenance(self):
        self.data['nodes'][0]['extras']['source']='Invented source'
        with self.assertRaisesRegex(AssertionError,'provenance'): self.run_validation()

    def test_rejects_displaced_world_geometry(self):
        self.data['nodes'][0]['translation']=[.01,0,0]
        with self.assertRaisesRegex(AssertionError,'position/bounds'): self.run_validation()

    def test_rejects_reversed_normals(self):
        offset=self.data['bufferViews'][1]['byteOffset']
        for i in range(300): struct.pack_into('<h',self.binary,offset+i*8+4,-32767)
        with self.assertRaisesRegex(AssertionError,'normal error'): self.run_validation()

    def test_rejects_changed_primitive_mode(self):
        self.data['meshes'][0]['primitives'][0]['mode']=1
        with self.assertRaisesRegex(AssertionError,'primitive mode'): self.run_validation()

if __name__=='__main__': unittest.main()
