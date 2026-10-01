"""Stdlib-only local worker probe; no database credentials or application imports.

Workers publish after a successful durable tick. A heartbeat is valid only while
its original process is alive, avoiding a stale file succeeding after a restart.
This is process-local readiness; /system/status retains the shared DB heartbeat.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time


def health_directory():
    return Path(os.environ.get('CARBENTRA_WORKER_HEALTH_DIR', str(Path(tempfile.gettempdir())/'carbentra-worker-health')))


def process_identity(pid):
    try:
        if os.name == 'nt':
            # PID alone can be reused. Bind readiness to the live process creation
            # FILETIME just as Linux binds it to the process start clock tick.
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)]*4)]
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x1000, False, int(pid))
            if not handle:
                return None
            try:
                created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
                status = wintypes.DWORD()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(status)) or status.value != 259:
                    return None
                if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(system), ctypes.byref(user)):
                    return None
                return str((created.dwHighDateTime << 32) | created.dwLowDateTime)
            finally:
                kernel.CloseHandle(handle)
        # Linux stat field 22 is the process start clock tick; comm may contain spaces.
        data=Path(f'/proc/{int(pid)}/stat').read_text(encoding="utf-8")
        fields=data.rsplit(') ',1)[1].split()
        return None if fields[0] in {'Z','X'} else fields[19]
    except (OSError,ValueError,IndexError):
        return None


def publish(role, durable_tick_epoch, directory=None):
    directory=Path(directory) if directory is not None else health_directory()
    directory.mkdir(parents=True,exist_ok=True)
    value={'version':1,'role':role,'pid':os.getpid(),'process_start':process_identity(os.getpid()),
        'tick_epoch':durable_tick_epoch,'written_monotonic':time.monotonic()}
    descriptor,name=tempfile.mkstemp(prefix=role+'-',suffix='.tmp',dir=directory)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(value,stream,allow_nan=False)
        os.replace(name,directory/(role+'.json'))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def healthy(role='control',max_age=10,directory=None):
    path=(Path(directory) if directory is not None else health_directory())/(role+'.json')
    try:
        if path.stat().st_size>4096:
            return False
        value=json.loads(path.read_text(encoding="utf-8"))
        age=time.time()-float(value['tick_epoch'])
        monotonic_age=time.monotonic()-float(value['written_monotonic'])
        return (value['version']==1 and value['role']==role and 0<=age<max_age and 0<=monotonic_age<max_age
            and value['process_start'] is not None and process_identity(value['pid'])==value['process_start'])
    except (OSError,ValueError,TypeError,KeyError):
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['control','simulation','analysis'],default='control')
    args=parser.parse_args()
    try:
        interval=int(os.environ.get('CARBENTRA_SIMULATION_INTERVAL_SECONDS','30'))
        maximum=180 if args.role=='analysis' else interval*3 if args.role=='simulation' else 10
        valid=5<=interval<=300 and healthy(args.role,maximum)
    except (ValueError,OverflowError):
        valid=False
    raise SystemExit(0 if valid else 1)


if __name__=='__main__':
    main()
