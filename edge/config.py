"""Operator configuration, not an automatic enrollment mechanism."""
from adapters import Enrollment


def enrollments(config):
    if not isinstance(config, dict):
        raise ValueError('configuration object required')
    if 'enrollments' in config:
        if not isinstance(config['enrollments'], list) or not config['enrollments']:
            raise ValueError('nonempty enrollment list required')
        result = [Enrollment(**item) for item in config['enrollments']]
    else:
        # Concrete prior Plug gateway configuration, retained only for migration.
        devices, virtual = config.get('devices'), config.get('virtual_devices', [])
        if not isinstance(devices, list) or not isinstance(virtual, list) or not set(virtual) <= set(devices):
            raise ValueError('invalid legacy Plug enrollment')
        result = [Enrollment(d, 'PLUG', 'plug-wire-v2', 'SIMULATED' if d in virtual else 'REAL') for d in devices]
    if len({e.device_id for e in result}) != len(result):
        raise ValueError('duplicate device enrollment')
    return result
