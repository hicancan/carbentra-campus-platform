"""Independent glTF binary/NumPy validation; never imports the optimization library."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np

COMPONENTS = {5120: np.dtype('i1'), 5121: np.dtype('u1'), 5122: np.dtype('<i2'), 5123: np.dtype('<u2'), 5125: np.dtype('<u4'), 5126: np.dtype('<f4')}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

class GLB:
    def __init__(self, path):
        self.bytes = Path(path).read_bytes()
        magic, version, size = struct.unpack_from('<4sII', self.bytes)
        assert magic == b'glTF' and version == 2 and size == len(self.bytes), 'Invalid GLB'
        offset = 12
        self.data = None
        self.binary = None
        while offset < len(self.bytes):
            length, kind = struct.unpack_from('<I4s', self.bytes, offset)
            chunk = memoryview(self.bytes)[offset + 8:offset + 8 + length]
            if kind == b'JSON': self.data = json.loads(bytes(chunk))
            elif kind == b'BIN\0': self.binary = chunk
            offset += 8 + length
        assert self.data is not None and self.binary is not None
        assert not self.data.get('animations') and not self.data.get('skins')
        assert not any(b.get('uri') for b in self.data.get('buffers', []))
        self.names = {node['name']: i for i, node in enumerate(self.data['nodes'])}
        assert len(self.names) == len(self.data['nodes']), 'Duplicate part names'
        self.world = {}
        def visit(index, parent):
            assert index not in self.world, 'Non-tree node graph'
            node = self.data['nodes'][index]
            local = self.matrix(node)
            world = parent @ local
            self.world[index] = world
            for child in node.get('children', []): visit(child, world)
        scene = self.data['scenes'][self.data.get('scene', 0)]
        for index in scene['nodes']: visit(index, np.eye(4))
        assert len(self.world) == len(self.names), 'Unreachable source part'

    @staticmethod
    def matrix(node):
        if 'matrix' in node: return np.array(node['matrix'], dtype=float).reshape((4, 4), order='F')
        x, y, z, w = node.get('rotation', [0, 0, 0, 1])
        rotation = np.array([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w], [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w], [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]])
        matrix = np.eye(4)
        matrix[:3, :3] = rotation @ np.diag(node.get('scale', [1, 1, 1]))
        matrix[:3, 3] = node.get('translation', [0, 0, 0])
        return matrix

    def accessor(self, index):
        accessor = self.data['accessors'][index]
        assert not accessor.get('sparse'), 'Sparse accessors require a separate validator'
        view = self.data['bufferViews'][accessor['bufferView']]
        assert view.get('buffer', 0) == 0
        dtype = COMPONENTS[accessor['componentType']]
        width = WIDTHS[accessor['type']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        array = np.ndarray((accessor['count'], width), dtype=dtype, buffer=self.binary, offset=offset, strides=(view.get('byteStride', dtype.itemsize * width), dtype.itemsize)).astype(np.float64)
        if accessor.get('normalized'):
            info = np.iinfo(dtype)
            array = np.maximum(array / info.max, -1) if info.min < 0 else array / info.max
        assert np.isfinite(array).all(), 'Non-finite accessor'
        return array

    def material(self, primitive):
        if 'material' not in primitive: return None
        material = dict(self.data['materials'][primitive['material']])
        pbr = dict(material.get('pbrMetallicRoughness', {}))
        pbr.setdefault('baseColorFactor', [1, 1, 1, 1])
        pbr.setdefault('metallicFactor', 1)
        pbr.setdefault('roughnessFactor', 1)
        material['pbrMetallicRoughness'] = pbr
        material.setdefault('alphaMode', 'OPAQUE')
        material.setdefault('doubleSided', False)
        material.setdefault('emissiveFactor', [0, 0, 0])
        if material['alphaMode'] == 'MASK': material.setdefault('alphaCutoff', 0.5)
        return material

def validate(source, candidate, position_tolerance_m=0.00001, normal_tolerance_degrees=0.01):
    old, new = GLB(source), GLB(candidate)
    assert old.names.keys() == new.names.keys(), 'Part names differ'
    assert len(new.bytes) < len(old.bytes), 'No actual display-size reduction'
    assert len(old.data['meshes']) == len(new.data['meshes']), 'Mesh identities were joined or removed'
    assert old.data.get('images', []) == new.data.get('images', []), 'Image references changed'
    parts = []
    for name, oi in old.names.items():
        ni = new.names[name]
        on, nn = old.data['nodes'][oi], new.data['nodes'][ni]
        assert on.get('extras', {}) == nn.get('extras', {}), f'{name}: provenance changed'
        assert [old.data['nodes'][i]['name'] for i in on.get('children', [])] == [new.data['nodes'][i]['name'] for i in nn.get('children', [])], f'{name}: hierarchy changed'
        assert ('mesh' in on) == ('mesh' in nn), f'{name}: mesh presence changed'
        if 'mesh' not in on: continue
        om, nm = old.data['meshes'][on['mesh']], new.data['meshes'][nn['mesh']]
        assert om.get('name') == nm.get('name') and om.get('extras', {}) == nm.get('extras', {}), f'{name}: mesh metadata changed'
        assert len(om['primitives']) == len(nm['primitives']), f'{name}: primitive count changed'
        position_error = normal_error = bounds_error = 0.0
        vertex_count = triangle_count = 0
        for op, np_ in zip(om['primitives'], nm['primitives']):
            assert op.get('mode', 4) == np_.get('mode', 4) == 4, f'{name}: primitive mode changed'
            assert op.get('extras', {}) == np_.get('extras', {}), f'{name}: primitive extras changed'
            assert old.material(op) == new.material(np_), f'{name}: PBR material changed'
            assert op['attributes'].keys() == np_['attributes'].keys(), f'{name}: vertex attributes changed'
            ov, nv = old.accessor(op['attributes']['POSITION']), new.accessor(np_['attributes']['POSITION'])
            assert ov.shape == nv.shape, f'{name}: vertex count changed'
            vertex_count += ov.shape[0]
            oidx = old.accessor(op['indices']) if 'indices' in op else np.arange(len(ov))[:, None]
            nidx = new.accessor(np_['indices']) if 'indices' in np_ else np.arange(len(nv))[:, None]
            assert np.array_equal(oidx, nidx), f'{name}: topology changed'
            triangle_count += len(oidx) // 3
            ow = ov @ old.world[oi][:3, :3].T + old.world[oi][:3, 3]
            nw = nv @ new.world[ni][:3, :3].T + new.world[ni][:3, 3]
            delta = float(np.linalg.norm(ow-nw, axis=1).max(initial=0))
            bounds_delta = float(np.max(np.abs(np.array([ow.min(axis=0), ow.max(axis=0)])-np.array([nw.min(axis=0), nw.max(axis=0)]))))
            position_error = max(position_error, delta)
            bounds_error = max(bounds_error, bounds_delta)
            assert delta <= position_tolerance_m and bounds_delta <= position_tolerance_m, f'{name}: position/bounds error {delta}/{bounds_delta}'
            for semantic in op['attributes']:
                if semantic == 'POSITION': continue
                oa, na = old.accessor(op['attributes'][semantic]), new.accessor(np_['attributes'][semantic])
                assert oa.shape == na.shape
                if semantic == 'NORMAL':
                    oa = oa @ np.linalg.inv(old.world[oi][:3, :3])
                    na = na @ np.linalg.inv(new.world[ni][:3, :3])
                    olen, nlen = np.linalg.norm(oa, axis=1), np.linalg.norm(na, axis=1)
                    assert np.all(olen > 0) and np.all(nlen > 0), f'{name}: zero normal'
                    cosine = np.sum((oa / olen[:, None]) * (na / nlen[:, None]), axis=1)
                    angle = float(np.degrees(np.arccos(np.clip(cosine, -1, 1))).max(initial=0))
                    normal_error = max(normal_error, angle)
                    assert angle <= normal_tolerance_degrees, f'{name}: normal error {angle}'
                else: assert np.array_equal(oa, na), f'{name}: {semantic} changed'
        parts.append({'id': name, 'vertices': vertex_count, 'triangles': triangle_count, 'max_world_position_error_m': position_error, 'max_world_bounds_error_m': bounds_error, 'max_world_normal_error_degrees': normal_error})
    return {'validator': 'independent GLB/NumPy', 'numpy_version': np.__version__, 'status': 'passed', 'source_sha256': hashlib.sha256(old.bytes).hexdigest(), 'display_sha256': hashlib.sha256(new.bytes).hexdigest(), 'position_tolerance_m': position_tolerance_m, 'normal_tolerance_degrees': normal_tolerance_degrees, 'parts': parts, 'part_count': len(parts), 'triangle_count': sum(p['triangles'] for p in parts), 'max_world_position_error_m': max(p['max_world_position_error_m'] for p in parts), 'max_world_bounds_error_m': max(p['max_world_bounds_error_m'] for p in parts), 'max_world_normal_error_degrees': max(p['max_world_normal_error_degrees'] for p in parts), 'topology_unchanged': True, 'part_ids_unchanged': True, 'materials_unchanged': True, 'extras_unchanged': True, 'physical_geometry_claim': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    result = validate(args.source, args.candidate)
    Path(args.report).write_text(json.dumps(result, indent=2) + '\n', encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != 'parts'}))
